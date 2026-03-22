#!/usr/bin/env python3
"""
agent_nats.py — NATS JetStream client for OpenClaw agents.

Provides publish/subscribe/request patterns for agent coordination:
- Task assignment and pickup
- Broadcast events across all agents
- Shared memory/knowledge distribution
- Heartbeat and health monitoring

Usage:
    from agent_nats import AgentNATS
    
    async with AgentNATS("rosie") as nats:
        # Publish a task for mack
        await nats.assign_task("mack", {"action": "fix_cron", "target": "..."})
        
        # Broadcast to all agents
        await nats.broadcast("model_rotation_updated", {"models": [...]})
        
        # Share knowledge
        await nats.share_memory("lesson", {"content": "...", "tags": [...]})
        
        # Subscribe to your tasks
        async for msg in nats.listen_tasks():
            await handle_task(msg)
"""

import asyncio
import json
import os
import datetime
from datetime import timezone
from typing import AsyncIterator, Any

# Try nats.py (pip install nats-py), fall back to sync subprocess
try:
    import nats as nats_lib
    from nats.js.api import StreamConfig, ConsumerConfig
    HAS_NATS_PY = True
except ImportError:
    HAS_NATS_PY = False

import subprocess

NATS_LOCAL_URL = os.environ.get("NATS_LOCAL_URL", "nats://localhost:4222")
NATS_RAILWAY_URL = os.environ.get("NATS_RAILWAY_URL", "nats://maglev.proxy.rlwy.net:55041")
NATS_URL = os.environ.get("NATS_URL", NATS_RAILWAY_URL)
NATS_USER = os.environ.get("NATS_USER", "system")
NATS_PASS = os.environ.get("NATS_PASS", "openclaw-system-2026")
NATS_URLS = [NATS_RAILWAY_URL, f"nats://{NATS_USER}:{NATS_PASS}@localhost:4222", NATS_LOCAL_URL]


