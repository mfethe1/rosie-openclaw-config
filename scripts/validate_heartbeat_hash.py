#!/usr/bin/env python3
import hashlib
import json
import os
import sys
import fcntl
from pathlib import Path

WORKSPACE_DIR = Path("/Users/harrisonfethe/.openclaw/workspace")
HEARTBEAT_FILE = WORKSPACE_DIR / "HEARTBEAT.md"
STATE_FILE = WORKSPACE_DIR / "shared_state" / "current" / "heartbeat_hash.json"

def get_file_hash(filepath: Path) -> str:
    if not filepath.exists():
        return ""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def main():
    if not HEARTBEAT_FILE.exists():
        print(f"Error: {HEARTBEAT_FILE} not found.")
        sys.exit(1)

    current_hash = get_file_hash(HEARTBEAT_FILE)
    
    # Ensure state directory exists
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    state = {}
    conflict = False
    
    # Use file locking to prevent race conditions during state read/write
    lock_file = STATE_FILE.with_suffix('.lock')
    with open(lock_file, 'w') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE, 'r') as f:
                        state = json.load(f)
                except json.JSONDecodeError:
                    state = {}
            
            stored_hash = state.get("hash")
            
            if stored_hash and stored_hash != current_hash:
                print(f"CONFLICT DETECTED: HEARTBEAT.md hash changed from {stored_hash[:8]} to {current_hash[:8]}")
                conflict = True
            elif not stored_hash or stored_hash == current_hash:
                print(f"OK: HEARTBEAT.md hash matches ({current_hash[:8]})")
            
            # Update the stored hash
            state["hash"] = current_hash
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
                
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)

    if conflict:
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()