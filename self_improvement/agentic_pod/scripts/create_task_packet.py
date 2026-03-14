#!/usr/bin/env python3
"""
create_task_packet.py — Generate task packet markdown from CLI args.
stdlib only, Python 3.9+

Usage:
    python3 create_task_packet.py --task-id TASK-001 --agent plumber \
        --title "Wire Stripe webhook" --repo https://github.com/org/repo \
        --output task_packets/TASK-001.md

    # Quick test
    python3 create_task_packet.py --test
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


VALID_AGENTS = {"plumber", "reader", "red_team"}

TEMPLATE = """\
# Task Packet: {task_id}
**Agent:** {agent}
**Title:** {title}
**Created:** {created_at}
**Status:** READY

---

## [SECTION 1] Repo Map

<!-- Required: list relevant files/dirs the agent needs to read/modify -->
<!-- Format: path :: purpose -->

- `src/` :: Primary source tree (edit target)
- `tests/` :: Test suite (must not regress)
- `docs/` :: Reference only (read-only)

**Repo:** {repo}
**Branch:** {branch}
**Base commit:** (fill before execution)

---

## [SECTION 2] API Docs & External References

| API / Resource | URL | Auth Method | Rate Limit |
|---------------|-----|-------------|-----------|
| (fill in) | | | |

**Env vars required:**
```
# List all required env vars here — never hardcode values
```

---

## [SECTION 3] Constraints

### Must NOT
- [ ] Modify files outside declared repo map without Sentinel approval
- [ ] Commit secrets or API keys to any file
- [ ] Delete existing tests
- [ ] Call external endpoints not listed in Section 2

### Must
- [ ] Run linter before submitting
- [ ] Pass existing test suite without regressions
- [ ] Leave audit comment: `# AGENT: {agent} {task_id}`

### Scope boundary
> {scope}

---

## [SECTION 4] Definition of Done

- [ ] Feature works end-to-end in staging
- [ ] All existing tests pass
- [ ] New tests cover happy path and ≥ 2 failure modes
- [ ] No linter errors
- [ ] PR description references task packet ID: {task_id}
- [ ] Domain Expert sign-off
- [ ] No secrets committed (gitleaks clean)

---

## [SECTION 5] Test Matrix

| Test Case | Input | Expected Output | Pass Criteria |
|-----------|-------|----------------|---------------|
| Happy path | (fill in) | (fill in) | (fill in) |
| Error / failure mode 1 | (fill in) | (fill in) | (fill in) |
| Edge case | (fill in) | (fill in) | (fill in) |

---

## [SECTION 6] Token Budget

| Phase | Allotted Tokens | Hard Limit |
|-------|----------------|-----------|
| Context ingestion | 20,000 | 30,000 |
| Execution | 30,000 | 50,000 |
| Review / self-check | 10,000 | 15,000 |
| **Total** | **60,000** | **95,000** |

**On budget overrun:** Stop, emit `BUDGET_EXCEEDED`, report state to Sentinel.

---

## [SECTION 7] Rollback Plan

**Rollback command:**
```bash
git revert HEAD --no-edit && git push origin main
```

**Data rollback:** N/A — update as needed.

---

## [SECTION 8] Sign-offs

| Role | Name | Timestamp | Status |
|------|------|-----------|--------|
| Domain Expert | | | ☐ Approved / ☐ Rejected |
| Sentinel | | | ☐ Approved / ☐ Rejected |
| Orchestrator | | | ☐ Go / ☐ No-Go |

