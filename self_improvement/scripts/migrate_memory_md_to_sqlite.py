#!/usr/bin/env python3
"""
migrate_memory_md_to_sqlite.py
Rosie Cycle: 2026-02-18-00

Migrates MEMORY.md → agent-memory.db (SQLite + FTS5).
Each H2/H3 section becomes one memory row with auto-derived tags.

Usage:
    /opt/homebrew/bin/python3.13 migrate_memory_md_to_sqlite.py [--dry-run]
"""

import re
import sqlite3
import sys
import os
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
MEMORY_MD_PATH = "/Users/harrisonfethe/.openclaw/workspace/MEMORY.md"
DB_PATH = "/Volumes/EDrive/Projects/agent-coordination/agent-memory.db"
AGENT = "rosie"
CYCLE = "2026-02-18-00-rosie"
SOURCE_FILE = "MEMORY.md"
DRY_RUN = "--dry-run" in sys.argv

# ── Tag derivation ─────────────────────────────────────────────────────────────
TAG_RULES = [
    (r"\btrad(e|ing|er)\b", "trading"),
    (r"\bjiraflow\b", "jiraflow"),
    (r"\bschwab\b", "schwab"),
    (r"\btoken\b", "token"),
    (r"\bsplit.brain\b", "split-brain"),
    (r"\bcrisis\b", "crisis"),
    (r"\blesson\b", "lesson"),
    (r"\boutreach\b", "outreach"),
    (r"\binfrastructure\b", "infrastructure"),
    (r"\bmemory\b", "memory"),
    (r"\bsecurity\b", "security"),
    (r"\bcrm\b", "crm"),
    (r"\bcoordination\b", "coordination"),
    (r"\bcron\b", "cron"),
    (r"\btelegram\b", "telegram"),
    (r"\bmacku?e?r?\b|\bmacklemore\b|\bmack\b", "mack"),
    (r"\bwinnie\b", "winnie"),
    (r"\brosie\b", "rosie"),
    (r"\blenny\b", "lenny"),
    (r"\bsqlite\b|\bsql\b|\bfts5\b", "sqlite"),
    (r"\bvector\b|\bembedding\b", "vector"),
    (r"\bautonomous\b", "autonomous"),
    (r"\bblockage?\b|\bblocker\b", "blocker"),
    (r"\bapi\b|\boauth\b|\bauth\b", "api"),
    (r"\bschedule\b|\bcron\b|\bloop\b", "schedule"),
]

def derive_tags(text: str) -> str:
    tags = set()
    lower = text.lower()
    for pattern, tag in TAG_RULES:
        if re.search(pattern, lower):
            tags.add(tag)
    return ",".join(sorted(tags)) if tags else ""


# ── Parser ─────────────────────────────────────────────────────────────────────
def parse_sections(content: str) -> list[dict]:
    """Split MEMORY.md into sections at H2/H3 headers."""
    section_pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
    matches = list(section_pattern.finditer(content))

    sections = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()

        # Skip nearly-empty sections
        if len(body) < 30:
            continue

        level = len(match.group(1))  # 2 or 3
        topic = match.group(2).strip()
        full_body = f"{'##' if level == 2 else '###'} {topic}\n\n{body}"

        sections.append({
            "topic": topic,
            "body": full_body,
            "tags": derive_tags(full_body),
        })

    return sections


# ── DB insertion ──────────────────────────────────────────────────────────────
def insert_memories(conn: sqlite3.Connection, sections: list[dict]) -> int:
    cur = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    count = 0
    for s in sections:
        cur.execute(
            """
            INSERT INTO agent_memories (agent, cycle, topic, body, source_file, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (AGENT, CYCLE, s["topic"], s["body"], SOURCE_FILE, s["tags"], now),
        )
        rowid = cur.lastrowid
        # Keep FTS5 index in sync
        cur.execute(
            "INSERT INTO agent_memories_fts(rowid, body, tags) VALUES (?, ?, ?)",
            (rowid, s["body"], s["tags"]),
        )
        count += 1
    conn.commit()
    return count


# ── Verification ───────────────────────────────────────────────────────────────
def verify(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM agent_memories WHERE source_file=?", (SOURCE_FILE,))
    n = cur.fetchone()[0]
    print(f"  ✅ Rows in agent_memories from {SOURCE_FILE}: {n}")

    # FTS5 spot-check
    cur.execute(
        "SELECT a.id, a.topic FROM agent_memories_fts f JOIN agent_memories a ON f.rowid=a.id "
        "WHERE agent_memories_fts MATCH 'crisis' ORDER BY rank LIMIT 3"
    )
    rows = cur.fetchall()
    print(f"  ✅ FTS5 'crisis' matches: {len(rows)}")
    for r in rows:
        print(f"     id={r[0]} | {r[1]}")

    cur.execute(
        "SELECT a.id, a.topic FROM agent_memories_fts f JOIN agent_memories a ON f.rowid=a.id "
        "WHERE agent_memories_fts MATCH 'trading' ORDER BY rank LIMIT 3"
    )
    rows = cur.fetchall()
    print(f"  ✅ FTS5 'trading' matches: {len(rows)}")
    for r in rows:
        print(f"     id={r[0]} | {r[1]}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(MEMORY_MD_PATH):
        print(f"ERROR: MEMORY.md not found at {MEMORY_MD_PATH}")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: agent-memory.db not found at {DB_PATH}")
        sys.exit(1)

    with open(MEMORY_MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    sections = parse_sections(content)
    print(f"Parsed {len(sections)} sections from MEMORY.md")

    if DRY_RUN:
        print("\n=== DRY RUN — top sections ===")
        for s in sections[:5]:
            print(f"  topic: {s['topic']}")
            print(f"  tags : {s['tags']}")
            print(f"  body : {s['body'][:120].replace(chr(10), ' ')}...")
            print()
        return

    conn = sqlite3.connect(DB_PATH)
    # Verify no duplicates (idempotent re-run guard)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM agent_memories WHERE source_file=?", (SOURCE_FILE,))
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"⚠️  {existing} rows already exist for source_file={SOURCE_FILE}. Skipping to avoid duplicates.")
        verify(conn)
        conn.close()
        return

    inserted = insert_memories(conn, sections)
    print(f"Inserted {inserted} memory rows")

    print("\nVerification:")
    verify(conn)
    conn.close()
    print("\nMigration complete ✅")


if __name__ == "__main__":
    main()