class AgentNATS:
    """NATS JetStream client for agent communication."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._nc = None
        self._js = None
    
    async def __aenter__(self):
        if HAS_NATS_PY:
            urls = [NATS_URL] + [u for u in NATS_URLS if u != NATS_URL]
            for url in urls:
                try:
                    self._nc = await nats_lib.connect(
                        url,
                        user=self.agent_id,
                        password="openclaw-agent-2026",
                        name=f"openclaw-{self.agent_id}",
                    )
                    self._js = self._nc.jetstream()
                    break
                except Exception:
                    continue
        return self
    
    async def __aexit__(self, *args):
        if self._nc:
            await self._nc.close()
    
    def _ts(self) -> str:
        return datetime.datetime.now(timezone.utc).isoformat()
    
    # ── Publishing ──────────────────────────────────────────────
    
    async def assign_task(self, target_agent: str, task: dict) -> None:
        """Assign a task to a specific agent."""
        msg = {
            "from": self.agent_id,
            "to": target_agent,
            "type": "task",
            "ts": self._ts(),
            **task,
        }
        await self._publish(f"tasks.{target_agent}.from_{self.agent_id}", msg)
    
    async def broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast an event to all agents."""
        msg = {
            "from": self.agent_id,
            "type": event_type,
            "ts": self._ts(),
            **data,
        }
        await self._publish(f"events.broadcast.{event_type}", msg)
    
    async def share_memory(self, key: str, data: dict) -> None:
        """Share knowledge/memory across agents."""
        msg = {
            "from": self.agent_id,
            "key": key,
            "ts": self._ts(),
            **data,
        }
        await self._publish(f"memory.shared.{self.agent_id}.{key}", msg)
    
    async def heartbeat(self, status: str = "active", details: dict = None) -> None:
        """Send agent heartbeat."""
        msg = {
            "from": self.agent_id,
            "status": status,
            "ts": self._ts(),
            **(details or {}),
        }
        await self._publish(f"events.heartbeat.{self.agent_id}", msg)
    
    async def report(self, report_type: str, content: str) -> None:
        """Report status/completion to the system."""
        msg = {
            "from": self.agent_id,
            "type": report_type,
            "content": content,
            "ts": self._ts(),
        }
        await self._publish(f"events.report.{self.agent_id}.{report_type}", msg)
    
    # ── Subscribing ─────────────────────────────────────────────
    
    async def listen_tasks(self, timeout: float = 5.0) -> AsyncIterator[dict]:
        """Listen for tasks assigned to this agent."""
        if HAS_NATS_PY and self._js:
            sub = await self._js.pull_subscribe(
                f"tasks.{self.agent_id}.>",
                durable=f"{self.agent_id}-worker",
                stream="AGENT_TASKS",
            )
            while True:
                try:
                    msgs = await sub.fetch(1, timeout=timeout)
                    for msg in msgs:
                        data = json.loads(msg.data.decode())
                        yield data
                        await msg.ack()
                except Exception:
                    break
    
    async def listen_broadcasts(self, timeout: float = 5.0) -> AsyncIterator[dict]:
        """Listen for broadcast events."""
        if HAS_NATS_PY and self._js:
            sub = await self._js.subscribe(
                "events.broadcast.>",
                stream="AGENT_EVENTS",
            )
            async for msg in sub.messages:
                data = json.loads(msg.data.decode())
                yield data
    
    # ── Internal ────────────────────────────────────────────────
    
    async def _publish(self, subject: str, msg: dict) -> None:
        """Publish a message to NATS JetStream."""
        payload = json.dumps(msg).encode()
        
        if HAS_NATS_PY and self._js:
            await self._js.publish(subject, payload)
        else:
            # Fallback: use nats CLI
            self._publish_cli(subject, json.dumps(msg))
    
    def _publish_cli(self, subject: str, data: str) -> None:
        """Fallback: publish via nats CLI (Railway primary, local fallback)."""
        for url in NATS_URLS:
            env = os.environ.copy()
            env["NATS_URL"] = url
            try:
                r = subprocess.run(
                    ["nats", "pub", subject, data],
                    env=env,
                    capture_output=True,
                    timeout=5,
                )
                if r.returncode == 0:
                    return
            except Exception:
                continue


# ── Synchronous helpers (for use in non-async scripts) ──────────

def publish_sync(subject: str, data: dict, agent_id: str = "system") -> bool:
    """Synchronous publish via CLI. Railway primary, local fallback."""
    msg = {"from": agent_id, "ts": datetime.datetime.now(timezone.utc).isoformat(), **data}
    for url in NATS_URLS:
        env = os.environ.copy()
        env["NATS_URL"] = url
        try:
            r = subprocess.run(
                ["nats", "pub", subject, json.dumps(msg)],
                env=env, capture_output=True, timeout=5, text=True,
            )
            if r.returncode == 0:
                return True
        except Exception:
            continue
    return False


def assign_task_sync(target: str, task: dict, from_agent: str = "system") -> bool:
    """Assign a task synchronously."""
    return publish_sync(f"tasks.{target}.from_{from_agent}", {"type": "task", **task}, from_agent)


def broadcast_sync(event_type: str, data: dict, from_agent: str = "system") -> bool:
    """Broadcast an event synchronously."""
    return publish_sync(f"events.broadcast.{event_type}", {"type": event_type, **data}, from_agent)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python agent_nats.py <publish|broadcast|test> [subject|event] [data_json]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "test":
        ok = broadcast_sync("test", {"message": "NATS agent messaging test"})
        print(f"Test broadcast: {'OK' if ok else 'FAILED'}")
    elif cmd == "publish":
        data = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {"message": "test"}
        ok = publish_sync(sys.argv[2], data)
        print(f"Published: {'OK' if ok else 'FAILED'}")
    elif cmd == "broadcast":
        data = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {"message": sys.argv[2]}
        ok = broadcast_sync(sys.argv[2], data)
        print(f"Broadcast: {'OK' if ok else 'FAILED'}")
