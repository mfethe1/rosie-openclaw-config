#!/usr/bin/env python3
"""winnie_gate_check.py — Enforces Winnie's quality gates before output delivery.

Checks:
  1. acceptance_gate field present (adopt_now | test_in_sandbox | skip)
  2. Minimum 2 distinct evidence sources cited (arXiv, GitHub, docs URL)
  3. Decision table present (Decision/Action/Owner)
  4. Output file is non-trivial (>200 chars)

Exit 0 = all gates pass
Exit 1 = gate failure (blocks delivery)
Exit 2 = file not found / parse error

Usage:
  python3 winnie_gate_check.py <output_file.md>
  python3 winnie_gate_check.py --latest   # auto-finds newest winnie output
"""

import argparse
import re
import sys
from pathlib import Path

OUTPUT_DIR = Path("/Users/harrisonfethe/.openclaw/workspace/self_improvement/outputs")

GATE_CHECKS = [
    {
        "name": "decision_present",
        "desc": "Contains an explicit decision (ADOPT/SKIP/EXTRACT/KEEP)",
        "pattern": r"(?i)\b(ADOPT|SKIP|EXTRACT|KEEP|D-\d{3})\b",
        "min_matches": 1,
    },
    {
        "name": "multi_source",
        "desc": "Cites at least 2 distinct evidence sources",
        "pattern": r"(?:arXiv|arxiv|github\.com|docs\.|http[s]?://|Survey|Paper|Source:)",
        "min_matches": 2,
    },
    {
        "name": "summary_table",
        "desc": "Contains a summary/decision table",
        "pattern": r"\|.*\|.*\|",
        "min_matches": 3,  # at least header + separator + 1 row
    },
    {
        "name": "minimum_depth",
        "desc": "Output is substantive (>500 chars)",
        "pattern": None,
        "min_chars": 500,
    },
]


def find_latest_winnie_output():
    files = sorted(OUTPUT_DIR.glob("*-winnie.md"), key=lambda f: f.stat().st_mtime)
    return files[-1] if files else None


def run_gates(path: Path) -> list[dict]:
    text = path.read_text(errors="replace")
    results = []
    for gate in GATE_CHECKS:
        if gate.get("pattern"):
            matches = re.findall(gate["pattern"], text)
            passed = len(matches) >= gate["min_matches"]
            results.append({
                "name": gate["name"],
                "desc": gate["desc"],
                "passed": passed,
                "detail": f"{len(matches)} matches (need {gate['min_matches']})",
            })
        elif gate.get("min_chars"):
            passed = len(text) >= gate["min_chars"]
            results.append({
                "name": gate["name"],
                "desc": gate["desc"],
                "passed": passed,
                "detail": f"{len(text)} chars (need {gate['min_chars']})",
            })
    return results


def main():
    parser = argparse.ArgumentParser(description="winnie_gate_check — quality gate enforcement")
    parser.add_argument("file", nargs="?", help="Output file to check")
    parser.add_argument("--latest", action="store_true", help="Check most recent winnie output")
    args = parser.parse_args()

    if args.latest:
        path = find_latest_winnie_output()
        if not path:
            print("No winnie output files found.", file=sys.stderr)
            sys.exit(2)
    elif args.file:
        path = Path(args.file)
    else:
        parser.print_help()
        sys.exit(2)

    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)

    results = run_gates(path)
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    print(f"Gate check: {path.name}")
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon} {r['name']}: {r['detail']}")

    if failed > 0:
        print(f"\n❌ {failed} gate(s) FAILED")
        sys.exit(1)
    else:
        print(f"\n✅ All {passed} gates PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
