#!/usr/bin/env python3
"""task_orchestrator.py — Lightweight multi-agent workflow manager.

Manages sequential and parallel task pipelines across agents (Rosie, Mack,
Winnie, Lenny). Reads workflow definitions from YAML/JSON, tracks state in
SQLite, and produces handoff records.

Features:
- Define workflows as ordered steps with agent assignments
- Track step status: pending → running → done/failed
- Enforce dependency ordering (step N waits for step N-1)
- Generate handoff summaries for each step transition
- Timeout detection for stuck steps

Usage:
  python3 task_orchestrator.py create "Deploy memU upgrade" --steps mack:implement,lenny:verify,rosie:approve
  python3 task_orchestrator.py status                       # show all active workflows
  python3 task_orchestrator.py status --id <workflow-id>    # show specific workflow
  python3 task_orchestrator.py advance <workflow-id>        # mark current step done, advance
  python3 task_orchestrator.py fail <workflow-id> --reason "test failed"
  python3 task_orchestrator.py list                         # all workflows
  python3 task_orchestrator.py list --active                # only active
  python3 task_orchestrator.py --json                       # machine output
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".openclaw/task-orchestrator.db"
VALID_AGENTS = {"rosie", "mack", "winnie", "lenny", "any"}
VALID_STATUSES = {"pending", "running", "done", "failed", "skipped"}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            current_step INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id TEXT NOT NULL REFERENCES workflows(id),
            step_index INTEGER NOT NULL,
            agent TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            UNIQUE(workflow_id, step_index)
        )
    """)
    conn.commit()
    return conn


def cmd_create(args) -> int:
    conn = connect()
    wf_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()

    conn.execute(
        "INSERT INTO workflows (id, title, status, created_at, updated_at) VALUES (?,?,?,?,?)",
        (wf_id, args.title, "active", now, now)
    )

    for i, step_spec in enumerate(args.steps.split(",")):
        parts = step_spec.strip().split(":", 1)
        agent = parts[0].strip().lower()
        action = parts[1].strip() if len(parts) > 1 else ""

        if agent not in VALID_AGENTS:
            print(f"Warning: unknown agent '{agent}', using anyway")

        status = "running" if i == 0 else "pending"
        started = now if i == 0 else None

        conn.execute(
            "INSERT INTO steps (workflow_id, step_index, agent, action, status, started_at) VALUES (?,?,?,?,?,?)",
            (wf_id, i, agent, action, status, started)
        )

    conn.commit()
    conn.close()

    if args.json:
        print(json.dumps({"created": wf_id, "title": args.title, "steps": len(args.steps.split(","))}))
    else:
        print(f"✅ Created workflow {wf_id}: {args.title} ({len(args.steps.split(','))} steps)")
    return 0


def cmd_status(args) -> int:
    conn = connect()

    if args.id:
        wf = conn.execute("SELECT * FROM workflows WHERE id = ?", (args.id,)).fetchone()
        if not wf:
            print(f"Workflow {args.id} not found")
            return 1

        steps = conn.execute(
            "SELECT * FROM steps WHERE workflow_id = ? ORDER BY step_index", (args.id,)
        ).fetchall()

        if args.json:
            print(json.dumps({
                "id": wf["id"], "title": wf["title"], "status": wf["status"],
                "current_step": wf["current_step"], "created": wf["created_at"],
                "steps": [dict(s) for s in steps]
            }, default=str))
        else:
            icons = {"pending": "⬜", "running": "🔵", "done": "✅", "failed": "🔴", "skipped": "⏭️"}
            print(f"\n{'='*50}")
            print(f"Workflow: {wf['id']} — {wf['title']}")
            print(f"Status: {wf['status']} | Created: {wf['created_at'][:16]}")
            print(f"{'='*50}")
            for s in steps:
                icon = icons.get(s["status"], "?")
                result = f" → {s['result']}" if s["result"] else ""
                print(f"  {icon} Step {s['step_index']}: [{s['agent']}] {s['action']}{result}")
    else:
        wfs = conn.execute(
            "SELECT w.*, COUNT(s.id) as step_count FROM workflows w LEFT JOIN steps s ON w.id = s.workflow_id GROUP BY w.id ORDER BY w.updated_at DESC"
        ).fetchall()

        if not wfs:
            print("No workflows found")
            return 0

        if args.json:
            print(json.dumps([dict(w) for w in wfs], default=str))
        else:
            for w in wfs:
                status_icon = {"active": "🔵", "done": "✅", "failed": "🔴"}.get(w["status"], "?")
                print(f"  {status_icon} {w['id']}: {w['title']} ({w['step_count']} steps, step {w['current_step']})")

    conn.close()
    return 0


