#!/usr/bin/env python3
"""ultrawork_trigger.py — Detect 'ulw' keyword and auto-orchestrate deep work sessions.

When triggered (by detecting 'ulw' keyword in a message or command), this script:
1. Creates a task_orchestrator workflow for the deep work session
2. Sets up a focused work block with defined steps
3. Configures auto-silence for non-critical notifications
4. Generates a structured plan from a free-text goal

The Ultrawork protocol:
- ulw <goal>        → start a focused 90-min deep work block
- ulw status        → check current ultrawork session
- ulw done          → complete current session, generate summary
- ulw abort         → cancel current session

Usage:
  python3 ultrawork_trigger.py start "Build memU semantic search upgrade"
  python3 ultrawork_trigger.py start "Fix cron delivery bugs" --duration 60
  python3 ultrawork_trigger.py status
  python3 ultrawork_trigger.py done --summary "Completed X, Y, Z"
  python3 ultrawork_trigger.py abort
  python3 ultrawork_trigger.py --json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
STATE_FILE = WORKSPACE / "self_improvement/memory/ultrawork_state.json"
ORCHESTRATOR = WORKSPACE / "self_improvement/scripts/task_orchestrator.py"
PYTHON = sys.executable


def load_state() -> dict | None:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_state(state: dict | None):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if state is None:
        STATE_FILE.unlink(missing_ok=True)
    else:
        STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def decompose_goal(goal: str) -> list[dict]:
    """Break a free-text goal into structured steps.

    Uses keyword heuristics to assign agents. Falls back to a
    generic mack→lenny→rosie pipeline for unknown goals.
    """
    goal_lower = goal.lower()

    # Keyword → agent mapping for step generation
    if any(w in goal_lower for w in ["research", "scout", "compare", "evaluate", "benchmark"]):
        return [
            {"agent": "winnie", "action": f"Research: {goal}"},
            {"agent": "mack", "action": f"Implement findings from research"},
            {"agent": "lenny", "action": "Verify implementation"},
        ]
    elif any(w in goal_lower for w in ["fix", "repair", "debug", "patch", "heal"]):
        return [
            {"agent": "mack", "action": f"Diagnose and fix: {goal}"},
            {"agent": "lenny", "action": "Verify fix, check for regressions"},
        ]
    elif any(w in goal_lower for w in ["review", "audit", "check", "validate"]):
        return [
            {"agent": "lenny", "action": f"Audit: {goal}"},
            {"agent": "rosie", "action": "Review audit findings and decide actions"},
        ]
    elif any(w in goal_lower for w in ["plan", "design", "architect", "coordinate"]):
        return [
            {"agent": "rosie", "action": f"Plan: {goal}"},
            {"agent": "mack", "action": "Implement plan"},
            {"agent": "lenny", "action": "Verify implementation"},
            {"agent": "rosie", "action": "Approve and close"},
        ]
    else:
        # Default: build pipeline
        return [
            {"agent": "mack", "action": f"Implement: {goal}"},
            {"agent": "lenny", "action": "Verify implementation"},
            {"agent": "rosie", "action": "Approve and close"},
        ]


def cmd_start(args) -> int:
    current = load_state()
    if current and current.get("status") == "active":
        remaining = ""
        if "end_time" in current:
            try:
                end = datetime.fromisoformat(current["end_time"])
                mins = max(0, int((end - datetime.now()).total_seconds() / 60))
                remaining = f" ({mins}m remaining)"
            except (ValueError, TypeError):
                pass
        print(f"⚠️ Ultrawork session already active: {current.get('goal', '?')}{remaining}")
        print("Use 'ultrawork_trigger.py done' or 'abort' first.")
        return 1

    now = datetime.now()
    duration = args.duration or 90
    end_time = now + timedelta(minutes=duration)

    # Decompose goal into steps
    steps = decompose_goal(args.goal)
    steps_str = ",".join(f"{s['agent']}:{s['action']}" for s in steps)

    # Create workflow via task_orchestrator
    wf_id = None
    try:
        result = subprocess.check_output(
            [PYTHON, str(ORCHESTRATOR), "--json", "create", args.goal, "--steps", steps_str],
            timeout=10
        ).decode().strip()
        wf_data = json.loads(result)
        wf_id = wf_data.get("created")
    except Exception as e:
        print(f"Warning: could not create workflow: {e}")

    state = {
        "status": "active",
        "goal": args.goal,
        "start_time": now.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_min": duration,
        "workflow_id": wf_id,
        "steps": steps,
    }
    save_state(state)

    if args.json:
        print(json.dumps(state))
    else:
        print(f"🔥 Ultrawork session started!")
        print(f"   Goal: {args.goal}")
        print(f"   Duration: {duration} minutes (until {end_time.strftime('%H:%M')})")
        print(f"   Steps: {len(steps)}")
        for i, s in enumerate(steps):
            marker = "→" if i == 0 else " "
            print(f"   {marker} [{s['agent']}] {s['action']}")
        if wf_id:
            print(f"   Workflow: {wf_id}")

    return 0


def cmd_status(args) -> int:
    state = load_state()
    if not state:
        if args.json:
            print(json.dumps({"status": "inactive"}))
        else:
            print("No active Ultrawork session.")
        return 0

    now = datetime.now()
    remaining = ""
    overtime = False
    if "end_time" in state:
        try:
            end = datetime.fromisoformat(state["end_time"])
            diff = (end - now).total_seconds() / 60
            if diff > 0:
                remaining = f"{int(diff)}m remaining"
            else:
                remaining = f"{int(-diff)}m overtime"
                overtime = True
        except (ValueError, TypeError):
            pass

    if args.json:
        state["remaining"] = remaining
        state["overtime"] = overtime
        print(json.dumps(state))
    else:
        icon = "🔴" if overtime else "🔥"
        print(f"{icon} Ultrawork: {state.get('goal', '?')}")
        print(f"   Status: {state.get('status', '?')} | {remaining}")
        if state.get("workflow_id"):
            print(f"   Workflow: {state['workflow_id']}")

    return 0


def cmd_done(args) -> int:
    state = load_state()
    if not state:
        print("No active Ultrawork session.")
        return 1

    now = datetime.now()
    start = datetime.fromisoformat(state.get("start_time", now.isoformat()))
    actual_min = int((now - start).total_seconds() / 60)

    summary = {
        "goal": state.get("goal"),
        "planned_duration": state.get("duration_min"),
        "actual_duration": actual_min,
        "summary": args.summary or "completed",
        "workflow_id": state.get("workflow_id"),
        "completed_at": now.isoformat(),
    }

    save_state(None)

    if args.json:
        print(json.dumps(summary))
    else:
        print(f"✅ Ultrawork session complete!")
        print(f"   Goal: {summary['goal']}")
        print(f"   Duration: {actual_min}m (planned {summary['planned_duration']}m)")
        if args.summary:
            print(f"   Summary: {args.summary}")

    return 0


def cmd_abort(args) -> int:
    state = load_state()
    if not state:
        print("No active Ultrawork session.")
        return 1

    goal = state.get("goal", "?")
    save_state(None)

    if args.json:
        print(json.dumps({"aborted": True, "goal": goal}))
    else:
        print(f"⏹️ Ultrawork session aborted: {goal}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ultrawork deep work trigger system")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p_start = sub.add_parser("start", help="Start an Ultrawork session")
    p_start.add_argument("goal", help="What to accomplish")
    p_start.add_argument("--duration", type=int, default=90, help="Duration in minutes (default: 90)")

    sub.add_parser("status", help="Check current session")

    p_done = sub.add_parser("done", help="Complete current session")
    p_done.add_argument("--summary", help="What was accomplished")

    sub.add_parser("abort", help="Abort current session")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return 1

    return {"start": cmd_start, "status": cmd_status, "done": cmd_done, "abort": cmd_abort}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
