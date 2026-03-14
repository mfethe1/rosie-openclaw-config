#!/usr/bin/env python3
"""
S-03: Outcome Tracker
Tracks whether self-improvement changes actually helped by comparing
before/after state snapshots and classifying results.

CLI:
  python3 outcome_tracker.py record <agent> <improvement_desc>
  python3 outcome_tracker.py score <improvement_id>
  python3 outcome_tracker.py summary [--agent <agent>]
  python3 outcome_tracker.py snapshot <improvement_id>   # capture after snapshot
  python3 outcome_tracker.py --test
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── paths ──────────────────────────────────────────────────────────────────
SELF_DIR = Path(__file__).parent
LOGS_DIR = SELF_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PENDING_FILE = LOGS_DIR / "outcomes_pending.jsonl"   # improvements awaiting after-snap
CYCLES_DEFAULT = 3


# ── state snapshot ─────────────────────────────────────────────────────────

def _count_errors_today() -> int:
    """Count ERROR lines in today's event log."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    log = LOGS_DIR / f"events-{date_str}.jsonl"
    if not log.exists():
        return 0
    count = 0
    try:
        with log.open() as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    if ev.get("level", "").upper() in ("ERROR", "CRITICAL"):
                        count += 1
                except Exception:
                    pass
    except Exception:
        pass
    return count


def _count_memories() -> int:
    mem_dir = SELF_DIR / "memory"
    if not mem_dir.exists():
        return 0
    return sum(1 for f in mem_dir.rglob("*.md")) + sum(1 for f in mem_dir.rglob("*.jsonl"))


def _avg_cycle_time() -> float:
    """Return average cycle time in seconds from recent events, or 0."""
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        log = LOGS_DIR / f"events-{date_str}.jsonl"
        if not log.exists():
            return 0.0
        times: List[float] = []
        with log.open() as f:
            for line in f:
                try:
                    ev = json.loads(line)
                    if ev.get("event_type") == "cycle_complete" and "duration_s" in ev:
                        times.append(float(ev["duration_s"]))
                except Exception:
                    pass
        return sum(times) / len(times) if times else 0.0
    except Exception:
        return 0.0


def capture_snapshot() -> Dict[str, Any]:
    """Capture a lightweight state snapshot."""
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "error_count": _count_errors_today(),
        "memory_count": _count_memories(),
        "avg_cycle_time_s": _avg_cycle_time(),
    }


# ── outcome classification ──────────────────────────────────────────────────

def classify(before: Dict[str, Any], after: Dict[str, Any]) -> str:
    """
    Classify improvement outcome based on metric deltas.
    Lower errors = POSITIVE, higher cycle time = NEGATIVE, etc.
    """
    scores: List[int] = []

    # error_count: lower is better
    if "error_count" in before and "error_count" in after:
        delta = after["error_count"] - before["error_count"]
        if delta < 0:
            scores.append(1)
        elif delta > 0:
            scores.append(-1)
        else:
            scores.append(0)

    # avg_cycle_time_s: lower is better (0 means unavailable)
    b_ct = before.get("avg_cycle_time_s", 0)
    a_ct = after.get("avg_cycle_time_s", 0)
    if b_ct > 0 and a_ct > 0:
        delta = a_ct - b_ct
        if delta < -0.5:
            scores.append(1)
        elif delta > 0.5:
            scores.append(-1)
        else:
            scores.append(0)

    # memory_count: higher is better (knowledge grows)
    if "memory_count" in before and "memory_count" in after:
        delta = after["memory_count"] - before["memory_count"]
        if delta > 0:
            scores.append(1)
        else:
            scores.append(0)

    if not scores:
        return "NEUTRAL"
    total = sum(scores)
    if total > 0:
        return "POSITIVE"
    elif total < 0:
        return "NEGATIVE"
    return "NEUTRAL"


# ── persistence helpers ────────────────────────────────────────────────────

def _outcomes_log_path() -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_DIR / f"outcomes-{date_str}.jsonl"


def _load_pending() -> List[Dict[str, Any]]:
    if not PENDING_FILE.exists():
        return []
    records: List[Dict[str, Any]] = []
    with PENDING_FILE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def _save_pending(records: List[Dict[str, Any]]) -> None:
    with PENDING_FILE.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _append_outcome(record: Dict[str, Any]) -> None:
    with _outcomes_log_path().open("a") as f:
        f.write(json.dumps(record) + "\n")


# ── core API ───────────────────────────────────────────────────────────────

def record_improvement(agent: str, description: str, cycles: int = CYCLES_DEFAULT) -> str:
    """
    Record a new improvement with a before snapshot.
    Returns the improvement_id.
    """
    imp_id = str(uuid.uuid4())[:8]
    before_snap = capture_snapshot()
    entry = {
        "improvement_id": imp_id,
        "agent": agent,
        "description": description,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "cycles_required": cycles,
        "cycles_elapsed": 0,
        "before": before_snap,
        "status": "PENDING",
    }
    pending = _load_pending()
    pending.append(entry)
    _save_pending(pending)
    # also write to today's outcomes log as PENDING
    _append_outcome(entry)
    return imp_id


def score_improvement(improvement_id: str) -> Optional[Dict[str, Any]]:
    """
    Capture after snapshot for an improvement, classify, and finalize.
    Returns the finalized record or None if not found.
    """
    pending = _load_pending()
    target = None
    remaining = []
    for rec in pending:
        if rec["improvement_id"] == improvement_id:
            target = rec
        else:
            remaining.append(rec)

    if target is None:
        # search historical logs
        return _find_in_logs(improvement_id)

    after_snap = capture_snapshot()
    outcome = classify(target["before"], after_snap)
    target["after"] = after_snap
    target["scored_at"] = datetime.now(timezone.utc).isoformat()
    target["outcome"] = outcome
    target["status"] = "SCORED"

    _save_pending(remaining)
    _append_outcome(target)
    return target


