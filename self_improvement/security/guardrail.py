#!/usr/bin/env python3
"""
guardrail.py — C9 Guardrail Class
A reusable guardrail that wraps any agent action and enforces safety rules.

Usage:
    from guardrail import Guardrail

    g = Guardrail()
    result = g.check(action="write_file", target="/etc/hosts", content="...")
    # Returns: {"allowed": False, "reason": "blocked path", "severity": "HIGH"}

CLI:
    python3 guardrail.py --test
"""

import sys
import json
import os
import re
import datetime
import pathlib
from typing import Optional

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
LOG_DIR = SCRIPT_DIR / "logs"

# ---------------------------------------------------------------------------
# Allowlisted hosts for network calls
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = {
    "api.anthropic.com",
    "api.openai.com",
    "openrouter.ai",
    "api.openrouter.ai",
    "brave.com",
    "search.brave.com",
    "api.search.brave.com",
    "firecrawl.dev",
    "api.firecrawl.dev",
    "pypi.org",
    "files.pythonhosted.org",
    "github.com",
    "api.github.com",
    "raw.githubusercontent.com",
    "localhost",
    "127.0.0.1",
}

# ---------------------------------------------------------------------------
# Blocked path prefixes (write_file)
# ---------------------------------------------------------------------------
BLOCKED_PATH_PREFIXES = [
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/lib/",
    "/boot/",
    "/sys/",
    "/proc/",
    "/dev/",
]

BLOCKED_PATH_SUFFIXES = [
    ".ssh/id_rsa",
    ".ssh/id_ed25519",
    ".ssh/authorized_keys",
    ".ssh/known_hosts",
    ".ssh/config",
]

BLOCKED_FILENAMES = {
    "openclaw.json",
    "jobs.json",
}

BLOCKED_PATH_PATTERNS = [
    re.compile(r"(^|/)\.ssh/"),
]

