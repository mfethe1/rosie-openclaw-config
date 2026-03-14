#!/usr/bin/env python3
"""session_analyzer.py — Analyze OpenClaw cron run history for patterns and insights.

Reads ~/.openclaw/cron/runs/*.jsonl and jobs.json to produce:
- Per-job success/error rates
- Consecutive error streaks (health alerts)
- Duration trends (slow jobs)
- Model performance comparison
- Time-of-day success patterns

Usage:
  python3 session_analyzer.py                     # full report
  python3 session_analyzer.py --health             # health alerts only
  python3 session_analyzer.py --job "Mack*"        # filter by job name glob
  python3 session_analyzer.py --json               # machine-readable output
  python3 session_analyzer.py --days 7             # only last N days
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

CRON_DIR = Path.home() / ".openclaw/cron"
RUNS_DIR = CRON_DIR / "runs"
JOBS_FILE = CRON_DIR / "jobs.json"


def load_jobs() -> dict[str, dict]:
    """Load job definitions keyed by id."""
    if not JOBS_FILE.exists():
        return {}
    data = json.loads(JOBS_FILE.read_text())
    jobs = data if isinstance(data, list) else data.get("jobs", [])
    return {j["id"]: j for j in jobs}


def load_runs(job_id: str, since: datetime | None = None) -> list[dict]:
    """Load run entries for a job, optionally filtered by time."""
    path = RUNS_DIR / f"{job_id}.jsonl"
    if not path.exists():
        return []
    runs = []
    for line in path.read_text().strip().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if since and "timestamp" in entry:
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                if ts < since:
                    continue
            except (ValueError, TypeError):
                pass
        runs.append(entry)
    return runs


def analyze_job(job: dict, runs: list[dict]) -> dict:
    """Analyze a single job's run history."""
    total = len(runs)
    if total == 0:
        return {"name": job.get("name", "?"), "total": 0, "status": "no_data"}

    successes = sum(1 for r in runs if r.get("status") == "success")
    errors = sum(1 for r in runs if r.get("status") == "error")
    timeouts = sum(1 for r in runs if r.get("status") == "timeout")

    # Consecutive errors from tail
    consec_errors = 0
    for r in reversed(runs):
        if r.get("status") == "error":
            consec_errors += 1
        else:
            break

    # Duration stats (if available)
    durations = []
    for r in runs:
        d = r.get("durationMs") or r.get("duration_ms")
        if d and isinstance(d, (int, float)):
            durations.append(d / 1000.0)  # convert to seconds

    # Error messages (deduplicated)
    error_msgs = list({r.get("error", "")[:80] for r in runs if r.get("status") == "error" and r.get("error")})

    # Health classification
    success_rate = successes / total if total > 0 else 0
    if consec_errors >= 5:
        health = "critical"
    elif consec_errors >= 3:
        health = "degraded"
    elif success_rate < 0.5:
        health = "unstable"
    elif success_rate >= 0.9:
        health = "healthy"
    else:
        health = "fair"

    result = {
        "name": job.get("name", "?"),
        "id": job.get("id", "?"),
        "enabled": job.get("enabled", True),
        "model": job.get("payload", {}).get("model", "default"),
        "total_runs": total,
        "successes": successes,
        "errors": errors,
        "timeouts": timeouts,
        "success_rate": round(success_rate, 3),
        "consecutive_errors": consec_errors,
        "health": health,
    }

    if durations:
        result["avg_duration_s"] = round(sum(durations) / len(durations), 1)
        result["max_duration_s"] = round(max(durations), 1)

    if error_msgs:
        result["recent_errors"] = error_msgs[:3]

    return result


def print_report(analyses: list[dict], health_only: bool = False):
    """Print human-readable report."""
    # Sort: critical first, then by error count
    analyses.sort(key=lambda a: (
        {"critical": 0, "degraded": 1, "unstable": 2, "fair": 3, "healthy": 4, "no_data": 5}.get(a.get("health", "no_data"), 5),
        -a.get("consecutive_errors", 0)
    ))

    health_icons = {
        "critical": "🔴", "degraded": "🟠", "unstable": "🟡",
        "fair": "🔵", "healthy": "🟢", "no_data": "⚪"
    }

    # Summary line
    counts = defaultdict(int)
    for a in analyses:
        counts[a.get("health", "no_data")] += 1
    summary_parts = []
    for h in ["critical", "degraded", "unstable", "fair", "healthy", "no_data"]:
        if counts[h]:
            summary_parts.append(f"{health_icons[h]} {counts[h]} {h}")
    print(f"Session Analysis: {' | '.join(summary_parts)}")
    print(f"{'='*70}")

    for a in analyses:
        if health_only and a.get("health") in ("healthy", "fair", "no_data"):
            continue

        icon = health_icons.get(a.get("health", "no_data"), "?")
        name = a.get("name", "?")[:50]
        enabled = "" if a.get("enabled", True) else " [DISABLED]"
        sr = a.get("success_rate", 0)

        print(f"\n{icon} {name}{enabled}")
        if a.get("total_runs", 0) == 0:
            print("   No run data")
            continue

        print(f"   Runs: {a['total_runs']} | Success: {a['successes']} ({sr:.0%}) | Errors: {a['errors']} | Timeouts: {a.get('timeouts', 0)}")

        if a.get("consecutive_errors", 0) > 0:
            print(f"   ⚠️  Consecutive errors: {a['consecutive_errors']}")

        if a.get("avg_duration_s"):
            print(f"   Duration: avg {a['avg_duration_s']}s, max {a['max_duration_s']}s")

        if a.get("model") and a["model"] != "default":
            print(f"   Model: {a['model']}")

        if a.get("recent_errors"):
            for err in a["recent_errors"][:2]:
                print(f"   Error: {err}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze OpenClaw cron session history")
    parser.add_argument("--health", action="store_true", help="Show only unhealthy jobs")
    parser.add_argument("--job", default=None, help="Filter by job name glob (e.g. 'Mack*')")
    parser.add_argument("--days", type=int, default=None, help="Only analyze last N days")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    jobs = load_jobs()
    if not jobs:
        print("No jobs found in", JOBS_FILE)
        return 1

    since = None
    if args.days:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)

    analyses = []
    for job_id, job in jobs.items():
        name = job.get("name", "")
        if args.job and not fnmatch.fnmatch(name, args.job):
            continue
        runs = load_runs(job_id, since)
        analysis = analyze_job(job, runs)
        analyses.append(analysis)

    if args.json:
        print(json.dumps(analyses, indent=2))
    else:
        print_report(analyses, health_only=args.health)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