def tick_cycles(improvement_id: str, n: int = 1) -> Optional[Dict[str, Any]]:
    """Increment cycle count; auto-score when cycles_required reached."""
    pending = _load_pending()
    for rec in pending:
        if rec["improvement_id"] == improvement_id:
            rec["cycles_elapsed"] = rec.get("cycles_elapsed", 0) + n
            if rec["cycles_elapsed"] >= rec["cycles_required"]:
                _save_pending([r for r in pending if r["improvement_id"] != improvement_id])
                return score_improvement(improvement_id)
            _save_pending(pending)
            return rec
    return None


def summary(agent: Optional[str] = None) -> Dict[str, Any]:
    """Return aggregated outcome summary across all log files."""
    all_outcomes: List[Dict[str, Any]] = []
    for log_file in sorted(LOGS_DIR.glob("outcomes-*.jsonl")):
        with log_file.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("status") == "SCORED":
                        if agent is None or rec.get("agent") == agent:
                            all_outcomes.append(rec)
                except Exception:
                    pass

    counts = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
    by_agent: Dict[str, Dict[str, int]] = {}
    for rec in all_outcomes:
        outcome = rec.get("outcome", "NEUTRAL")
        counts[outcome] = counts.get(outcome, 0) + 1
        ag = rec.get("agent", "unknown")
        if ag not in by_agent:
            by_agent[ag] = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
        by_agent[ag][outcome] = by_agent[ag].get(outcome, 0) + 1

    total = sum(counts.values())
    return {
        "total_scored": total,
        "counts": counts,
        "by_agent": by_agent,
        "score_rate": round(counts["POSITIVE"] / total, 3) if total > 0 else 0.0,
        "pending_count": len(_load_pending()),
    }


def _find_in_logs(improvement_id: str) -> Optional[Dict[str, Any]]:
    for log_file in sorted(LOGS_DIR.glob("outcomes-*.jsonl"), reverse=True):
        with log_file.open() as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    if rec.get("improvement_id") == improvement_id and rec.get("status") == "SCORED":
                        return rec
                except Exception:
                    pass
    return None


# ── self-test ──────────────────────────────────────────────────────────────

def run_tests() -> bool:
    print("=== outcome_tracker self-test ===")
    ok = True

    # Test capture_snapshot
    snap = capture_snapshot()
    assert "ts" in snap and "error_count" in snap and "memory_count" in snap, "snapshot missing keys"
    print(f"  [OK] capture_snapshot: {snap}")

    # Test classify
    assert classify({"error_count": 5}, {"error_count": 3}) == "POSITIVE"
    assert classify({"error_count": 3}, {"error_count": 5}) == "NEGATIVE"
    assert classify({"error_count": 3}, {"error_count": 3}) == "NEUTRAL"
    print("  [OK] classify logic")

    # Test record → score cycle (using temp files)
    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp())
    global LOGS_DIR, PENDING_FILE
    orig_logs, orig_pending = LOGS_DIR, PENDING_FILE
    LOGS_DIR = tmp
    PENDING_FILE = tmp / "outcomes_pending.jsonl"

    imp_id = record_improvement("test-agent", "Test improvement", cycles=1)
    assert imp_id, "record returned empty id"
    print(f"  [OK] record_improvement -> {imp_id}")

    pending = _load_pending()
    assert any(r["improvement_id"] == imp_id for r in pending), "not in pending"
    print("  [OK] pending saved")

    result = score_improvement(imp_id)
    assert result is not None, "score_improvement returned None"
    assert result["status"] == "SCORED"
    assert result["outcome"] in ("POSITIVE", "NEUTRAL", "NEGATIVE")
    print(f"  [OK] score_improvement -> {result['outcome']}")

    s = summary()
    assert s["total_scored"] == 1
    print(f"  [OK] summary: {s}")

    shutil.rmtree(tmp)
    LOGS_DIR = orig_logs
    PENDING_FILE = orig_pending

    print("=== ALL TESTS PASSED ===")
    return True


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Outcome Tracker - S-03")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    sub = parser.add_subparsers(dest="cmd")

    rec_p = sub.add_parser("record", help="Record a new improvement")
    rec_p.add_argument("agent", help="Agent name")
    rec_p.add_argument("description", help="Description of the improvement")
    rec_p.add_argument("--cycles", type=int, default=CYCLES_DEFAULT,
                       help=f"Cycles before after-snapshot (default: {CYCLES_DEFAULT})")

    score_p = sub.add_parser("score", help="Score an improvement (capture after snapshot)")
    score_p.add_argument("improvement_id", help="Improvement ID")

    tick_p = sub.add_parser("tick", help="Increment cycle count for an improvement")
    tick_p.add_argument("improvement_id")
    tick_p.add_argument("--n", type=int, default=1)

    sum_p = sub.add_parser("summary", help="Show outcome summary")
    sum_p.add_argument("--agent", default=None, help="Filter by agent name")

    args = parser.parse_args()

    if args.test:
        sys.exit(0 if run_tests() else 1)

    if args.cmd == "record":
        imp_id = record_improvement(args.agent, args.description, args.cycles)
        print(json.dumps({"improvement_id": imp_id, "status": "PENDING",
                          "cycles_required": args.cycles}, indent=2))

    elif args.cmd == "score":
        result = score_improvement(args.improvement_id)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"ERROR: improvement_id {args.improvement_id} not found in pending", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "tick":
        result = tick_cycles(args.improvement_id, args.n)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"ERROR: improvement_id {args.improvement_id} not found", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "summary":
        s = summary(args.agent)
        print(json.dumps(s, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
