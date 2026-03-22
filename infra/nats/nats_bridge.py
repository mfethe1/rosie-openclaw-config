#!/usr/bin/env python3
"""
nats_bridge.py — Bridge between OpenClaw agent crons and NATS JetStream.

Called by cron jobs to:
1. Publish heartbeats when an agent starts/finishes a cycle
2. Broadcast learnings to other agents
3. Check for pending tasks from NATS before starting work
4. Report cycle results

Usage in cron:
  python3 infra/nats/nats_bridge.py heartbeat rosie active
  python3 infra/nats/nats_bridge.py broadcast rosie "discovered new pattern: ..."
  python3 infra/nats/nats_bridge.py check-tasks rosie
  python3 infra/nats/nats_bridge.py report rosie "cycle_complete" "5 improvements applied"
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

NATS_LOCAL = os.environ.get("NATS_LOCAL_URL", "nats://system:openclaw-system-2026@127.0.0.1:4222")
NATS_RAILWAY = os.environ.get("NATS_RAILWAY_URL", "nats://maglev.proxy.rlwy.net:55041")
# Railway-first policy with explicit local fallback.
NATS_SERVERS = [NATS_RAILWAY, NATS_LOCAL]


def nats_pub(subject: str, data: dict) -> bool:
    """Publish to NATS with failover (local → Railway)."""
    for server_url in NATS_SERVERS:
        env = os.environ.copy()
        env["NATS_URL"] = server_url
        try:
            r = subprocess.run(
                ["nats", "pub", subject, json.dumps(data)],
                env=env, capture_output=True, timeout=5, text=True,
            )
            if r.returncode == 0:
                return True
        except Exception:
            continue
    return False


def _connected_server() -> str | None:
    """Return first reachable server from failover list."""
    for server_url in NATS_SERVERS:
        env = os.environ.copy()
        env["NATS_URL"] = server_url
        try:
            r = subprocess.run(
                ["nats", "server", "check", "connection"],
                env=env, capture_output=True, timeout=4, text=True,
            )
            if r.returncode == 0:
                return server_url
        except Exception:
            continue
    return None


def nats_available() -> bool:
    """Quick check if Railway/local NATS is reachable."""
    return _connected_server() is not None


def cmd_heartbeat(agent_id: str, status: str = "active", **extra):
    if not nats_available():
        return
    nats_pub(f"events.heartbeat.{agent_id}", {
        "from": agent_id,
        "status": status,
        "ts": datetime.now(timezone.utc).isoformat(),
        **extra,
    })


def cmd_broadcast(agent_id: str, message: str, event_type: str = "learning"):
    if not nats_available():
        return
    nats_pub(f"events.broadcast.{event_type}", {
        "from": agent_id,
        "type": event_type,
        "message": message,
        "ts": datetime.now(timezone.utc).isoformat(),
    })


def cmd_check_tasks(agent_id: str):
    """Check for pending tasks (pull from NATS)."""
    if not nats_available():
        print("[]")
        return
    server = _connected_server()
    if not server:
        print("[]")
        return
    env = os.environ.copy()
    env["NATS_URL"] = server
    try:
        r = subprocess.run(
            ["nats", "consumer", "next", "AGENT_TASKS", f"{agent_id}-worker",
             "--count", "5", "--no-ack"],
            env=env, capture_output=True, timeout=5, text=True,
        )
        if r.stdout:
            print(r.stdout)
        else:
            print("[]")
    except Exception:
        print("[]")


def cmd_report(agent_id: str, report_type: str, content: str):
    if not nats_available():
        return
    nats_pub(f"events.report.{agent_id}.{report_type}", {
        "from": agent_id,
        "type": report_type,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(),
    })


def cmd_assign(from_agent: str, to_agent: str, task_json: str):
    """Assign a task to another agent via NATS."""
    if not nats_available():
        print("NATS unavailable")
        return
    task = json.loads(task_json) if task_json.startswith("{") else {"description": task_json}
    nats_pub(f"tasks.{to_agent}.from_{from_agent}", {
        "from": from_agent,
        "to": to_agent,
        "type": "task",
        "ts": datetime.now(timezone.utc).isoformat(),
        **task,
    })
    print(f"Task assigned to {to_agent}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: nats_bridge.py <command> <agent_id> [args...]")
        print("Commands: heartbeat, broadcast, check-tasks, report, assign")
        sys.exit(1)
    
    cmd = sys.argv[1]
    agent = sys.argv[2]
    
    if cmd == "heartbeat":
        status = sys.argv[3] if len(sys.argv) > 3 else "active"
        cmd_heartbeat(agent, status)
    elif cmd == "broadcast":
        message = sys.argv[3] if len(sys.argv) > 3 else ""
        cmd_broadcast(agent, message)
    elif cmd == "check-tasks":
        cmd_check_tasks(agent)
    elif cmd == "report":
        report_type = sys.argv[3] if len(sys.argv) > 3 else "status"
        content = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_report(agent, report_type, content)
    elif cmd == "assign":
        to_agent = sys.argv[3]
        task = sys.argv[4] if len(sys.argv) > 4 else "{}"
        cmd_assign(agent, to_agent, task)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
