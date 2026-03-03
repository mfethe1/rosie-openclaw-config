#!/usr/bin/env python3
"""Escalate stale critical blockers to chat.

Scans self_improvement/shared-state.json active_blockers and sends a compact alert
when HIGH/CRITICAL blockers remain unresolved for >24h.

Designed for cron use (idempotent with alert cooldown state).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE = Path(__file__).resolve().parents[2]
SHARED_STATE_PATH = WORKSPACE / "self_improvement" / "shared-state.json"
STATE_DIR = WORKSPACE / "self_improvement" / "state"
ALERT_STATE_PATH = STATE_DIR / "alert_escalation_state.json"


@dataclass
class Blocker:
    blocker_id: str
    priority: str
    owner: str
    description: str
    age_hours: float
    raised_at: Optional[str]
    updated_at: Optional[str]


def _parse_dt(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open() as f:
            return json.load(f)
    except Exception:
        return default


def _is_unresolved(raw: Dict[str, Any]) -> bool:
    priority = str(raw.get("priority", "")).upper()
    if priority == "RESOLVED":
        return False
    if raw.get("resolved_at"):
        return False
    return True


def find_stale_critical_blockers(shared_state: Path, min_age_hours: int) -> List[Blocker]:
    payload = _load_json(shared_state, {})
    active = payload.get("active_blockers", []) if isinstance(payload, dict) else []
    now = datetime.now(timezone.utc)
    out: List[Blocker] = []

    for item in active:
        if not isinstance(item, dict):
            continue
        if not _is_unresolved(item):
            continue

        priority = str(item.get("priority", "")).upper()
        if priority not in {"CRITICAL", "HIGH"}:
            continue

        anchor = _parse_dt(item.get("updated_at")) or _parse_dt(item.get("raised_at"))
        if not anchor:
            continue

        age_hours = (now - anchor).total_seconds() / 3600.0
        if age_hours < min_age_hours:
            continue

        out.append(
            Blocker(
                blocker_id=str(item.get("id", "UNKNOWN")),
                priority=priority,
                owner=str(item.get("owner", "unassigned")),
                description=str(item.get("description", "")),
                age_hours=age_hours,
                raised_at=item.get("raised_at"),
                updated_at=item.get("updated_at"),
            )
        )

    # deterministic order: priority then age desc then id
    out.sort(key=lambda b: (0 if b.priority == "CRITICAL" else 1, -b.age_hours, b.blocker_id))
    return out


def filter_by_cooldown(blockers: List[Blocker], state_path: Path, cooldown_hours: int) -> List[Blocker]:
    state = _load_json(state_path, {"last_alerted": {}})
    last_alerted: Dict[str, str] = state.get("last_alerted", {}) if isinstance(state, dict) else {}
    now = datetime.now(timezone.utc)
    cooldown = timedelta(hours=cooldown_hours)

    send: List[Blocker] = []
    for b in blockers:
        ts = _parse_dt(last_alerted.get(b.blocker_id))
        if ts is None or (now - ts) >= cooldown:
            send.append(b)
    return send


def build_message(blockers: List[Blocker], min_age_hours: int) -> str:
    lines = [
        f"🚨 Blocker escalation: {len(blockers)} HIGH/CRITICAL blockers unresolved >{min_age_hours}h",
    ]
    for b in blockers[:8]:
        lines.append(
            f"- {b.blocker_id} [{b.priority}] owner={b.owner} age={int(b.age_hours)}h — {b.description[:110]}"
        )
    if len(blockers) > 8:
        lines.append(f"- ...and {len(blockers) - 8} more")
    lines.append("Action: acknowledge owner + ETA, or mark resolved in shared-state/TODO.")
    return "\n".join(lines)


def send_alert(channel: str, target: str, message: str, dry_run: bool) -> Dict[str, Any]:
    cmd = [
        "openclaw",
        "message",
        "send",
        "--channel",
        channel,
        "--target",
        target,
        "--message",
        message,
        "--json",
    ]
    if dry_run:
        cmd.append("--dry-run")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or "openclaw message send failed")

    try:
        return json.loads(proc.stdout) if proc.stdout.strip() else {"ok": True}
    except json.JSONDecodeError:
        return {"ok": True, "raw": proc.stdout.strip()}


def write_state(state_path: Path, alerted: List[Blocker]) -> None:
    state = _load_json(state_path, {"last_alerted": {}})
    if not isinstance(state, dict):
        state = {"last_alerted": {}}
    last_alerted = state.setdefault("last_alerted", {})
    now = datetime.now(timezone.utc).isoformat()
    for b in alerted:
        last_alerted[b.blocker_id] = now

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Escalate stale critical blockers to chat")
    parser.add_argument("--shared-state", default=str(SHARED_STATE_PATH))
    parser.add_argument("--min-age-hours", type=int, default=24)
    parser.add_argument("--cooldown-hours", type=int, default=24)
    parser.add_argument("--state-file", default=str(ALERT_STATE_PATH))
    parser.add_argument("--channel", default="telegram")
    parser.add_argument("--target", default="7991290678", help="Chat target for openclaw message send")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    shared_state = Path(args.shared_state)
    state_file = Path(args.state_file)

    stale = find_stale_critical_blockers(shared_state, args.min_age_hours)
    to_alert = filter_by_cooldown(stale, state_file, args.cooldown_hours)

    result: Dict[str, Any] = {
        "scanned": len(stale),
        "to_alert": len(to_alert),
        "min_age_hours": args.min_age_hours,
        "cooldown_hours": args.cooldown_hours,
        "sent": False,
        "target": args.target,
        "channel": args.channel,
        "blockers": [
            {
                "id": b.blocker_id,
                "priority": b.priority,
                "owner": b.owner,
                "age_hours": round(b.age_hours, 1),
            }
            for b in to_alert
        ],
    }

    if not to_alert:
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("OK: no stale critical blockers need escalation")
        return 0

    msg = build_message(to_alert, args.min_age_hours)
    send_result = send_alert(args.channel, args.target, msg, args.dry_run)

    if not args.dry_run:
        write_state(state_file, to_alert)

    result["sent"] = True
    result["send_result"] = send_result

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(msg)
        print("\nOK: escalation sent")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
