#!/usr/bin/env python3
"""change_monitor.py

Purpose:
  Minimal "auto-update" mechanism for the self-improvement system.

What it does:
  - Computes sha256 hashes for a curated set of coordination files.
  - Stores last-seen hashes in a local state file (default: ~/.openclaw/si-change-monitor.json).
  - On changes, prints a concise report (text or JSON).
  - Optionally appends a broadcast item into shared-state.json so other agents will notice.

Why local state:
  shared-state.json is for coordination, not for high-frequency hash bookkeeping.

Usage:
  python3 self_improvement/scripts/change_monitor.py --update
  python3 self_improvement/scripts/change_monitor.py --json --update
  python3 self_improvement/scripts/change_monitor.py --broadcast --update

Exit codes:
  0 = no changes
  3 = changes detected
  4 = error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure scripts directory is on path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_mutex import file_lock

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
SHARED_STATE = WORKSPACE / "self_improvement/shared-state.json"

DEFAULT_STATE_PATH = Path.home() / ".openclaw" / "si-change-monitor.json"

# Curated list: coordination + profiles + key scripts.
WATCH_PATHS = [
    WORKSPACE / "agents/rosie.md",
    WORKSPACE / "agents/mack.md",
    WORKSPACE / "agents/winnie.md",
    WORKSPACE / "agents/lenny.md",
    WORKSPACE / "self_improvement/TODO.md",
    WORKSPACE / "self_improvement/LOOPS.md",
    WORKSPACE / "self_improvement/CHANGELOG.md",
    WORKSPACE / "self_improvement/shared-state.json",
    WORKSPACE / "self_improvement/scripts/continuation_check.py",
    WORKSPACE / "self_improvement/scripts/agent_memory_cli.py",
]


@dataclass
class Change:
    path: str
    kind: str  # added|modified|removed
    old: str | None = None
    new: str | None = None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state(state_path: Path) -> Dict[str, str]:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Atomically write text to avoid partial-file corruption under concurrent writers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding=encoding, dir=path.parent, delete=False) as tf:
        tf.write(content)
        tmp_path = Path(tf.name)
    os.replace(tmp_path, path)


def load_json_with_retry(path: Path, retries: int = 3, delay_s: float = 0.15) -> dict:
    """Read JSON with short retries to tolerate concurrent atomic replacements."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return json.loads(path.read_text("utf-8"))
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(delay_s)
    raise RuntimeError(f"failed to read JSON from {path}: {last_exc}")


def save_state(state_path: Path, hashes: Dict[str, str]) -> None:
    atomic_write_text(state_path, json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compute_hashes(paths: List[Path]) -> Tuple[Dict[str, str], List[str]]:
    hashes: Dict[str, str] = {}
    missing: List[str] = []
    for p in paths:
        if not p.exists():
            missing.append(str(p))
            continue
        try:
            hashes[str(p)] = sha256_file(p)
        except OSError:
            missing.append(str(p))
    return hashes, missing


def diff(old: Dict[str, str], new: Dict[str, str], missing_now: List[str]) -> List[Change]:
    changes: List[Change] = []
    old_keys = set(old.keys())
    new_keys = set(new.keys())

    for k in sorted(new_keys - old_keys):
        changes.append(Change(path=k, kind="added", new=new[k]))

    for k in sorted(old_keys & new_keys):
        if old[k] != new[k]:
            changes.append(Change(path=k, kind="modified", old=old[k], new=new[k]))

    # if a previously tracked file vanishes, call it removed
    for k in sorted(old_keys - new_keys):
        changes.append(Change(path=k, kind="removed", old=old[k]))

    # treat missing-now as removed if it was previously tracked
    for k in sorted(set(missing_now) & old_keys):
        # already handled above if missing implies not in new
        pass

    return changes


def append_broadcast(shared_state_path: Path, message: str) -> None:
    with file_lock(shared_state_path):
        data = load_json_with_retry(shared_state_path)
        if not isinstance(data, dict):
            raise RuntimeError(f"shared state must be a JSON object: {shared_state_path}")
    
        broadcasts = data.get("broadcasts")
        if not isinstance(broadcasts, list):
            broadcasts = []
            data["broadcasts"] = broadcasts
    
        item = {
            "id": f"bc-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "message": message,
            "ack_by": {},
        }
        broadcasts.append(item)
    
        data["last_updated"] = datetime.now().isoformat()
        data["last_updated_by"] = "rosie"
    
        atomic_write_text(shared_state_path, json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=str(DEFAULT_STATE_PATH))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--update", action="store_true", help="write current hashes to state file")
    ap.add_argument(
        "--broadcast",
        action="store_true",
        help="if changes are detected, append a broadcast item to shared-state.json",
    )
    args = ap.parse_args()

    state_path = Path(args.state)
    old_hashes = load_state(state_path)
    new_hashes, missing = compute_hashes(WATCH_PATHS)
    changes = diff(old_hashes, new_hashes, missing)

    report = {
        "state_path": str(state_path),
        "watched": [str(p) for p in WATCH_PATHS],
        "missing": missing,
        "num_changes": len(changes),
        "changes": [c.__dict__ for c in changes],
        "generated_at": datetime.now().isoformat(),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if not changes:
            print("change_monitor: no changes")
        else:
            print(f"change_monitor: {len(changes)} change(s)")
            for c in changes:
                print(f"- {c.kind}: {c.path}")
            if missing:
                print(f"- missing: {len(missing)}")

    if changes and args.broadcast:
        msg = (
            "[AUTO-UPDATE] Detected changes in coordination files. "
            "Run change_monitor.py --json for details. Summary: "
            + ", ".join([f"{c.kind}:{Path(c.path).name}" for c in changes][:8])
        )
        append_broadcast(SHARED_STATE, msg)

    if args.update:
        save_state(state_path, new_hashes)

    return 3 if changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