# ---------------------------------------------------------------------------
# Destructive command patterns
# ---------------------------------------------------------------------------
DESTRUCTIVE_COMMANDS = [
    re.compile(r"\brm\s+-[^\s]*r[^\s]*\s", re.IGNORECASE),   # rm -rf, rm -r
    re.compile(r"\brm\s+--recursive", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+", re.IGNORECASE),
    re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+-R\s+777\b", re.IGNORECASE),
    re.compile(r":\s*\(\s*\)\s*\{", re.IGNORECASE),           # fork bomb
    re.compile(r"\bshred\b", re.IGNORECASE),
    re.compile(r"\bwipefs\b", re.IGNORECASE),
    re.compile(r"\bformat\s+c:", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Dangerous content patterns (eval/exec in written content)
# ---------------------------------------------------------------------------
DANGEROUS_CONTENT_PATTERNS = [
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bexec\s*\(", re.IGNORECASE),
    re.compile(r"\b__import__\s*\(", re.IGNORECASE),
    re.compile(r"\bcompile\s*\(", re.IGNORECASE),
    re.compile(r"\bos\.system\s*\(", re.IGNORECASE),
    re.compile(r"\bsubprocess\.call\s*\(\s*['\"]rm", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Network host extraction
# ---------------------------------------------------------------------------
_HOST_RE = re.compile(
    r"https?://([a-zA-Z0-9\-\.]+)",
    re.IGNORECASE,
)


def _extract_hosts(text: str) -> list:
    return _HOST_RE.findall(text)


# ---------------------------------------------------------------------------
# Guardrail class
# ---------------------------------------------------------------------------

class Guardrail:
    """C9 Guardrail: wraps agent actions and enforces safety rules."""

    def __init__(self, log_dir: Optional[str] = None, allowed_hosts: Optional[set] = None):
        self.log_dir = pathlib.Path(log_dir) if log_dir else LOG_DIR
        self.allowed_hosts = allowed_hosts if allowed_hosts is not None else ALLOWED_HOSTS

    def _log_blocked(self, action: str, target: str, reason: str, severity: str) -> None:
        """Append blocked action to daily JSONL log."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.date.today().strftime("%Y-%m-%d")
        log_path = self.log_dir / f"guardrail-{today}.jsonl"
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "action": action,
            "target": target,
            "reason": reason,
            "severity": severity,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _block(self, action: str, target: str, reason: str, severity: str) -> dict:
        self._log_blocked(action, target, reason, severity)
        return {"allowed": False, "reason": reason, "severity": severity}

    def _allow(self) -> dict:
        return {"allowed": True, "reason": "passed all checks"}

    # ------------------------------------------------------------------
    # Individual rule checkers
    # ------------------------------------------------------------------

    def _check_write_file(self, target: str, content: str) -> Optional[dict]:
        """Check write_file action rules."""
        abs_target = os.path.abspath(target)
        norm = abs_target.replace("\\", "/")

        # Blocked path prefixes
        for prefix in BLOCKED_PATH_PREFIXES:
            if norm.startswith(prefix):
                return self._block("write_file", target, f"blocked path: {prefix}", "HIGH")

        # Blocked filename (anywhere in path)
        basename = os.path.basename(norm)
        if basename in BLOCKED_FILENAMES:
            return self._block("write_file", target, f"blocked filename: {basename}", "HIGH")

        # Blocked path patterns (.ssh/)
        for pat in BLOCKED_PATH_PATTERNS:
            if pat.search(norm):
                return self._block("write_file", target, "blocked path: .ssh/", "HIGH")

        # Blocked path suffixes
        for suffix in BLOCKED_PATH_SUFFIXES:
            if norm.endswith(suffix):
                return self._block("write_file", target, f"blocked path suffix: {suffix}", "HIGH")

        # Dangerous content (eval/exec)
        for pat in DANGEROUS_CONTENT_PATTERNS:
            if pat.search(content):
                return self._block("write_file", target, f"dangerous content: {pat.pattern[:40]}", "HIGH")

        return None  # no block

    def _check_run_command(self, target: str, content: str) -> Optional[dict]:
        """Check run_command action rules."""
        command_text = target + " " + content

        for pat in DESTRUCTIVE_COMMANDS:
            if pat.search(command_text):
                return self._block("run_command", target, f"destructive command: {pat.pattern[:50]}", "CRITICAL")

        return None

    def _check_network_call(self, target: str, content: str) -> Optional[dict]:
        """Check network_call action rules (host allowlist)."""
        hosts = _extract_hosts(target) + _extract_hosts(content)
        for host in hosts:
            # Strip port
            host_clean = host.split(":")[0].lower()
            if host_clean not in self.allowed_hosts:
                # Check wildcard subdomain matches
                allowed = False
                for allowed_host in self.allowed_hosts:
                    if host_clean.endswith("." + allowed_host) or host_clean == allowed_host:
                        allowed = True
                        break
                if not allowed:
                    return self._block("network_call", target, f"host not in allowlist: {host_clean}", "HIGH")
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, action: str, target: str, content: str = "") -> dict:
        """
        Check if an agent action is allowed.

        Args:
            action:  One of: write_file, run_command, network_call, or any custom action.
            target:  The target path, command, or URL.
            content: Optional content being written or request body.

        Returns:
            dict with keys: allowed (bool), reason (str), [severity (str) if blocked]
        """
        action = action.lower().replace("-", "_").replace(" ", "_")

        if action in ("write_file", "write", "file_write"):
            result = self._check_write_file(target, content)
        elif action in ("run_command", "exec", "shell", "command"):
            result = self._check_run_command(target, content)
        elif action in ("network_call", "http_request", "fetch", "request"):
            result = self._check_network_call(target, content)
        else:
            # For unknown actions, run all checks as appropriate
            result = self._check_run_command(target, content)
            if result is None and target.startswith(("/", "~", ".")):
                result = self._check_write_file(target, content)
            if result is None:
                result = self._check_network_call(target, content)

        return result if result is not None else self._allow()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    import tempfile
    print("Running guardrail self-tests...")

    # Use a temp log dir so we don't pollute prod logs during testing
    with tempfile.TemporaryDirectory() as tmpdir:
        g = Guardrail(log_dir=tmpdir)

        tests = [
            # (action, target, content, expected_allowed, description)
            ("write_file", "/etc/hosts", "127.0.0.1 evil.com", False, "Block write to /etc/"),
            ("write_file", "/usr/bin/python3", "#!/bin/bash", False, "Block write to /usr/"),
            ("write_file", "/home/user/.ssh/authorized_keys", "ssh-rsa ...", False, "Block write to .ssh/"),
            ("write_file", "/home/user/.ssh/config", "Host *", False, "Block write to .ssh/config"),
            ("write_file", "/app/openclaw.json", "{}", False, "Block openclaw.json"),
            ("write_file", "/app/jobs.json", "[]", False, "Block jobs.json"),
            ("write_file", "./output.md", "# Safe content", True, "Allow safe write"),
            ("write_file", "/tmp/test.py", "import os\neval('1+1')", False, "Block eval() in content"),
            ("write_file", "/tmp/test.py", "exec('import os')", False, "Block exec() in content"),
            ("run_command", "rm -rf /", "", False, "Block rm -rf /"),
            ("run_command", "rm -rf /home/user", "", False, "Block rm -rf path"),
            ("run_command", "mkfs.ext4 /dev/sda1", "", False, "Block mkfs"),
            ("run_command", "dd if=/dev/zero of=/dev/sda", "", False, "Block dd"),
            ("run_command", "chmod 777 /etc/passwd", "", False, "Block chmod 777"),
            ("run_command", "ls -la /tmp", "", True, "Allow safe command"),
            ("run_command", "python3 script.py", "", True, "Allow safe python"),
            ("network_call", "https://api.anthropic.com/v1/messages", "", True, "Allow anthropic API"),
            ("network_call", "https://evil.example.com/steal", "", False, "Block non-allowlisted host"),
            ("network_call", "https://api.openai.com/v1/chat", "", True, "Allow OpenAI API"),
        ]

        failures = []
        for action, target, content, expected, desc in tests:
            result = g.check(action=action, target=target, content=content)
            actual = result["allowed"]
            status = "PASS" if actual == expected else "FAIL"
            if actual != expected:
                failures.append(f"{desc}: expected allowed={expected}, got {result}")
            print(f"  [{status}] {desc}")

        # Test that blocked actions are logged
        log_files = list(pathlib.Path(tmpdir).glob("guardrail-*.jsonl"))
        assert len(log_files) >= 1, "Expected at least one log file"
        with open(log_files[0]) as f:
            lines = f.readlines()
        assert len(lines) > 0, "Expected log entries for blocked actions"
        print(f"  [PASS] Blocked actions logged ({len(lines)} entries)")

        if failures:
            print(f"\nFAILED ({len(failures)}):")
            for f in failures:
                print(f"  - {f}")
            sys.exit(1)
        else:
            print(f"\nAll guardrail self-tests PASSED ({len(tests)} tests).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    if "--test" in args or not args:
        _self_test()
        return

    # Simple interactive check: guardrail.py check <action> <target> [content]
    if args[0] == "check":
        if len(args) < 3:
            print("Usage: guardrail.py check <action> <target> [content]", file=sys.stderr)
            sys.exit(1)
        action = args[1]
        target = args[2]
        content = args[3] if len(args) > 3 else ""
        g = Guardrail()
        result = g.check(action=action, target=target, content=content)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["allowed"] else 1)
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        print("Usage: guardrail.py check <action> <target> [content] | --test", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
