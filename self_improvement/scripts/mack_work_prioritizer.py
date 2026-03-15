#!/usr/bin/env python3
import json, os, re
from datetime import datetime
from pathlib import Path

# Resolve paths relative to this script's location
SCRIPT_DIR = Path(__file__).parent
SI_DIR = SCRIPT_DIR.parent  # self_improvement/

# Scans TODO.md, logs, and infra health; scores work by (impact*urgency)/effort
# Output: ranked_work.json with [{'task': str, 'score': float, 'category': str, 'effort_hours': float}]

def score_work():
    work = []
    # Parse TODO.md for blockers (impact=10, urgency=10)
    todo_path = SI_DIR / 'TODO.md'
    if todo_path.exists():
        with open(todo_path) as f:
            for line in f:
                if 'BLOCKER' in line or 'CRITICAL' in line:
                    work.append({'task': line.strip(), 'impact': 10, 'urgency': 10, 'effort': 2, 'category': 'blocker'})
    # Check for broken crons (impact=8, urgency=9)
    cron_log = SI_DIR / 'logs' / 'cron_health.log'
    if cron_log.exists():
        with open(cron_log) as f:
            if 'FAILED' in f.read():
                work.append({'task': 'Repair failed cron jobs', 'impact': 8, 'urgency': 9, 'effort': 1.5, 'category': 'infra'})
    # Score: (impact * urgency) / effort
    for item in work:
        item['score'] = (item['impact'] * item['urgency']) / item['effort']
    work.sort(key=lambda x: x['score'], reverse=True)
    out_path = SI_DIR / 'ranked_work.json'
    with open(out_path, 'w') as f:
        json.dump(work, f, indent=2)
    return work

if __name__ == '__main__':
    result = score_work()
    print(json.dumps({'status': 'ok', 'top_work': result[:3] if result else []}))