**Notes:** {notes}
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a task packet markdown file from CLI args.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 create_task_packet.py \\
      --task-id TASK-001 --agent plumber \\
      --title "Wire Stripe webhook to Issuesflow billing" \\
      --repo https://github.com/mfethe/issuesflow \\
      --output task_packets/TASK-001.md

  python3 create_task_packet.py --test
        """,
    )
    p.add_argument("--task-id", required=False, help="Task ID, e.g. TASK-001")
    p.add_argument(
        "--agent",
        required=False,
        choices=list(VALID_AGENTS),
        help="Agent role: plumber | reader | red_team",
    )
    p.add_argument("--title", required=False, help="Short task title")
    p.add_argument("--repo", default="(not specified)", help="Repo URL or name")
    p.add_argument(
        "--branch",
        default="feature/{task_id}",
        help="Branch name (default: feature/<task-id>)",
    )
    p.add_argument("--scope", default="(fill in scope boundary)", help="Scope description")
    p.add_argument("--notes", default="", help="Additional notes for sign-off section")
    p.add_argument(
        "--output",
        required=False,
        help="Output file path (default: task_packets/<task-id>.md)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print to stdout, do not write file")
    p.add_argument("--test", action="store_true", help="Run self-test and exit")
    return p.parse_args()


def generate_packet(
    task_id: str,
    agent: str,
    title: str,
    repo: str = "(not specified)",
    branch: str = "",
    scope: str = "(fill in scope boundary)",
    notes: str = "",
    created_at: str = "",
) -> str:
    if not created_at:
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not branch:
        branch = f"feature/{task_id.lower()}"
    return TEMPLATE.format(
        task_id=task_id,
        agent=agent,
        title=title,
        repo=repo,
        branch=branch,
        scope=scope,
        notes=notes,
        created_at=created_at,
    )


def run_self_test() -> bool:
    """Run basic self-tests. Returns True if all pass."""
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

    print("Running create_task_packet self-tests...")

    # Test 1: generate_packet produces valid markdown
    packet = generate_packet(
        task_id="TASK-TEST",
        agent="plumber",
        title="Test task",
        repo="https://github.com/test/repo",
        created_at="2026-01-01T00:00:00Z",
    )
    check("generate_packet returns string", isinstance(packet, str))
    check("task_id in output", "TASK-TEST" in packet)
    check("agent in output", "plumber" in packet)
    check("title in output", "Test task" in packet)
    check("[SECTION 1] present", "[SECTION 1]" in packet)
    check("[SECTION 2] present", "[SECTION 2]" in packet)
    check("[SECTION 3] present", "[SECTION 3]" in packet)
    check("[SECTION 4] present", "[SECTION 4]" in packet)
    check("[SECTION 5] present", "[SECTION 5]" in packet)
    check("[SECTION 6] present", "[SECTION 6]" in packet)
    check("[SECTION 7] present", "[SECTION 7]" in packet)
    check("[SECTION 8] present", "[SECTION 8]" in packet)

    # Test 2: READY status default
    check("status is READY", "**Status:** READY" in packet)

    # Test 3: agent audit comment format
    check("audit comment template present", "# AGENT: plumber TASK-TEST" in packet)

    # Test 4: branch default
    packet2 = generate_packet(task_id="TASK-002", agent="reader", title="Read blueprints")
    check("default branch uses task-id", "feature/task-002" in packet2)

    # Test 5: all valid agents accepted
    for ag in VALID_AGENTS:
        p = generate_packet(task_id="T", agent=ag, title="t")
        check(f"agent '{ag}' renders correctly", ag in p)

    # Test 6: dry-run via write to /dev/null equivalent (StringIO)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(generate_packet("T-DRY", "red_team", "Dry run test"))
    check("dry-run output non-empty", len(buf.getvalue()) > 0)

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main() -> int:
    args = parse_args()

    if args.test:
        ok = run_self_test()
        return 0 if ok else 1

    # Validate required fields when not in test mode
    missing = []
    if not args.task_id:
        missing.append("--task-id")
    if not args.agent:
        missing.append("--agent")
    if not args.title:
        missing.append("--title")
    if missing:
        print(f"Error: missing required arguments: {', '.join(missing)}", file=sys.stderr)
        return 1

    branch = args.branch.replace("{task_id}", args.task_id.lower())
    packet = generate_packet(
        task_id=args.task_id,
        agent=args.agent,
        title=args.title,
        repo=args.repo,
        branch=branch,
        scope=args.scope,
        notes=args.notes,
    )

    if args.dry_run:
        print(packet)
        return 0

    output_path = args.output or f"task_packets/{args.task_id}.md"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.exists():
        print(f"Warning: {out} already exists. Overwrite? [y/N] ", end="", flush=True)
        answer = sys.stdin.readline().strip().lower()
        if answer != "y":
            print("Aborted.")
            return 1

    out.write_text(packet, encoding="utf-8")
    print(f"Created: {out}")
    print(f"Task ID: {args.task_id} | Agent: {args.agent} | Title: {args.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
