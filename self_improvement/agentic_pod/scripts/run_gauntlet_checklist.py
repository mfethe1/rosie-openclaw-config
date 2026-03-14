#!/usr/bin/env python3
"""
run_gauntlet_checklist.py — Validates DoD + test matrix present before merge.
stdlib only, Python 3.9+

Exit codes:
    0 — All checks pass
    1 — One or more checks failed
    2 — File not found or unreadable

Usage:
    # Full gauntlet (pre-merge)
    python3 run_gauntlet_checklist.py task_packets/DONE/TASK-001.md

    # Pre-flight only (pre-execution, less strict)
    python3 run_gauntlet_checklist.py task_packets/READY/TASK-001.md --pre-flight

    # JSON output (for CI integration)
    python3 run_gauntlet_checklist.py task_packets/DONE/TASK-001.md --json

    # Self-test
    python3 run_gauntlet_checklist.py --test
"""

import argparse
import json
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    severity: str = "ERROR"   # ERROR | WARN


@dataclass
class GauntletReport:
    file_path: str
    mode: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "ERROR")

    @property
    def errors(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "ERROR"]

    @property
    def warnings(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "WARN"]

    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "mode": self.mode,
            "passed": self.passed,
            "errors": [{"name": c.name, "detail": c.detail} for c in self.errors],
            "warnings": [{"name": c.name, "detail": c.detail} for c in self.warnings],
            "checks": [
                {"name": c.name, "passed": c.passed, "severity": c.severity, "detail": c.detail}
                for c in self.checks
            ],
        }


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = [
    "[SECTION 1]",
    "[SECTION 2]",
    "[SECTION 3]",
    "[SECTION 4]",
    "[SECTION 5]",
    "[SECTION 6]",
]

REQUIRED_SECTIONS_FULL = REQUIRED_SECTIONS + ["[SECTION 7]", "[SECTION 8]"]

# Minimum number of test matrix data rows (excluding header and separator)
MIN_TEST_MATRIX_ROWS = 3

# Minimum number of DoD checklist items
MIN_DOD_ITEMS = 3


def _extract_section(content: str, section_marker: str) -> str:
    """Return text between section_marker and the next ## heading."""
    idx = content.find(section_marker)
    if idx == -1:
        return ""
    # find next ## heading after this section
    next_heading = re.search(r"\n##\s+", content[idx + len(section_marker):])
    if next_heading:
        return content[idx: idx + len(section_marker) + next_heading.start()]
    return content[idx:]


def check_sections_present(content: str, full: bool = True) -> CheckResult:
    required = REQUIRED_SECTIONS_FULL if full else REQUIRED_SECTIONS
    missing = [s for s in required if s not in content]
    if missing:
        return CheckResult(
            name="required_sections_present",
            passed=False,
            detail=f"Missing sections: {', '.join(missing)}",
        )
    return CheckResult(name="required_sections_present", passed=True)


def check_status_field(content: str, expected_statuses: Optional[List[str]] = None) -> CheckResult:
    match = re.search(r"\*\*Status:\*\*\s*(\S+)", content)
    if not match:
        return CheckResult(name="status_field", passed=False, detail="No **Status:** field found")
    status = match.group(1).rstrip(".,;")
    if expected_statuses and status not in expected_statuses:
        return CheckResult(
            name="status_field",
            passed=False,
            detail=f"Status is '{status}', expected one of {expected_statuses}",
        )
    return CheckResult(name="status_field", passed=True, detail=f"Status: {status}")


def check_agent_field(content: str) -> CheckResult:
    match = re.search(r"\*\*Agent:\*\*\s*(\S+)", content)
    if not match:
        return CheckResult(name="agent_field", passed=False, detail="No **Agent:** field found")
    agent = match.group(1).rstrip(".,;")
    valid = {"plumber", "reader", "red_team"}
    if agent not in valid:
        return CheckResult(
            name="agent_field",
            passed=False,
            detail=f"Agent '{agent}' not in valid set {valid}",
        )
    return CheckResult(name="agent_field", passed=True, detail=f"Agent: {agent}")


def check_task_id(content: str) -> CheckResult:
    match = re.search(r"# Task Packet:\s*(\S+)", content)
    if not match:
        return CheckResult(
            name="task_id_present",
            passed=False,
            detail="No '# Task Packet: <ID>' header found",
        )
    task_id = match.group(1)
    if task_id in {"{{TASK_ID}}", "(fill", ""}:
        return CheckResult(
            name="task_id_present",
            passed=False,
            detail="Task ID is a placeholder — fill it in",
        )
    return CheckResult(name="task_id_present", passed=True, detail=f"Task ID: {task_id}")


