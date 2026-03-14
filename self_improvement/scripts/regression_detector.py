#!/usr/bin/env python3
"""
regression_detector.py — Cross-run regression detector for Lenny QA.

Scans fail-reflections.jsonl and eval-log.md for patterns:
1. Same probable_cause appearing in N consecutive or near-consecutive runs
2. FAIL→PASS→FAIL oscillation (fix didn't hold)
3. Same agent failing on same task type repeatedly

Usage:
    python3 regression_detector.py [--threshold 3] [--hours 48] [--json]

Exit codes:
    0 = no regressions detected
    1 = regressions found (prints details)
    2 = error reading inputs
"""

import json
import sys
import collections
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
FAIL_LOG = WORKSPACE / "memory" / "fail-reflections.jsonl"
EVAL_LOG = WORKSPACE / "memory" / "eval-log.md"


def load_fail_entries(hours: int) -> list:
    """Load fail-reflections.jsonl entries within the time window."""
    if not FAIL_LOG.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    entries = []
    for line in FAIL_LOG.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            ts = e.get("timestamp", "")
            if ts:
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    entries.append(e)
        except (json.JSONDecodeError, ValueError):
            continue
    return entries


def load_eval_entries(hours: int) -> list:
    """Parse eval-log.md for recent PASS/FAIL entries."""
    if not EVAL_LOG.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    entries = []
    current = {}
    for line in EVAL_LOG.read_text().split("\n"):
        if line.startswith("## ["):
            if current:
                entries.append(current)
            # Parse: ## [2026-02-23 00:54 EST] | Agent: rosie | Task: sweep-...
            try:
                parts = line.split("|")
                ts_str = parts[0].strip("## [").split("]")[0].strip()
                agent = parts[1].split(":")[1].strip() if len(parts) > 1 else ""
                task = parts[2].split(":")[1].strip() if len(parts) > 2 else ""
                current = {"timestamp": ts_str, "agent": agent, "task": task, "status": ""}
            except (IndexError, ValueError):
                current = {}
        elif "**Status:**" in line and current:
            current["status"] = "PASS" if "PASS" in line else "FAIL" if "FAIL" in line else ""
    if current:
        entries.append(current)
    return entries


def detect_regressions(fail_entries: list, eval_entries: list, threshold: int) -> list:
    """Detect regression patterns."""
    regressions = []

    # Pattern 1: Same probable_cause appearing threshold+ times
    causes = collections.Counter()
    for e in fail_entries:
        cause = e.get("probable_cause", e.get("root_cause", "unknown"))
        # Normalize: strip paths and numbers for grouping
        normalized = cause.split(":")[0].strip() if ":" in cause else cause[:50]
        causes[normalized] += 1

    for cause, count in causes.items():
        if count >= threshold:
            regressions.append({
                "type": "repeat_failure",
                "severity": "CRITICAL" if count >= threshold + 2 else "HIGH",
                "cause": cause,
                "count": count,
                "detail": f"Same failure cause appeared {count} times (threshold: {threshold})",
            })

    # Pattern 2: Same agent+task combo failing repeatedly
    agent_task = collections.Counter()
    for e in fail_entries:
        key = f"{e.get('agent', '?')}:{e.get('task', '?')}"
        agent_task[key] += 1

    for key, count in agent_task.items():
        if count >= threshold:
            regressions.append({
                "type": "agent_task_repeat",
                "severity": "HIGH",
                "cause": key,
                "count": count,
                "detail": f"Agent+task combo failed {count} times",
            })

    # Pattern 3: FAIL→PASS→FAIL oscillation in eval-log (fix didn't hold)
    task_history = collections.defaultdict(list)
    for e in eval_entries:
        if e.get("status") in ("PASS", "FAIL"):
            task_history[f"{e['agent']}:{e['task']}"].append(e["status"])

    for key, statuses in task_history.items():
        if len(statuses) >= 3:
            for i in range(len(statuses) - 2):
                if statuses[i] == "FAIL" and statuses[i + 1] == "PASS" and statuses[i + 2] == "FAIL":
                    regressions.append({
                        "type": "oscillation",
                        "severity": "HIGH",
                        "cause": key,
                        "count": 1,
                        "detail": f"FAIL→PASS→FAIL oscillation detected — fix didn't hold",
                    })
                    break

    return regressions


def main():
    parser = argparse.ArgumentParser(description="Cross-run regression detector")
    parser.add_argument("--threshold", type=int, default=3, help="Min repeat count to flag")
    parser.add_argument("--hours", type=int, default=48, help="Lookback window in hours")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    try:
        fail_entries = load_fail_entries(args.hours)
        eval_entries = load_eval_entries(args.hours)
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        sys.exit(2)

    regressions = detect_regressions(fail_entries, eval_entries, args.threshold)

    if args.json:
        print(json.dumps({
            "regressions": regressions,
            "fail_entries_scanned": len(fail_entries),
            "eval_entries_scanned": len(eval_entries),
            "threshold": args.threshold,
            "hours": args.hours,
        }, indent=2))
    else:
        if regressions:
            print(f"🚨 {len(regressions)} regression(s) detected ({len(fail_entries)} fails, {len(eval_entries)} evals in {args.hours}h):")
            for r in regressions:
                print(f"  [{r['severity']}] {r['type']}: {r['cause']} ({r['count']}x) — {r['detail']}")
        else:
            print(f"✅ No regressions ({len(fail_entries)} fails, {len(eval_entries)} evals in {args.hours}h, threshold={args.threshold})")

    sys.exit(1 if regressions else 0)


if __name__ == "__main__":
    main()