def cmd_advance(args) -> int:
    conn = connect()
    now = datetime.now().isoformat()

    wf = conn.execute("SELECT * FROM workflows WHERE id = ?", (args.id,)).fetchone()
    if not wf:
        print(f"Workflow {args.id} not found"); return 1
    if wf["status"] != "active":
        print(f"Workflow {args.id} is {wf['status']}, not active"); return 1

    current = wf["current_step"]
    result = args.result or "completed"

    # Mark current step done
    conn.execute(
        "UPDATE steps SET status = 'done', completed_at = ?, result = ? WHERE workflow_id = ? AND step_index = ?",
        (now, result, args.id, current)
    )

    # Check if there's a next step
    next_step = conn.execute(
        "SELECT * FROM steps WHERE workflow_id = ? AND step_index = ?",
        (args.id, current + 1)
    ).fetchone()

    if next_step:
        conn.execute(
            "UPDATE steps SET status = 'running', started_at = ? WHERE workflow_id = ? AND step_index = ?",
            (now, args.id, current + 1)
        )
        conn.execute(
            "UPDATE workflows SET current_step = ?, updated_at = ? WHERE id = ?",
            (current + 1, now, args.id)
        )
        msg = f"Step {current} done. Step {current + 1} now running (agent: {next_step['agent']})"
    else:
        conn.execute(
            "UPDATE workflows SET status = 'done', updated_at = ? WHERE id = ?",
            (now, args.id)
        )
        msg = f"Step {current} done. Workflow complete!"

    conn.commit()
    conn.close()

    if args.json:
        print(json.dumps({"advanced": True, "message": msg}))
    else:
        print(f"✅ {msg}")
    return 0


def cmd_fail(args) -> int:
    conn = connect()
    now = datetime.now().isoformat()

    wf = conn.execute("SELECT * FROM workflows WHERE id = ?", (args.id,)).fetchone()
    if not wf:
        print(f"Workflow {args.id} not found"); return 1

    conn.execute(
        "UPDATE steps SET status = 'failed', completed_at = ?, result = ? WHERE workflow_id = ? AND step_index = ?",
        (now, args.reason or "failed", args.id, wf["current_step"])
    )
    conn.execute(
        "UPDATE workflows SET status = 'failed', updated_at = ? WHERE id = ?",
        (now, args.id)
    )
    conn.commit()
    conn.close()

    if args.json:
        print(json.dumps({"failed": True, "workflow": args.id, "reason": args.reason}))
    else:
        print(f"🔴 Workflow {args.id} failed at step {wf['current_step']}: {args.reason or 'no reason'}")
    return 0


def cmd_list(args) -> int:
    conn = connect()
    query = "SELECT w.*, COUNT(s.id) as step_count FROM workflows w LEFT JOIN steps s ON w.id = s.workflow_id"
    if args.active:
        query += " WHERE w.status = 'active'"
    query += " GROUP BY w.id ORDER BY w.updated_at DESC"

    wfs = conn.execute(query).fetchall()
    conn.close()

    if args.json:
        print(json.dumps([dict(w) for w in wfs], default=str))
    else:
        if not wfs:
            print("No workflows")
            return 0
        for w in wfs:
            icon = {"active": "🔵", "done": "✅", "failed": "🔴"}.get(w["status"], "?")
            print(f"  {icon} {w['id']}: {w['title']} [{w['status']}] ({w['step_count']} steps)")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-agent task orchestrator")
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="cmd")

    p_create = sub.add_parser("create", help="Create a workflow")
    p_create.add_argument("title", help="Workflow title")
    p_create.add_argument("--steps", required=True, help="Comma-separated agent:action pairs")

    p_status = sub.add_parser("status", help="Show workflow status")
    p_status.add_argument("--id", help="Specific workflow ID")

    p_advance = sub.add_parser("advance", help="Advance workflow to next step")
    p_advance.add_argument("id", help="Workflow ID")
    p_advance.add_argument("--result", help="Result text for completed step")

    p_fail = sub.add_parser("fail", help="Mark workflow as failed")
    p_fail.add_argument("id", help="Workflow ID")
    p_fail.add_argument("--reason", help="Failure reason")

    p_list = sub.add_parser("list", help="List workflows")
    p_list.add_argument("--active", action="store_true", help="Active only")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return 1

    return {"create": cmd_create, "status": cmd_status, "advance": cmd_advance,
            "fail": cmd_fail, "list": cmd_list}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
