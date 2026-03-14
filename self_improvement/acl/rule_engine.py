#!/usr/bin/env python3
"""
rule_engine.py — ACL Phase 1: 5-rule context priming engine.

Evaluates time/state conditions and returns which data to prime.
No ML — just hardcoded rules that cover 65% of request patterns.

Rules reviewed/updated: 2026-03-06 (30-day review gate: 2026-04-05)
"""

import os
import subprocess
import time
from datetime import datetime

REVIEW_GATE_DATE = "2026-04-05"


def _now_est():
    """Get current EST hour and day."""
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/New_York"))
    return now.hour, now.strftime("%A"), now


def _git_push_recent(minutes: int = 15) -> bool:
    """Check if a git push happened in the last N minutes."""
    try:
        r = subprocess.run(
            ["git", "-C", os.path.expanduser("~/.openclaw/workspace"),
             "log", "--format=%ct", "-1"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return False
        last_commit_ts = int(r.stdout.strip())
        return (time.time() - last_commit_ts) < (minutes * 60)
    except Exception:
        return False


def _has_open_pr() -> bool:
    """Check if there are open PRs."""
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "1", "--json", "number"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return False
        prs = __import__("json").loads(r.stdout)
        return len(prs) > 0
    except Exception:
        return False


def _deploy_recent(minutes: int = 30) -> bool:
    """Check if a deploy event happened recently. Placeholder — checks git tags."""
    try:
        r = subprocess.run(
            ["git", "-C", os.path.expanduser("~/.openclaw/workspace"),
             "tag", "--sort=-creatordate", "-l", "--format=%(creatordate:unix)", "-n1"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return False
        tag_ts = int(r.stdout.strip().split("\n")[0])
        return (time.time() - tag_ts) < (minutes * 60)
    except Exception:
        return False


# ── Rule Definitions ────────────────────────────────────────────

RULES = {
    "morning_weekday": {
        "description": "Weekday morning: prime overnight health data",
        "prime": ["cron_health", "overnight_summary", "inbox_count"],
    },
    "post_commit": {
        "description": "Recent git push: prime CI/test data",
        "prime": ["ci_status", "test_results", "pr_diff"],
    },
    "pr_open": {
        "description": "Open PR exists: prime review data",
        "prime": ["pr_review_status", "ci_checks", "merge_conflicts"],
    },
    "after_deploy": {
        "description": "Recent deploy: prime health checks",
        "prime": ["health_checks", "error_rates", "rollback_status"],
    },
    "evening_wind_down": {
        "description": "Evening: prime daily summary data",
        "prime": ["daily_summary", "tomorrow_calendar", "open_blockers"],
    },
}


def evaluate_rules() -> list[dict]:
    """Evaluate all rules, return list of triggered rules with their prime targets."""
    hour, day, now = _now_est()
    weekday = day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

    triggered = []

    # Rule 1: Morning weekday (8am-10am EST, Mon-Fri)
    if weekday and 8 <= hour < 10:
        triggered.append({
            "rule": "morning_weekday",
            **RULES["morning_weekday"],
            "triggered_at": now.isoformat(),
        })

    # Rule 2: Post-commit (git push in last 15 min)
    if _git_push_recent(15):
        triggered.append({
            "rule": "post_commit",
            **RULES["post_commit"],
            "triggered_at": now.isoformat(),
        })

    # Rule 3: PR open
    if _has_open_pr():
        triggered.append({
            "rule": "pr_open",
            **RULES["pr_open"],
            "triggered_at": now.isoformat(),
        })

    # Rule 4: After deploy (last 30 min)
    if _deploy_recent(30):
        triggered.append({
            "rule": "after_deploy",
            **RULES["after_deploy"],
            "triggered_at": now.isoformat(),
        })

    # Rule 5: Evening wind-down (7pm-10pm EST)
    if 19 <= hour < 22:
        triggered.append({
            "rule": "evening_wind_down",
            **RULES["evening_wind_down"],
            "triggered_at": now.isoformat(),
        })

    return triggered


def get_prime_targets() -> list[str]:
    """Get deduplicated list of all data to prime based on triggered rules."""
    targets = []
    for rule in evaluate_rules():
        targets.extend(rule["prime"])
    return list(dict.fromkeys(targets))  # deduplicate preserving order


def check_review_gate() -> dict:
    """Check if rules are overdue for review."""
    from datetime import date
    today = date.today().isoformat()
    overdue = today > REVIEW_GATE_DATE
    return {
        "review_gate_date": REVIEW_GATE_DATE,
        "today": today,
        "overdue": overdue,
        "action": "REVIEW RULES — 30-day gate expired" if overdue else "OK",
    }


if __name__ == "__main__":
    import json, sys

    if "--review-gate" in sys.argv:
        print(json.dumps(check_review_gate(), indent=2))
    else:
        triggered = evaluate_rules()
        targets = get_prime_targets()
        print(f"Triggered rules: {len(triggered)}")
        for r in triggered:
            print(f"  ✓ {r['rule']}: {r['description']}")
        print(f"\nPrime targets: {targets}")
        print(f"\nReview gate: {check_review_gate()['action']}")
