#!/usr/bin/env python3
"""
event_logger.py — Structured JSONL event logging for the self-improvement system.

Usage:
    from event_logger import log_event
    log_event("CYCLE_START", "rosie", {"cycle": 65, "sonar_enabled": True})

Events are written to:
    self_improvement/logs/events-YYYY-MM-DD.jsonl   (daily rotation)
    self_improvement/logs/all.jsonl                  (append-only master)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"

EVENT_TYPES = [
    "CYCLE_START", "CYCLE_COMPLETE", "CYCLE_FAILED",
    "IMPROVEMENT_APPLIED", "IMPROVEMENT_FAILED",
    "HEALTH_CHECK", "SELF_HEAL",
    "SONAR_RESEARCH", "MEMU_WRITE", "MEMU_SEARCH",
    "NATS_PUBLISH", "MLE_POST",
    "PROMPT_EVOLVED", "ERROR", "WARNING",
    "PLAN_UPDATE", "FEEDBACK_RECEIVED",
]


def log_event(event_type: str, agent_id: str, payload: dict = None,
              level: str = "info", tags: list = None):
    """Log a structured event to JSONL files."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    event = {
        "event_id": str(uuid.uuid4())[:8],
        "event_type": event_type,
        "agent_id": agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "payload": payload or {},
        "tags": tags or [agent_id],
    }

    line = json.dumps(event, separators=(",", ":")) + "\n"

    # Daily file
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_file = LOGS_DIR / f"events-{today}.jsonl"
    with open(daily_file, "a") as f:
        f.write(line)

    # Master file
    master_file = LOGS_DIR / "all.jsonl"
    with open(master_file, "a") as f:
        f.write(line)

    return event["event_id"]


def query_events(event_type: str = None, agent_id: str = None,
                 level: str = None, since: str = None, limit: int = 50) -> list:
    """Query events from the master log. Returns most recent first."""
    master = LOGS_DIR / "all.jsonl"
    if not master.exists():
        return []

    results = []
    for line in reversed(master.read_text().strip().splitlines()):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event_type and ev.get("event_type") != event_type:
            continue
        if agent_id and ev.get("agent_id") != agent_id:
            continue
        if level and ev.get("level") != level:
            continue
        if since and ev.get("timestamp", "") < since:
            break
        results.append(ev)
        if len(results) >= limit:
            break
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        etype = sys.argv[1]
        agent = sys.argv[2]
        payload = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        eid = log_event(etype, agent, payload)
        print(f"Logged: {eid} {etype} {agent}")
    else:
        # Query mode
        events = query_events(limit=10)
        for ev in events:
            print(f"{ev['timestamp']} [{ev['event_type']}] {ev['agent_id']}: {json.dumps(ev['payload'])[:100]}")
