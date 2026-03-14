#!/usr/bin/env python3
"""
Mack Cron Health Rotation — runs as part of weekly_review.
Sample 2 random crons owned by Mack, validate last run, flag errors >2h old.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
import random

def get_mack_crons():
    """Fetch all crons assigned to Mack from openclaw.json."""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list", "--owner=Mack", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"ERROR: openclaw cron list failed: {result.stderr}")
            return []
        return json.loads(result.stdout)
    except Exception as e:
        print(f"ERROR fetching Mack crons: {e}")
        return []

def check_cron_status(cron_id):
    """Get last run status for a cron."""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "log", cron_id, "--last=1", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return {"status": "ERROR", "message": result.stderr}
        return json.loads(result.stdout)
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

def main():
    crons = get_mack_crons()
    if len(crons) < 2:
        print("WARN: <2 Mack crons found; skipping rotation")
        return 0
    
    sample = random.sample(crons, min(2, len(crons)))
    now = datetime.utcnow()
    stale_threshold = now - timedelta(hours=2)
    
    alerts = []
    for cron in sample:
        cron_id = cron.get("id")
        status = check_cron_status(cron_id)
        last_run = status.get("timestamp")
        
        if status.get("status") == "ERROR":
            alerts.append(f"CRON {cron_id}: error in last run — {status.get('message')}")
        elif last_run and datetime.fromisoformat(last_run) < stale_threshold:
            alerts.append(f"CRON {cron_id}: last run >2h old ({last_run})")
    
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
