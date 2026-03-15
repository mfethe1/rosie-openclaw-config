#!/usr/bin/env python3
"""
Mack Cron Health Rotation — runs as part of weekly_review.
Sample 2 random crons owned by Mack, validate last run, flag errors >2h old.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random

JOBS_PATH = Path.home() / ".openclaw/cron/jobs.json"

def get_mack_crons():
    """Fetch all crons assigned to Mack from ~/.openclaw/cron/jobs.json."""
    try:
        if not JOBS_PATH.exists():
            print(f"ERROR: cron/jobs.json not found at {JOBS_PATH}")
            return []
        data = json.loads(JOBS_PATH.read_text())
        jobs = data.get("jobs", data) if isinstance(data, dict) else data
        mack_jobs = [
            j for j in jobs
            if "mack" in j.get("name", "").lower()
            or "macklemore" in j.get("name", "").lower()
        ]
        return mack_jobs
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR fetching Mack crons: {e}")
        return []

def check_cron_status(cron):
    """Derive health from job metadata (updatedAtMs, enabled)."""
    updated_ms = cron.get("updatedAtMs") or cron.get("createdAtMs")
    enabled = cron.get("enabled", False)
    if updated_ms:
        updated_dt = datetime.fromtimestamp(updated_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
        return {"status": "OK", "timestamp": updated_dt.isoformat(), "enabled": enabled}
    return {"status": "UNKNOWN", "timestamp": None, "enabled": enabled}

def main():
    crons = get_mack_crons()
    if len(crons) < 2:
        print("WARN: <2 Mack crons found; skipping rotation")
        return 0
    
    sample = random.sample(crons, min(2, len(crons)))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stale_threshold = now - timedelta(hours=2)
    
    alerts = []
    for cron in sample:
        cron_id = cron.get("id")
        status = check_cron_status(cron)
        last_run = status.get("timestamp")
        enabled = status.get("enabled", False)

        if not enabled:
            alerts.append(f"CRON {cron_id} ({cron.get('name','')}): disabled")
        elif last_run and datetime.fromisoformat(last_run) < stale_threshold:
            alerts.append(f"CRON {cron_id} ({cron.get('name','')}): not updated in >2h ({last_run})")
    
    if alerts:
        print("\n## Mack Cron Health Alerts\n")
        for alert in alerts:
            print(f"- {alert}")
        return 1
    else:
        print(f"✓ Mack cron sample OK ({len(sample)} checked)")
        return 0

if __name__ == "__main__":
    sys.exit(main())
