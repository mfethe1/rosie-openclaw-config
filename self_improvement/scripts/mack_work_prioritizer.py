#!/usr/bin/env python3
import json, os, re
from datetime import datetime

# Scans TODO.md, logs, and infra health; scores work by (impact*urgency)/effort
# Output: ranked_work.json with [{'task': str, 'score': float, 'category': str, 'effort_hours': float}]

def score_work():
    work = []
    # Parse TODO.md for blockers (impact=10, urgency=10)
    if os.path.exists('TODO.md'):
        with open('TODO.md') as f:
            for line in f:
                if 'BLOCKER' in line or 'CRITICAL' in line:
                    work.append({'task': line.strip(), 'impact': 10, 'urgency': 10, 'effort': 2, 'category': 'blocker'})
    # Check for broken crons (impact=8, urgency=9)
    if os.path.exists('logs/cron_health.log'):
        with open('logs/cron_health.log') as f:
            if 'FAILED' in f.read():
                work.append({'task': 'Repair failed cron jobs', 'impact': 8, 'urgency': 9, 'effort': 1.5, 'category': 'infra'})
    # Score: (impact * urgency) / effort
    for item in work:
        item['score'] = (item['impact'] * item['urgency']) / item['effort']
    work.sort(key=lambda x: x['score'], reverse=True)
    with open('self_improvement/ranked_work.json', 'w') as f:
        json.dump(work, f, indent=2)
    return work

if __name__ == '__main__':
    result = score_work()
    print(json.dumps({'status': 'ok', 'top_work': result[:3] if result else []}))
