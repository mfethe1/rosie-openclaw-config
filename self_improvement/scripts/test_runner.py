#!/usr/bin/env python3
"""test_runner.py — Automated test execution + fix loop skill (Winnie Cycle #13).

Runs any command (or list of commands) with:
  1. Capture: stdout, stderr, exit code, duration
  2. Classify: PASS / FAIL / TIMEOUT / ERROR
  3. Fix loop: on FAIL, apply heuristic fixers and retry (up to --max-attempts)
  4. Store: write result to agent-memory.db via agent_memory_cli.py
  5. Report: structured JSON + Markdown summary

Usage:
  python3 test_runner.py --cmd "python3 -m py_compile scripts/foo.py"
  python3 test_runner.py --cmd "bash smoke_test.sh" --max-attempts 2 --timeout 60
  python3 test_runner.py --suite scripts/test_suite.txt   # one command per line
  python3 test_runner.py --cmd "pytest tests/" --agent mack --dry-run

Fix strategies applied (in order on FAIL):
  - module_not_found   : pip install <missing_module> (Python 3.13)
  - permission_denied  : chmod +x <path> extracted from stderr
  - command_not_found  : skip + note (cannot auto-fix binary paths)
  - syntax_error       : report line/col, no retry (code bug)
  - connection_refused : retry with backoff (transient service)
  - generic            : single plain retry
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

# ── constants ──────────────────────────────────────────────────────────────
PYTHON = "/opt/homebrew/bin/python3.13"
CLI = Path(__file__).parent / "agent_memory_cli.py"
DEFAULT_TIMEOUT = 120        # seconds per attempt
DEFAULT_MAX_ATTEMPTS = 3
BACKOFF_BASE = 2.0           # seconds, doubled each retry


# ── result types ───────────────────────────────────────────────────────────
class RunResult(NamedTuple):
    cmd: str
    attempt: int
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    status: str          # PASS | FAIL | TIMEOUT | ERROR
    fix_applied: str     # "" if none
    notes: str


class SuiteReport(NamedTuple):
    ran: int
    passed: int
    failed: int
    results: list[RunResult]
    total_ms: float


# ── fix strategies ─────────────────────────────────────────────────────────

def _fix_module_not_found(stderr: str, cmd: str) -> str | None:
    """pip-install the missing module if identifiable."""
    m = re.search(r"No module named '([^']+)'", stderr)
    if not m:
        return None
    module = m.group(1).split(".")[0]   # top-level package
    # Safety: only install known safe packages
    SAFE = {"sentence_transformers", "fastembed", "sqlite_vec",
            "numpy", "scipy", "sklearn", "requests", "httpx"}
    pkg = module.replace("_", "-")
    if module not in SAFE and pkg not in SAFE:
        return None
    result = subprocess.run(
        [PYTHON, "-m", "pip", "install", pkg, "--break-system-packages", "-q"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        return f"pip install {pkg} → OK"
    return None


def _fix_permission_denied(stderr: str, cmd: str) -> str | None:
    """chmod +x the file mentioned in permission denied."""
    m = re.search(r"Permission denied.*?'?([/\w.\-]+\.(?:sh|py|bash))'?", stderr)
    if not m:
        m = re.search(r"([/\w.\-]+\.(?:sh|py|bash)).*[Pp]ermission denied", stderr)
    if not m:
        return None
    path = Path(m.group(1))
    if path.exists():
        path.chmod(path.stat().st_mode | 0o111)
        return f"chmod +x {path}"
    return None


def _fix_connection_refused(stderr: str, cmd: str) -> str | None:
    """For transient connection errors: just wait and retry."""
    if "Connection refused" in stderr or "ECONNREFUSED" in stderr:
        time.sleep(BACKOFF_BASE)
        return "wait 2s (connection refused → retry)"
    return None


# Ordered fixer registry
FIXERS = [
    ("module_not_found",   r"No module named",              _fix_module_not_found),
    ("permission_denied",  r"[Pp]ermission denied",         _fix_permission_denied),
    ("connection_refused", r"[Cc]onnection refused|ECONN",  _fix_connection_refused),
    ("syntax_error",       r"SyntaxError|IndentationError",  None),   # no fix, abort
    ("command_not_found",  r"command not found|No such file", None),  # no fix
]


def classify_error(stderr: str, stdout: str) -> str:
    """Return the first matching error class name or 'generic'."""
    combined = stderr + stdout
    for name, pattern, _ in FIXERS:
        if re.search(pattern, combined):
            return name
    return "generic"


def apply_fix(error_class: str, stderr: str, cmd: str) -> str | None:
    """Apply the fixer for the given error class. Returns fix description or None."""
    for name, _, fixer in FIXERS:
        if name == error_class:
            if fixer is None:
                return None     # unrecoverable
            try:
                return fixer(stderr, cmd)
            except Exception as e:
                return None
    return None


# ── core runner ────────────────────────────────────────────────────────────

def run_once(cmd: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, str, float]:
    """Run cmd, return (exit_code, stdout, stderr, duration_ms)."""
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        duration = (time.time() - t0) * 1000
        return proc.returncode, proc.stdout, proc.stderr, duration
    except subprocess.TimeoutExpired:
        duration = timeout * 1000
        return -99, "", f"TIMEOUT after {timeout}s", duration
    except Exception as e:
        duration = (time.time() - t0) * 1000
        return -1, "", f"ERROR: {e}", duration


def run_with_fixes(
    cmd: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    timeout: int = DEFAULT_TIMEOUT,
    dry_run: bool = False,
) -> RunResult:
    """Run cmd with up to max_attempts, applying heuristic fixes on failure."""
    fix_applied = ""
    notes = ""

    for attempt in range(1, max_attempts + 1):
        if dry_run and attempt == 1:
            print(f"  [DRY-RUN] would run: {cmd[:80]}")
            return RunResult(cmd, 1, 0, "", "", 0.0, "PASS", "", "dry-run")

        exit_code, stdout, stderr, duration_ms = run_once(cmd, timeout)

        if exit_code == 0:
            return RunResult(cmd, attempt, exit_code, stdout, stderr,
                             duration_ms, "PASS", fix_applied, notes)

        if exit_code == -99:
            return RunResult(cmd, attempt, exit_code, stdout, stderr,
                             duration_ms, "TIMEOUT", fix_applied, f"timed out after {timeout}s")

        # FAIL path — try to fix
        error_class = classify_error(stderr, stdout)
        notes = f"error_class={error_class}"

        if error_class in ("syntax_error", "command_not_found"):
            # Unrecoverable — no point retrying
            return RunResult(cmd, attempt, exit_code, stdout, stderr,
                             duration_ms, "FAIL", fix_applied,
                             f"unrecoverable: {error_class}")

        if attempt < max_attempts:
            fix = apply_fix(error_class, stderr, cmd)
            if fix:
                fix_applied = fix
                print(f"  [FIX attempt {attempt}] {fix}")
                time.sleep(BACKOFF_BASE * (attempt - 1))   # gentle backoff
            else:
                # No fix available — plain retry with backoff
                time.sleep(BACKOFF_BASE * attempt)

    return RunResult(cmd, max_attempts, exit_code, stdout, stderr,
                     duration_ms, "FAIL", fix_applied, notes)


# ── memory storage ─────────────────────────────────────────────────────────

def store_result(result: RunResult, agent: str = "winnie", cycle: str = "") -> bool:
    """Store test result in agent-memory.db."""
    if not CLI.exists():
        return False
    status_emoji = "✅" if result.status == "PASS" else "❌"
    body = (
        f"{status_emoji} test-runner: '{result.cmd[:60]}' → {result.status} "
        f"(attempt {result.attempt}, {result.duration_ms:.0f}ms)"
    )
    if result.fix_applied:
        body += f" | fix: {result.fix_applied}"
    if result.notes:
        body += f" | {result.notes}"

    cmd = [
        PYTHON, str(CLI), "store",
        "--agent", agent,
        "--cycle", cycle or datetime.now().strftime("%Y-%m-%d-%H"),
        "--topic", f"test-result:{result.cmd[:40]}",
        "--body", body[:400],
        "--tags", f"test-runner,{result.status.lower()}",
        "--type", "experiential",
        "--context", f"automated test run, exit_code={result.exit_code}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return r.returncode == 0


# ── report formatting ──────────────────────────────────────────────────────

def format_report(suite: SuiteReport, agent: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M EST")
    lines = [
        f"# Test Runner Report — {ts}",
        f"**Agent:** {agent} | **Ran:** {suite.ran} | "
        f"**Passed:** {suite.passed} | **Failed:** {suite.failed} | "
        f"**Total time:** {suite.total_ms:.0f}ms",
        "",
    ]
    for r in suite.results:
        icon = "✅" if r.status == "PASS" else ("⏱" if r.status == "TIMEOUT" else "❌")
        lines.append(f"## {icon} `{r.cmd[:70]}`")
        lines.append(f"- **Status:** {r.status} | **Attempt:** {r.attempt} | **Time:** {r.duration_ms:.0f}ms")
        if r.fix_applied:
            lines.append(f"- **Fix applied:** {r.fix_applied}")
        if r.notes:
            lines.append(f"- **Notes:** {r.notes}")
        if r.status != "PASS" and r.stderr:
            lines.append(f"- **Stderr (last 300c):** `{r.stderr[-300:].strip()}`")
        lines.append("")
    lines += [
        "---",
        f"**Result:** {'ALL PASSED ✅' if suite.failed == 0 else f'{suite.failed} FAILED ❌'}",
    ]
    return "\n".join(lines)


def format_json(suite: SuiteReport) -> dict:
    return {
        "ran": suite.ran,
        "passed": suite.passed,
        "failed": suite.failed,
        "total_ms": round(suite.total_ms, 1),
        "results": [
            {
                "cmd": r.cmd,
                "status": r.status,
                "exit_code": r.exit_code,
                "attempt": r.attempt,
                "duration_ms": round(r.duration_ms, 1),
                "fix_applied": r.fix_applied,
                "notes": r.notes,
            }
            for r in suite.results
        ],
    }


# ── CLI entry ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="test_runner — automated test execution + fix loops")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cmd", help="Single command to run")
    group.add_argument("--suite", help="Path to .txt file with one command per line")
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Seconds per attempt")
    parser.add_argument("--agent", default="winnie", help="Agent name for memory storage")
    parser.add_argument("--cycle", default="", help="Cycle tag for memory entries")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    parser.add_argument("--no-store", action="store_true", help="Skip agent-memory storage")
    parser.add_argument("--out", help="Write report to file path")
    args = parser.parse_args()

    # Build command list
    if args.cmd:
        commands = [args.cmd]
    else:
        suite_path = Path(args.suite)
        if not suite_path.exists():
            print(f"ERROR: suite file not found: {suite_path}", file=sys.stderr)
            sys.exit(1)
        commands = [
            l.strip() for l in suite_path.read_text().splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]

    t_start = time.time()
    results: list[RunResult] = []

    for cmd in commands:
        print(f"\n▶ {cmd[:80]}")
        r = run_with_fixes(cmd, max_attempts=args.max_attempts,
                           timeout=args.timeout, dry_run=args.dry_run)
        results.append(r)
        icon = "✅" if r.status == "PASS" else "❌"
        print(f"  {icon} {r.status} (attempt {r.attempt}, {r.duration_ms:.0f}ms)"
              + (f" | fix: {r.fix_applied}" if r.fix_applied else ""))
        if not args.no_store and not args.dry_run:
            store_result(r, agent=args.agent, cycle=args.cycle)

    total_ms = (time.time() - t_start) * 1000
    passed = sum(1 for r in results if r.status == "PASS")
    failed = len(results) - passed
    suite = SuiteReport(len(results), passed, failed, results, total_ms)

    if args.json:
        output = json.dumps(format_json(suite), indent=2)
    else:
        output = format_report(suite, args.agent)

    if args.out:
        Path(args.out).write_text(output)
        print(f"\nReport written: {args.out}")
    else:
        print(f"\n{output}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