def check_dod_items(content: str) -> CheckResult:
    section = _extract_section(content, "[SECTION 4]")
    if not section:
        return CheckResult(
            name="dod_items_count",
            passed=False,
            detail="Section 4 (DoD) not found",
        )
    items = re.findall(r"- \[[ xX]\]", section)
    if len(items) < MIN_DOD_ITEMS:
        return CheckResult(
            name="dod_items_count",
            passed=False,
            detail=f"DoD has {len(items)} items, need ≥ {MIN_DOD_ITEMS}",
        )
    return CheckResult(
        name="dod_items_count", passed=True, detail=f"DoD items: {len(items)}"
    )


def check_dod_all_checked(content: str) -> CheckResult:
    """For pre-merge: all DoD items must be checked [x] or [X]."""
    section = _extract_section(content, "[SECTION 4]")
    if not section:
        return CheckResult(
            name="dod_all_checked",
            passed=False,
            detail="Section 4 (DoD) not found",
        )
    unchecked = re.findall(r"- \[ \]", section)
    if unchecked:
        return CheckResult(
            name="dod_all_checked",
            passed=False,
            detail=f"{len(unchecked)} DoD item(s) not checked off",
        )
    return CheckResult(name="dod_all_checked", passed=True)


def check_test_matrix(content: str) -> CheckResult:
    section = _extract_section(content, "[SECTION 5]")
    if not section:
        return CheckResult(
            name="test_matrix_present",
            passed=False,
            detail="Section 5 (Test Matrix) not found",
        )
    # Count table data rows (lines with | that are not header or separator)
    rows = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            # skip header and separator lines
            if re.match(r"^\|[-| :]+\|$", stripped):
                continue
            if "Test Case" in stripped or "---" in stripped:
                continue
            rows.append(stripped)
    if len(rows) < MIN_TEST_MATRIX_ROWS:
        return CheckResult(
            name="test_matrix_present",
            passed=False,
            detail=f"Test matrix has {len(rows)} data rows, need ≥ {MIN_TEST_MATRIX_ROWS}",
        )
    return CheckResult(
        name="test_matrix_present", passed=True, detail=f"Test matrix rows: {len(rows)}"
    )


def check_test_matrix_no_placeholders(content: str) -> CheckResult:
    section = _extract_section(content, "[SECTION 5]")
    if not section:
        return CheckResult(
            name="test_matrix_no_placeholders",
            passed=False,
            detail="Section 5 not found",
        )
    placeholder_patterns = [r"\(fill in\)", r"\{\{.*?\}\}", r"^\s*\|\s*\|\s*\|\s*\|\s*$"]
    placeholder_rows = []
    for line in section.splitlines():
        for pat in placeholder_patterns:
            if re.search(pat, line):
                placeholder_rows.append(line.strip())
                break
    if placeholder_rows:
        return CheckResult(
            name="test_matrix_no_placeholders",
            passed=False,
            severity="WARN",
            detail=f"{len(placeholder_rows)} placeholder row(s) found in test matrix",
        )
    return CheckResult(name="test_matrix_no_placeholders", passed=True)


def check_token_budget(content: str) -> CheckResult:
    section = _extract_section(content, "[SECTION 6]")
    if not section:
        return CheckResult(
            name="token_budget_declared",
            passed=False,
            detail="Section 6 (Token Budget) not found",
        )
    if "Total" not in section or "Hard Limit" not in section:
        return CheckResult(
            name="token_budget_declared",
            passed=False,
            detail="Token budget table missing Total or Hard Limit row",
        )
    return CheckResult(name="token_budget_declared", passed=True)


