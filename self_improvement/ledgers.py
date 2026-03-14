#!/usr/bin/env python3
"""
ledgers.py — Task Ledger + Progress Ledger for self-improvement orchestration.

Based on Magentic-One dual-loop architecture:
- Task Ledger: facts, guesses, current plan (outer loop)
- Progress Ledger: per-agent task tracking with assignments (inner loop)

Stored as JSON files, updated each cycle, queryable by all agents.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

SI_DIR = Path(__file__).parent
TASK_LEDGER = SI_DIR / "task_ledger.json"
PROGRESS_LEDGER = SI_DIR / "progress_ledger.json"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save(path, data):
    path.write_text(json.dumps(data, indent=2))


# ── Task Ledger (outer loop) ──

def get_task_ledger():
    """Load current task ledger."""
    ledger = _load(TASK_LEDGER)
    if not ledger:
        ledger = {
            "version": 1,
            "last_updated": _now(),
            "facts": [],
            "guesses": [],
            "plan": [],
            "blockers": [],
        }
        _save(TASK_LEDGER, ledger)
    return ledger


def add_fact(fact: str, source: str = "system"):
    """Add a verified fact to the task ledger."""
    ledger = get_task_ledger()
    entry = {"fact": fact, "source": source, "ts": _now(), "verified": True}
    # Dedup by content
    if not any(f["fact"] == fact for f in ledger["facts"]):
        ledger["facts"].append(entry)
        # Keep last 50 facts
        ledger["facts"] = ledger["facts"][-50:]
        ledger["last_updated"] = _now()
        _save(TASK_LEDGER, ledger)
    return entry


def add_guess(guess: str, confidence: float = 0.5, source: str = "system"):
    """Add an unverified guess/hypothesis."""
    ledger = get_task_ledger()
    entry = {"guess": guess, "confidence": confidence, "source": source, "ts": _now()}
    ledger["guesses"].append(entry)
    ledger["guesses"] = ledger["guesses"][-20:]
    ledger["last_updated"] = _now()
    _save(TASK_LEDGER, ledger)
    return entry


def update_plan(plan_items: list):
    """Replace the current plan with new items."""
    ledger = get_task_ledger()
    ledger["plan"] = [{"item": p, "ts": _now()} for p in plan_items]
    ledger["last_updated"] = _now()
    _save(TASK_LEDGER, ledger)


def add_blocker(blocker: str, owner: str = "unassigned"):
    """Add a blocker."""
    ledger = get_task_ledger()
    entry = {"blocker": blocker, "owner": owner, "ts": _now(), "resolved": False}
    ledger["blockers"].append(entry)
    ledger["last_updated"] = _now()
    _save(TASK_LEDGER, ledger)


def resolve_blocker(blocker_text: str):
    """Mark a blocker as resolved."""
    ledger = get_task_ledger()
    for b in ledger["blockers"]:
        if b["blocker"] == blocker_text and not b["resolved"]:
            b["resolved"] = True
            b["resolved_ts"] = _now()
    ledger["last_updated"] = _now()
    _save(TASK_LEDGER, ledger)


# ── Progress Ledger (inner loop) ──

def get_progress_ledger():
    """Load current progress ledger."""
    ledger = _load(PROGRESS_LEDGER)
    if not ledger:
        ledger = {
            "version": 1,
            "last_updated": _now(),
            "assignments": {},  # agent -> [task items]
            "completed": [],
            "in_progress": [],
        }
        _save(PROGRESS_LEDGER, ledger)
    return ledger


def assign_task(agent: str, task_id: str, description: str):
    """Assign a task to an agent."""
    ledger = get_progress_ledger()
    if agent not in ledger["assignments"]:
        ledger["assignments"][agent] = []
    entry = {"task_id": task_id, "description": description, "assigned_ts": _now(), "status": "assigned"}
    # Don't duplicate
    if not any(t["task_id"] == task_id for t in ledger["assignments"][agent]):
        ledger["assignments"][agent].append(entry)
        ledger["in_progress"].append({"task_id": task_id, "agent": agent, "ts": _now()})
    ledger["last_updated"] = _now()
    _save(PROGRESS_LEDGER, ledger)
    return entry


def complete_task(agent: str, task_id: str, outcome: str = "done"):
    """Mark a task as complete."""
    ledger = get_progress_ledger()
    if agent in ledger["assignments"]:
        for t in ledger["assignments"][agent]:
            if t["task_id"] == task_id:
                t["status"] = "complete"
                t["completed_ts"] = _now()
                t["outcome"] = outcome
    ledger["completed"].append({"task_id": task_id, "agent": agent, "outcome": outcome, "ts": _now()})
    ledger["in_progress"] = [t for t in ledger["in_progress"] if t["task_id"] != task_id]
    ledger["last_updated"] = _now()
    _save(PROGRESS_LEDGER, ledger)


def get_agent_status(agent: str) -> dict:
    """Get current status for an agent."""
    ledger = get_progress_ledger()
    tasks = ledger["assignments"].get(agent, [])
    active = [t for t in tasks if t["status"] != "complete"]
    completed = [t for t in tasks if t["status"] == "complete"]
    return {"agent": agent, "active": active, "completed_count": len(completed)}


# ── CLI ──

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: ledgers.py <status|add-fact|assign|complete> [args]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        tl = get_task_ledger()
        pl = get_progress_ledger()
        print(f"Task Ledger: {len(tl['facts'])} facts, {len(tl['guesses'])} guesses, {len(tl['plan'])} plan items, {len([b for b in tl['blockers'] if not b['resolved']])} active blockers")
        print(f"Progress: {len(pl['in_progress'])} in progress, {len(pl['completed'])} completed")
        for agent, tasks in pl["assignments"].items():
            active = [t for t in tasks if t["status"] != "complete"]
            if active:
                print(f"  {agent}: {len(active)} active tasks")
    elif cmd == "add-fact" and len(sys.argv) >= 3:
        f = add_fact(" ".join(sys.argv[2:]), "cli")
        print(f"Added fact: {f['fact']}")
    elif cmd == "assign" and len(sys.argv) >= 5:
        t = assign_task(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
        print(f"Assigned {t['task_id']} to {sys.argv[2]}")
    elif cmd == "complete" and len(sys.argv) >= 4:
        complete_task(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]) if len(sys.argv) > 4 else "done")
        print(f"Completed {sys.argv[3]} for {sys.argv[2]}")
    else:
        print(f"Unknown command: {cmd}")
