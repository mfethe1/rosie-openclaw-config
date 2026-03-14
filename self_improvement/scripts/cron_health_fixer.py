#!/usr/bin/env python3
"""cron_health_fixer.py — Auto-repair known-bad cron job configurations.

Fixes:
- channel: "last" → explicit "telegram"
- Legacy/wrong delivery targets → configurable default (env), never hardcoded
- Non-existent models → "anthropic/claude-haiku-4-5"
- Disabled hourly reflect crons → re-enable
- Missing timeoutSeconds → set 45s

Usage:
  python3 cron_health_fixer.py              # fix + report
  python3 cron_health_fixer.py --dry-run    # report only
  python3 cron_health_fixer.py --json       # machine output
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

JOBS_FILE = Path.home() / ".openclaw/cron/jobs.json"
SHARED_STATE_FILE = Path.home() / ".openclaw/workspace/self_improvement/shared-state.json"
DEFAULT_MODEL = "anthropic/claude-haiku-4-5"
BAD_MODELS = {"google-antigravity/gemini-3-flash", "gemini-3-flash", ""}
HOURLY_KEYWORDS = ["Hourly Self-Improvement"]


def _extract_blocked_targets_from_shared_state() -> set[str]:
    """Load known failing delivery targets from shared-state dependency notes."""
    if not SHARED_STATE_FILE.exists():
        return set()
    try:
        state = json.loads(SHARED_STATE_FILE.read_text())
    except json.JSONDecodeError:
        return set()

    blocked: set[str] = set()
    for key in (state.get("dependency_notes") or {}).keys():
        # Example: delivery_failures_5198788775 -> -5198788775
        m = re.search(r"delivery_failures_(\d+)", key)
        if m:
            blocked.add(f"-{m.group(1)}")
    return blocked


def _resolve_default_delivery_to(blocked_targets: set[str]) -> str | None:
    """Resolve optional default delivery target from env, skipping known blocked IDs."""
    candidate = os.environ.get("OPENCLAW_DEFAULT_DELIVERY_TO", "").strip()
    if not candidate or candidate in blocked_targets:
        return None
    return candidate


def fix_jobs(dry_run: bool = False) -> list[dict]:
    if not JOBS_FILE.exists():
        return []

    data = json.loads(JOBS_FILE.read_text())
    jobs = data if isinstance(data, list) else data.get("jobs", [])
    fixes = []
    blocked_targets = _extract_blocked_targets_from_shared_state()
    default_delivery_to = _resolve_default_delivery_to(blocked_targets)

    for j in jobs:
        name = j.get("name", "")
        job_fixes = []

        # Fix delivery
        dl = j.get("delivery", {})
        if dl.get("channel") == "last" or not dl.get("channel"):
            if not dry_run:
                new_delivery = {
                    "mode": dl.get("mode", "silent"),
                    "channel": "telegram",
                }
                existing_to = str(dl.get("to", "")).strip()
                if existing_to and existing_to not in blocked_targets:
                    new_delivery["to"] = existing_to
                elif default_delivery_to:
                    new_delivery["to"] = default_delivery_to
                j["delivery"] = new_delivery
            job_fixes.append("channel:last→telegram")

        to_value = str((j.get("delivery") or {}).get("to", "")).strip()
        if to_value in blocked_targets:
            if not dry_run and default_delivery_to:
                j.setdefault("delivery", {})["to"] = default_delivery_to
                job_fixes.append(f"blocked target:{to_value}→{default_delivery_to}")
            else:
                job_fixes.append(f"blocked target flagged:{to_value}")

        # Legacy bad group mapping: only rewrite when a safe configured target exists
        if to_value == "-1003753060481" and default_delivery_to:
            if not dry_run:
                j.setdefault("delivery", {})["to"] = default_delivery_to
            job_fixes.append(f"legacy group ID→{default_delivery_to}")

        # Fix bad models
        model = j.get("payload", {}).get("model", "")
        if model in BAD_MODELS or "gemini-3-flash" in model:
            if not dry_run:
                j.setdefault("payload", {})["model"] = DEFAULT_MODEL
            job_fixes.append(f"bad model:{model}→{DEFAULT_MODEL}")

        # Re-enable hourly reflects
        if any(kw in name for kw in HOURLY_KEYWORDS):
            if not j.get("enabled", True):
                if not dry_run:
                    j["enabled"] = True
                job_fixes.append("re-enabled")
            # Ensure timeout
            ts = j.get("payload", {}).get("timeoutSeconds", 0)
            if ts < 30:
                if not dry_run:
                    j.setdefault("payload", {})["timeoutSeconds"] = 45
                job_fixes.append(f"timeout:{ts}→45")

        if job_fixes:
            fixes.append({"name": name[:60], "fixes": job_fixes})

    if fixes and not dry_run:
        if isinstance(data, dict):
            data["jobs"] = jobs
            JOBS_FILE.write_text(json.dumps(data, indent=2) + "\n")
        else:
            JOBS_FILE.write_text(json.dumps(jobs, indent=2) + "\n")

    return fixes


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-repair cron job configs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    fixes = fix_jobs(dry_run=args.dry_run)

    if args.json:
        print(json.dumps({"fixed": len(fixes), "dry_run": args.dry_run, "details": fixes}))
    else:
        if fixes:
            action = "Would fix" if args.dry_run else "Fixed"
            for f in fixes:
                print(f"  {action}: {f['name']} — {', '.join(f['fixes'])}")
            print(f"\n{action} {len(fixes)} job(s)")
        else:
            print("✅ All cron jobs healthy")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
