#!/usr/bin/env python3
"""
Sync MEMORY.md to SQLite DB (One-Way: MD -> DB)
Usage: python3 memory_sync.py [--force]

1. Checks hash of MEMORY.md.
2. If changed since last sync (stored in DB metadata or state file), parses MEMORY.md.
3. For each section:
   - Computes hash of content.
   - Upserts into 'memories' table if hash differs.
   - Tags: 'memory-md', 'section:<name>'
4. Updates last-sync timestamp.
"""

import sys
import os
import sqlite3
import hashlib
import re
import datetime
import json

MEMORY_MD_PATH = "/Users/harrisonfethe/.openclaw/workspace/MEMORY.md"
DB_PATH = os.path.expanduser("~/.openclaw/agent-memory.db")
STATE_FILE = "/Users/harrisonfethe/.openclaw/workspace/self_improvement/memory_sync_state.json"

def get_file_hash(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def parse_memory_md(path):
    """Parses MEMORY.md into sections."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by level 2 headers (## Section)
    # Assumes standard format
    sections = {}
    
    # Find all level 2 headers
    # Logic: everything after "## Name" until next "## " is body
    # Use simple split for robustness
    parts = re.split(r'(^|\n)##\s+', content)
    
    # parts[0] is usually preamble (before first ##)
    if parts[0].strip():
        sections["PREAMBLE"] = parts[0].strip()
        
    # The split includes the delimiter capture, so we iterate in steps
    # But re.split with capture groups is tricky.
    # Let's use simple line iteration.
    
    current_section = "PREAMBLE"
    buffer = []
    
    lines = content.splitlines()
    for line in lines:
        if line.startswith("## "):
            # Save previous
            if buffer:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = line[3:].strip()
            buffer = []
        else:
            buffer.append(line)
            
    if buffer:
        sections[current_section] = "\n".join(buffer).strip()
        
    return sections

def update_db(sections):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    updates = 0
    inserts = 0
    
    current_time = datetime.datetime.now().isoformat()
    
    for title, body in sections.items():
        if not body: continue
        
        # We use the topic as the primary identifier for MEMORY.md sync
        # Since titles are unique in MEMORY.md, this is safe.
        # We look for existing entries from source_file='MEMORY.md' with same topic
        
        query = "SELECT id, body FROM agent_memories WHERE source_file = ? AND topic = ?"
        c.execute(query, ("MEMORY.md", title))
        rows = c.fetchall()
        
        body_hash = hashlib.md5(body.encode('utf-8')).hexdigest()
        
        if rows:
            # Check for update needed
            row_id, current_body = rows[0]
            current_hash = hashlib.md5(current_body.encode('utf-8')).hexdigest()
            
            if current_hash != body_hash:
                print(f"[UPDATE] Section '{title}' changed.")
                c.execute("""
                    UPDATE agent_memories 
                    SET body = ?, created_at = ?, cycle = ? 
                    WHERE id = ?
                """, (body, current_time, "memory-sync", row_id))
                updates += 1
        else:
            # Insert new
            print(f"[INSERT] New section '{title}'.")
            tags = json.dumps(["source:MEMORY.md", f"section:{title}"])
            c.execute("""
                INSERT INTO agent_memories 
                (agent, cycle, topic, body, source_file, tags, created_at, memory_type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("rosie", "memory-sync", title, body, "MEMORY.md", tags, current_time, "factual"))
            inserts += 1
            
    conn.commit()
    conn.close()
    return updates, inserts

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        sys.exit(1)
        
    current_hash = get_file_hash(MEMORY_MD_PATH)
    
    # Load state
    last_hash = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                last_hash = state.get('hash')
        except:
            pass
            
    if last_hash == current_hash and "--force" not in sys.argv:
        print("MEMORY.md unchanged. No sync needed.")
        sys.exit(0)
        
    print(f"Syncing MEMORY.md to DB... (Hash: {current_hash[:8]})")
    sections = parse_memory_md(MEMORY_MD_PATH)
    updates, inserts = update_db(sections)
    
    print(f"Sync complete. Updates: {updates}, Inserts: {inserts}")
    
    # Save state
    with open(STATE_FILE, 'w') as f:
        json.dump({'hash': current_hash, 'last_sync': datetime.datetime.now().isoformat()}, f)
    
    # After sync: push new high-quality DB discoveries back to MEMORY.md
    run_updater()

def run_updater():
    """Run memory_md_updater.py after sync to push new DB discoveries back to MEMORY.md.
    
    Added by Rosie 2026-02-21 — closes the memory pipeline loop:
        MEMORY.md → DB (memory_sync) → MEMORY.md (memory_md_updater)
    Failures are non-fatal: print warning and continue.
    """
    import subprocess
    updater_path = os.path.join(os.path.dirname(__file__), "memory_md_updater.py")
    if not os.path.exists(updater_path):
        print(f"[memory_sync] WARNING: memory_md_updater.py not found at {updater_path}; skipping.")
        return
    try:
        result = subprocess.run(
            [sys.executable, updater_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            lines = [l for l in result.stdout.strip().splitlines() if l]
            summary = lines[-1] if lines else "ok"
            print(f"[memory_sync] memory_md_updater: {summary}")
        else:
            print(f"[memory_sync] WARNING: memory_md_updater exited {result.returncode}: "
                  f"{result.stderr.strip()[:200]}")
    except subprocess.TimeoutExpired:
        print("[memory_sync] WARNING: memory_md_updater timed out after 120s; skipping.")
    except Exception as exc:
        print(f"[memory_sync] WARNING: memory_md_updater error: {exc}")


if __name__ == "__main__":
    main()
