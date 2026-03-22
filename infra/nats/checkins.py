#!/usr/bin/env python3
import json
import sys
import os
import subprocess
from datetime import datetime, timezone

NATS_LOCAL = os.environ.get("NATS_LOCAL_URL", "nats://system:openclaw-system-2026@127.0.0.1:4222")
NATS_RAILWAY = os.environ.get("NATS_RAILWAY_URL", "nats://system:openclaw-system-2026@maglev.proxy.rlwy.net:55041")
NATS_SERVERS = [NATS_RAILWAY, NATS_LOCAL]

def _connected_server() -> str:
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

def publish(agent_id, task, blockers, next_step):
    server = _connected_server()
    if not server:
        print("Could not connect to NATS.")
        sys.exit(1)
        
    subject = f"events.report.{agent_id}.checkin"
    data = {
        "from": agent_id,
        "type": "checkin",
        "task": task,
        "blockers": blockers,
        "next_step": next_step,
        "ts": datetime.now(timezone.utc).isoformat()
    }
    
    env = os.environ.copy()
    env["NATS_URL"] = server
    r = subprocess.run(["nats", "pub", subject, json.dumps(data)], env=env, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"Check-in published to NATS for {agent_id}")
    else:
        print(f"Failed to publish: {r.stderr}")

def list_checkins():
    server = _connected_server()
    if not server:
        print("Could not connect to NATS.")
        sys.exit(1)
        
    env = os.environ.copy()
    env["NATS_URL"] = server
    
    print("--- Recent Agent Check-ins ---")
    agents = ["rosie", "mack", "winnie", "lenny", "system", "sweep"]
    found = False
    
    for a in agents:
        subject = f"events.report.{a}.checkin"
        r = subprocess.run(
            ["nats", "stream", "get", "AGENT_EVENTS", "--last-for", subject, "-j"],
            env=env, capture_output=True, text=True
        )
        if r.returncode == 0 and r.stdout.strip():
            try:
                # The CLI outputs JSON. We need the "data" field which is base64 encoded or raw string depending on version.
                # Actually, NATS CLI -j outputs {"message": {"data": "base64..."}} or similar. 
                # Wait, if --translate is not used, it might be raw JSON in stdout if we just use --translate?
                # Actually it's easier to just parse it.
                parsed = json.loads(r.stdout)
                if "message" in parsed and "data" in parsed["message"]:
                    import base64
                    try:
                        msg_data = base64.b64decode(parsed["message"]["data"]).decode()
                    except:
                        msg_data = parsed["message"]["data"]
                    data = json.loads(msg_data)
                    print(f"\n[{a.upper()}]")
                    print(f"  Task:      {data.get('task')}")
                    print(f"  Blockers:  {data.get('blockers')}")
                    print(f"  Next Step: {data.get('next_step')}")
                    found = True
            except Exception as e:
                pass
    
    if not found:
        print("No recent check-ins found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 checkins.py publish <agent_id> \"<task>\" \"<blockers>\" \"<next_step>\"")
        print("       python3 checkins.py list")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "publish" and len(sys.argv) >= 6:
        publish(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "list":
        list_checkins()
    else:
        print("Invalid command or missing arguments.")