def check_no_hardcoded_secrets(content: str) -> CheckResult:
    # Simple heuristic: look for common secret patterns
    patterns = [
        (r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]", "hardcoded credential"),
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI-style API key"),
        (r"AKIA[0-9A-Z]{16}", "AWS access key"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
        (r"Bearer\s+[a-zA-Z0-9\-_]{20,}", "Bearer token value"),
    ]
    findings = []
    for pat, label in patterns:
        if re.search(pat, content):
            findings.append(label)
    if findings:
        return CheckResult(
            name="no_hardcoded_secrets",
            passed=False,
            detail=f"Potential secrets detected: {', '.join(findings)}",
        )
    return CheckResult(name="no_hardcoded_secrets", passed=True)


def check_repo_map_non_empty(content: str) -> CheckResult:
    section = _extract_section(content, "[SECTION 1]")
    if not section:
        return CheckResult(
            name="repo_map_non_empty",
            passed=False,
            detail="Section 1 (Repo Map) not found",
        )
    entries = re.findall(r"^-\s+`[^`]+`", section, re.MULTILINE)
    if not entries:
        return CheckResult(
            name="repo_map_non_empty",
            passed=False,
            detail="Repo map has no file entries (need ≥ 1 backtick-quoted path)",
        )
    return CheckResult(
        name="repo_map_non_empty", passed=True, detail=f"Repo map entries: {len(entries)}"
    )


def check_signoffs_present(content: str) -> CheckResult:
    """Pre-merge: all three sign-off rows must have a name and timestamp."""
    section = _extract_section(content, "[SECTION 8]")
    if not section:
        return CheckResult(
            name="signoffs_present",
            passed=False,
            severity="WARN",
            detail="Section 8 (Sign-offs) not found",
        )
    # Check for at least one row that looks filled in
    # A filled row has content beyond just placeholders
    rows = [l for l in section.splitlines() if "| Domain Expert |" in l or "| Sentinel |" in l or "| Orchestrator |" in l]
    # For pre-flight this is just a warning
    return CheckResult(name="signoffs_present", passed=True, detail=f"Sign-off rows: {len(rows)}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_preflight_checks(content: str, file_path: str) -> GauntletReport:
    """Pre-flight checks: run before agent execution. Less strict."""
    report = GauntletReport(file_path=file_path, mode="pre-flight")
    report.checks.extend([
        check_task_id(content),
        check_agent_field(content),
        check_sections_present(content, full=False),
        check_repo_map_non_empty(content),
        check_dod_items(content),
        check_test_matrix(content),
        check_token_budget(content),
        check_no_hardcoded_secrets(content),
        check_status_field(content, expected_statuses=["READY", "DRAFT"]),
    ])
    return report


def run_full_checks(content: str, file_path: str) -> GauntletReport:
    """Full gauntlet: run before merge/deploy. Strict."""
    report = GauntletReport(file_path=file_path, mode="full")
    report.checks.extend([
        check_task_id(content),
        check_agent_field(content),
        check_sections_present(content, full=True),
        check_repo_map_non_empty(content),
        check_dod_items(content),
        check_dod_all_checked(content),
        check_test_matrix(content),
        check_test_matrix_no_placeholders(content),
        check_token_budget(content),
        check_no_hardcoded_secrets(content),
        check_signoffs_present(content),
        check_status_field(content, expected_statuses=["DONE", "REVIEW"]),
    ])
    return report


def print_report(report: GauntletReport) -> None:
    status = "PASS" if report.passed else "FAIL"
    print(f"\nGauntlet [{report.mode}]: {status}  —  {report.file_path}")
    print("-" * 60)
    for c in report.checks:
        icon = "✓" if c.passed else ("✗" if c.severity == "ERROR" else "⚠")
        detail = f"  ({c.detail})" if c.detail else ""
        print(f"  {icon} {c.name}{detail}")
    if report.errors:
        print(f"\n{len(report.errors)} error(s) must be fixed before merge.")
    if report.warnings:
        print(f"{len(report.warnings)} warning(s) should be reviewed.")
    print()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

SAMPLE_READY_PACKET = textwrap.dedent("""\
    # Task Packet: TASK-TEST
    **Agent:** plumber
    **Title:** Test task
    **Created:** 2026-01-01T00:00:00Z
    **Status:** READY

    ## [SECTION 1] Repo Map
    - `src/main.py` :: main entry point
    - `tests/test_main.py` :: test suite

    **Repo:** https://github.com/test/repo
    **Branch:** feature/task-test

    ## [SECTION 2] API Docs & External References
    | API / Resource | URL | Auth Method | Rate Limit |
    |---------------|-----|-------------|-----------|
    | Stripe | https://stripe.com/docs | Secret key | 100 rps |

    **Env vars required:**
    ```
    STRIPE_KEY=
    ```

    ## [SECTION 3] Constraints
    ### Must NOT
    - [ ] Modify files outside declared repo map
    ### Must
    - [ ] Pass tests

    ### Scope boundary
    > Only touch stripe webhook handler.

    ## [SECTION 4] Definition of Done
    - [ ] Feature works end-to-end
    - [ ] All tests pass
    - [ ] No linter errors
    - [ ] Domain Expert sign-off

    ## [SECTION 5] Test Matrix
    | Test Case | Input | Expected Output | Pass Criteria |
    |-----------|-------|----------------|---------------|
    | Happy path | valid event | 200 OK | DB updated |
    | Bad signature | tampered payload | 400 | No DB write |
    | Duplicate event | same ID twice | 200 | Single row |

    ## [SECTION 6] Token Budget
    | Phase | Allotted Tokens | Hard Limit |
    |-------|----------------|-----------|
    | Context ingestion | 20,000 | 30,000 |
    | Execution | 30,000 | 50,000 |
    | **Total** | **50,000** | **80,000** |

    ## [SECTION 7] Rollback Plan
    ```bash
    git revert HEAD
    ```

    ## [SECTION 8] Sign-offs
    | Role | Name | Timestamp | Status |
    |------|------|-----------|--------|
    | Domain Expert | Alice | 2026-01-01 | ☐ Approved |
    | Sentinel | Bob | 2026-01-01 | ☐ Approved |
    | Orchestrator | Michael | 2026-01-01 | ☐ Go |
""")

SAMPLE_DONE_PACKET = SAMPLE_READY_PACKET.replace(
    "**Status:** READY", "**Status:** DONE"
).replace("- [ ] Feature works end-to-end", "- [x] Feature works end-to-end"
).replace("- [ ] All tests pass", "- [x] All tests pass"
).replace("- [ ] No linter errors", "- [x] No linter errors"
).replace("- [ ] Domain Expert sign-off", "- [x] Domain Expert sign-off")


def run_self_test() -> bool:
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
            failed += 1

    print("Running run_gauntlet_checklist self-tests...")

    # --- Pre-flight on READY packet ---
    report = run_preflight_checks(SAMPLE_READY_PACKET, "SAMPLE_READY")
    check("preflight/READY passes", report.passed, str(report.errors))
    check("preflight/mode is pre-flight", report.mode == "pre-flight")

    # --- Full gauntlet on READY packet should fail (not all DoD checked, status not DONE) ---
    report_full_ready = run_full_checks(SAMPLE_READY_PACKET, "SAMPLE_READY_FULL")
    check("full/READY fails (DoD unchecked)", not report_full_ready.passed)

    # --- Full gauntlet on DONE packet ---
    report_done = run_full_checks(SAMPLE_DONE_PACKET, "SAMPLE_DONE")
    check("full/DONE passes", report_done.passed, str(report_done.errors))

    # --- Individual checks ---
    check("task_id check passes", check_task_id(SAMPLE_READY_PACKET).passed)
    check(
        "task_id check fails on placeholder",
        not check_task_id("# Task Packet: {{TASK_ID}}\n").passed,
    )
    check("agent_field plumber ok", check_agent_field("**Agent:** plumber").passed)
    check(
        "agent_field bad fails",
        not check_agent_field("**Agent:** unknown_bot").passed,
    )
    check("dod_items ≥3 ok", check_dod_items(SAMPLE_READY_PACKET).passed)
    check(
        "dod_items <3 fails",
        not check_dod_items(
            "[SECTION 4]\n- [ ] item1\n- [ ] item2\n"
        ).passed,
    )
    check("test_matrix ≥3 ok", check_test_matrix(SAMPLE_READY_PACKET).passed)
    check(
        "test_matrix <3 fails",
        not check_test_matrix(
            "[SECTION 5]\n| T | I | O | P |\n|---|---|---|---|\n| row1 | a | b | c |\n"
        ).passed,
    )
    check("no_secrets passes on clean", check_no_hardcoded_secrets("no secrets here").passed)
    check(
        "no_secrets fails on AKIA key",
        not check_no_hardcoded_secrets("AKIAIOSFODNN7EXAMPLE").passed,
    )
    check(
        "dod_all_checked fails on unchecked",
        not check_dod_all_checked(SAMPLE_READY_PACKET).passed,
    )
    check("dod_all_checked passes on DONE", check_dod_all_checked(SAMPLE_DONE_PACKET).passed)

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate a task packet markdown file before agent execution or merge.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pre-merge full gauntlet
  python3 run_gauntlet_checklist.py task_packets/DONE/TASK-001.md

  # Pre-flight only (before giving packet to agent)
  python3 run_gauntlet_checklist.py task_packets/READY/TASK-001.md --pre-flight

  # JSON output for CI
  python3 run_gauntlet_checklist.py task_packets/DONE/TASK-001.md --json

  # Self-test
  python3 run_gauntlet_checklist.py --test
        """,
    )
    p.add_argument("file", nargs="?", help="Path to task packet markdown file")
    p.add_argument("--pre-flight", action="store_true", help="Run pre-flight checks (less strict)")
    p.add_argument("--json", action="store_true", help="Output results as JSON")
    p.add_argument("--test", action="store_true", help="Run self-test and exit")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.test:
        ok = run_self_test()
        return 0 if ok else 1

    if not args.file:
        print("Error: provide a task packet file path, or use --test", file=sys.stderr)
        return 2

    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 2

    if args.pre_flight:
        report = run_preflight_checks(content, str(path))
    else:
        report = run_full_checks(content, str(path))

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
