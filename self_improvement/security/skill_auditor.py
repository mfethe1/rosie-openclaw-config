#!/usr/bin/env python3
"""
skill_auditor.py — AST Static Analyzer for ClawHub Skill Audits.

Scans Python files for dangerous patterns including shell execution,
code injection, unsafe network calls, and restricted filesystem writes.

Usage:
    python3 skill_auditor.py <path_to_skill_dir>
    python3 skill_auditor.py --test
"""

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALLOWLISTED_HOSTS: set[str] = {
    "api.anthropic.com",
    "api.openai.com",
    "api.telegram.org",
    "raw.githubusercontent.com",
    "github.com",
    "pypi.org",
    "files.pythonhosted.org",
}

RESTRICTED_WRITE_PREFIXES: tuple[str, ...] = (
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/lib/",
    "/boot/",
    ".ssh/",
    "~/.ssh",
)

SYSTEM_DIRS_FOR_RMTREE: tuple[str, ...] = (
    "/",
    "/etc",
    "/usr",
    "/bin",
    "/home",
    "/root",
    "/var",
)


# ---------------------------------------------------------------------------
# Finding dataclass (plain dict for stdlib compat)
# ---------------------------------------------------------------------------

def make_finding(
    file: str,
    line: int,
    pattern: str,
    severity: str,
    recommendation: str,
) -> dict[str, Any]:
    """Return a standardised finding dict."""
    return {
        "file": file,
        "line": line,
        "pattern": pattern,
        "severity": severity,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------

class SecurityVisitor(ast.NodeVisitor):
    """Walk an AST and collect security findings."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.findings: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add(self, node: ast.AST, pattern: str, severity: str, recommendation: str) -> None:
        lineno = getattr(node, "lineno", 0)
        self.findings.append(make_finding(self.filepath, lineno, pattern, severity, recommendation))

    @staticmethod
    def _const_str(node: ast.expr | None) -> str | None:
        """Return the string value of a constant node, or None."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    @staticmethod
    def _call_names(node: ast.Call) -> tuple[str, ...]:
        """Return (module, attr) or (name,) for a call."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return (node.func.value.id, node.func.attr)
            return (node.func.attr,)
        if isinstance(node.func, ast.Name):
            return (node.func.id,)
        return ()

    # ------------------------------------------------------------------
    # Visitors
    # ------------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        names = self._call_names(node)

        # eval() / exec()
        if names == ("eval",):
            self._add(node, "eval()", "CRITICAL",
                      "Remove eval(); use ast.literal_eval() for safe data parsing.")
        elif names == ("exec",):
            self._add(node, "exec()", "CRITICAL",
                      "Remove exec(); refactor to explicit function calls.")

        # __import__()
        elif names == ("__import__",):
            self._add(node, "__import__()", "HIGH",
                      "Use standard 'import' statements or importlib.import_module().")

        # os.system
        elif names == ("os", "system"):
            self._add(node, "os.system()", "HIGH",
                      "Replace with subprocess.run(..., shell=False) and validate inputs.")

        # subprocess.*
        elif len(names) == 2 and names[0] == "subprocess":
            if names[1] in ("call", "run", "Popen", "check_call", "check_output"):
                # Check for shell=True
                shell_true = any(
                    isinstance(kw.value, ast.Constant) and kw.value.value is True
                    for kw in node.keywords if kw.arg == "shell"
                )
                severity = "HIGH" if shell_true else "MEDIUM"
                detail = " with shell=True" if shell_true else ""
                self._add(node, f"subprocess.{names[1]}(){detail}", severity,
                          "Avoid shell=True; pass args as a list and validate all inputs.")

        # shutil.rmtree on system dirs
        elif names == ("shutil", "rmtree"):
            if node.args:
                path_val = self._const_str(node.args[0])
                if path_val and any(path_val.startswith(d) for d in SYSTEM_DIRS_FOR_RMTREE):
                    self._add(node, f"shutil.rmtree({path_val!r})", "CRITICAL",
                              "Never delete system directories programmatically.")

        # Network calls — urllib / http.client / socket.connect
        elif names in (("urllib", "urlopen"), ("urllib", "request")) or (
            len(names) >= 1 and names[-1] in ("urlopen", "urlretrieve")
        ):
            self._check_url_args(node, ".".join(names))

        # requests.get/post/put/delete/request (optional; stdlib-only but flag the pattern)
        elif len(names) == 2 and names[0] == "requests":
            self._check_url_args(node, f"requests.{names[1]}")

        # open() for restricted write paths
        elif names == ("open",) or names == ("builtins", "open"):
            self._check_open(node)

        self.generic_visit(node)

    def _check_url_args(self, node: ast.Call, pattern_name: str) -> None:
        """Flag network calls to non-allowlisted hosts."""
        if not node.args:
            return
        url = self._const_str(node.args[0])
        if url is None:
            return
        # Extract host
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower().split(":")[0]
        except Exception:
            return
        if host and host not in ALLOWLISTED_HOSTS:
            self._add(node, f"{pattern_name}({url!r})", "MEDIUM",
                      f"Host '{host}' is not in the allowlist. Verify this endpoint is safe.")

    def _check_open(self, node: ast.Call) -> None:
        """Flag file writes to restricted directories."""
        if not node.args:
            return
        path_val = self._const_str(node.args[0])
        if path_val is None:
            return
        # Determine mode
        mode = "r"
        if len(node.args) >= 2:
            mode = self._const_str(node.args[1]) or "r"
        for kw in node.keywords:
            if kw.arg == "mode":
                mode = self._const_str(kw.value) or mode
        if "w" in mode or "a" in mode or "x" in mode:
            expanded = path_val.replace("~", "/root")
            if any(expanded.startswith(p) or p in expanded for p in RESTRICTED_WRITE_PREFIXES):
                self._add(node, f"open({path_val!r}, mode={mode!r})", "HIGH",
                          "Writing to restricted paths is forbidden. Use a sandboxed temp dir.")

    def visit_Import(self, node: ast.Import) -> None:
        """Flag direct import of known dangerous modules when misused."""
        for alias in node.names:
            if alias.name in ("pickle", "marshal"):
                self._add(node, f"import {alias.name}", "LOW",
                          f"'{alias.name}' can deserialise arbitrary objects; ensure inputs are trusted.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module in ("pickle", "marshal"):
            self._add(node, f"from {node.module} import ...", "LOW",
                      f"'{node.module}' deserialisation risk; ensure inputs are trusted.")
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def audit_file(filepath: str) -> list[dict[str, Any]]:
    """Parse and audit a single Python file. Returns list of findings."""
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as exc:
        return [make_finding(filepath, exc.lineno or 0, "SyntaxError", "INFO",
                             f"File could not be parsed: {exc}")]
    except Exception as exc:
        return [make_finding(filepath, 0, "ReadError", "INFO", str(exc))]

    visitor = SecurityVisitor(filepath)
    visitor.visit(tree)
    return visitor.findings


def audit_directory(dirpath: str) -> dict[str, Any]:
    """Recursively audit all .py files under dirpath. Returns full report."""
    findings: list[dict[str, Any]] = []
    scanned: list[str] = []

    for root, _dirs, files in os.walk(dirpath):
        for fname in files:
            if fname.endswith(".py"):
                full = os.path.join(root, fname)
                scanned.append(full)
                findings.extend(audit_file(full))

    return {
        "scanned_files": len(scanned),
        "total_findings": len(findings),
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

SAFE_CODE = '''
import json
import os

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

def greet(name: str) -> str:
    return f"Hello, {name}"
'''

UNSAFE_CODE = '''
import os
import subprocess
import shutil
import pickle

def bad_eval(x):
    return eval(x)

def bad_exec():
    exec("import sys; sys.exit()")

def bad_os():
    os.system("rm -rf /tmp/test")

def bad_sub():
    subprocess.run("ls", shell=True)

def bad_rmtree():
    shutil.rmtree("/etc/cron.d")

def bad_write():
    with open("/etc/passwd", "w") as f:
        f.write("hacked")

def bad_import():
    __import__("os")
'''


def run_tests() -> None:
    """Self-test: validate detector against safe and unsafe samples."""
    import tempfile

    print("Running skill_auditor self-tests...")

    with tempfile.TemporaryDirectory() as tmpdir:
        safe_path = os.path.join(tmpdir, "safe.py")
        unsafe_path = os.path.join(tmpdir, "unsafe.py")
        Path(safe_path).write_text(SAFE_CODE)
        Path(unsafe_path).write_text(UNSAFE_CODE)

        safe_findings = audit_file(safe_path)
        unsafe_findings = audit_file(unsafe_path)

    print(f"  Safe file findings:   {len(safe_findings)} (expected 0)")
    assert len(safe_findings) == 0, f"Safe code produced findings: {safe_findings}"

    patterns_found = {f["pattern"].split("(")[0] for f in unsafe_findings}
    expected = {"eval", "exec", "os.system", "subprocess.run", "shutil.rmtree",
                "open", "__import__"}
    missing = expected - {p.split(".")[0] if "." not in p else p for p in patterns_found}
    # Flatten check — just ensure we caught the critical ones
    raw_patterns = " ".join(f["pattern"] for f in unsafe_findings)
    for keyword in ("eval()", "exec()", "os.system()", "subprocess.run()", "shutil.rmtree", "__import__"):
        assert keyword in raw_patterns, f"Expected to detect '{keyword}' but didn't. Found: {raw_patterns}"

    print(f"  Unsafe file findings: {len(unsafe_findings)} (expected ≥7)")
    assert len(unsafe_findings) >= 7, f"Expected ≥7 findings, got {len(unsafe_findings)}"

    print("  All tests PASSED ✓")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--test":
        run_tests()
        return

    target = sys.argv[1]
    if os.path.isdir(target):
        report = audit_directory(target)
    elif os.path.isfile(target):
        findings = audit_file(target)
        report = {"scanned_files": 1, "total_findings": len(findings), "findings": findings}
    else:
        print(f"Error: '{target}' is not a file or directory.", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
