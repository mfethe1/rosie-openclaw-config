#!/usr/bin/env python3
"""Lenny Repeat-Failure Pattern Scanner — runs each cycle.
Scans fail-reflections.jsonl for root causes with 3+ occurrences.
Escalates immediately if threshold breached.
"""
import json
import collections
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

def scan_repeat_failures(log_path: str = "memory/fail-reflections.jsonl", threshold: int = 3) -> Dict:
    """Scan fail-reflections for repeat root causes. Return escalation summary."""
    log = Path(log_path)
    if not log.exists():
        return {"status": "clean", "message": "No fail-reflections.jsonl found — clean slate."}
    
    root_causes = collections.Counter()
    failure_detail = collections.defaultdict(list)
    now = datetime.now()
    
    try:
        with open(log, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                root = entry.get('probable_cause') or entry.get('root_cause') or 'UNKNOWN'
                timestamp = entry.get('timestamp', 'N/A')
                task_id = entry.get('task') or entry.get('task_id') or entry.get('task_key', 'N/A')
                
                root_causes[root] += 1
                failure_detail[root].append({
                    'timestamp': timestamp,
                    'task_id': task_id,
                    'attempted_fix': entry.get('attempted_fix', 'none'),
                    'remaining_risk': entry.get('remaining_risk', 'not_assessed')
                })
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse fail-reflections.jsonl: {e}"}
    
    # Identify escalations
    escalations = {cause: count for cause, count in root_causes.items() if count >= threshold}
    
    result = {
        "status": "escalation_required" if escalations else "ok",
        "scan_time": now.isoformat(),
        "total_unique_root_causes": len(root_causes),
        "threshold": threshold,
        "repeat_failures_detected": escalations,
        "details": {}
    }
    
    for cause, count in escalations.items():
        result["details"][cause] = {
            "count": count,
            "incidents": failure_detail[cause]
        }
    
    return result

if __name__ == "__main__":
    result = scan_repeat_failures()
    print(json.dumps(result, indent=2))
    if result.get("status") == "escalation_required":
        print("\n🚨 ESCALATION TRIGGERED: Repeat failure pattern detected.")
        for cause, data in result.get("details", {}).items():
            print(f"  • {cause}: {data['count']} occurrences")
        exit(1)
    else:
        print("\n✓ No repeat patterns above threshold.")
        exit(0)
