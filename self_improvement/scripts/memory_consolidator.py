#!/usr/bin/env python3
"""
memory_consolidator.py — D-022: Sleep-Time Memory Consolidation (Rosie)

Implements EverMemOS-inspired sleep-time consolidation:
1. Dedup: merge near-duplicate entries (same agent + similar topic)
2. Quality decay: multiply quality_score × 0.9 for entries not accessed this week
3. Archive: move entries with quality_score < 0.15 to archive table

Usage:
    python3 memory_consolidator.py [--dry-run] [--decay-only] [--dedup-only] [--archive-only]
    python3 memory_consolidator.py --report

Exit codes:
    0 — consolidation complete (or dry-run reported)
    1 — error
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path.home() / ".openclaw" / "agent-memory.db"
WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
OUTPUTS = WORKSPACE / "self_improvement" / "outputs"

DECAY_FACTOR = 0.9          # per-week decay for unused memories
ARCHIVE_THRESHOLD = 0.15    # archive entries with quality below this
DEDUP_MIN_SIMILARITY = 0.85 # jaccard similarity threshold for dedup


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_archive_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_memories_archive (
            id INTEGER PRIMARY KEY,
            agent TEXT,
            topic TEXT,
            body TEXT,
            tags TEXT,
            context TEXT,
            memory_type TEXT,
            quality_score REAL,
            use_count INTEGER,
            outcome TEXT,
            provenance_score REAL,
            archived_at TEXT,
            archive_reason TEXT
        )
    """)
    conn.commit()


def jaccard_similarity(a, b):
    """Token-level Jaccard similarity between two strings."""
    tokens_a = set(re.findall(r'\w+', a.lower()))
    tokens_b = set(re.findall(r'\w+', b.lower()))
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def run_dedup(conn, dry_run=False):
    """Find and merge near-duplicate memories per agent."""
    rows = conn.execute("""
        SELECT id, agent, topic, body, quality_score, use_count
        FROM agent_memories
        ORDER BY agent, quality_score DESC
    """).fetchall()

    # Group by agent
    by_agent = {}
    for row in rows:
        agent = row['agent'] or 'unknown'
        by_agent.setdefault(agent, []).append(dict(row))

    merged_ids = []
    merge_log = []

    for agent, entries in by_agent.items():
        seen = []  # list of (canonical_id, topic, body)
        for entry in entries:
            duplicate_of = None
            for canon_id, canon_topic, canon_body in seen:
                topic_sim = jaccard_similarity(entry['topic'] or '', canon_topic or '')
                body_sim = jaccard_similarity(entry['body'] or '', canon_body or '')
                combined = 0.4 * topic_sim + 0.6 * body_sim
                if combined >= DEDUP_MIN_SIMILARITY:
                    duplicate_of = canon_id
                    break
            if duplicate_of is None:
                seen.append((entry['id'], entry['topic'], entry['body']))
            else:
                merged_ids.append(entry['id'])
                merge_log.append({
                    'agent': agent,
                    'merged_id': entry['id'],
                    'into_id': duplicate_of,
                    'topic': entry['topic']
                })
                if not dry_run:
                    # Bump use_count on canonical, delete duplicate
                    conn.execute(
                        "UPDATE agent_memories SET use_count = use_count + 1 WHERE id = ?",
                        (duplicate_of,)
                    )
                    conn.execute("DELETE FROM agent_memories WHERE id = ?", (entry['id'],))

    if not dry_run and merged_ids:
        conn.commit()

    return merge_log


def run_decay(conn, dry_run=False):
    """Apply quality decay to entries not accessed in the past week."""
    one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Entries with use_count=0 are treated as never accessed; also check last_used if column exists
    # We use use_count == 0 as proxy for "not accessed this week" (conservative)
    rows = conn.execute("""
        SELECT id, agent, topic, quality_score, use_count
        FROM agent_memories
        WHERE use_count = 0 AND quality_score > ?
    """, (ARCHIVE_THRESHOLD,)).fetchall()

    decayed = []
    for row in rows:
        new_score = round(row['quality_score'] * DECAY_FACTOR, 4)
        new_score = max(0.0, new_score)
        decayed.append({'id': row['id'], 'agent': row['agent'], 'topic': row['topic'],
                        'old_score': row['quality_score'], 'new_score': new_score})
        if not dry_run:
            conn.execute("UPDATE agent_memories SET quality_score = ? WHERE id = ?",
                         (new_score, row['id']))

    if not dry_run and decayed:
        conn.commit()

    return decayed


def run_archive(conn, dry_run=False):
    """Move entries with quality_score < threshold to archive table."""
    ensure_archive_table(conn)

    rows = conn.execute("""
        SELECT id, agent, topic, body, tags, context, memory_type,
               quality_score, use_count, outcome, provenance_score
        FROM agent_memories
        WHERE quality_score < ?
    """, (ARCHIVE_THRESHOLD,)).fetchall()

    archived = []
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        archived.append({'id': row['id'], 'agent': row['agent'],
                         'topic': row['topic'], 'quality_score': row['quality_score']})
        if not dry_run:
            conn.execute("""
                INSERT INTO agent_memories_archive
                (agent, topic, body, tags, context, memory_type, quality_score,
                 use_count, outcome, provenance_score, archived_at, archive_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row['agent'], row['topic'], row['body'], row['tags'], row['context'],
                row['memory_type'], row['quality_score'], row['use_count'],
                row['outcome'], row['provenance_score'],
                now, 'quality_below_threshold'
            ))
            conn.execute("DELETE FROM agent_memories WHERE id = ?", (row['id'],))

    if not dry_run and archived:
        conn.commit()

    return archived


def build_report(merge_log, decayed, archived, dry_run):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    prefix = "[DRY-RUN] " if dry_run else ""
    lines = [
        f"# {prefix}Memory Consolidation Report — {ts}",
        "",
        f"## Dedup: {len(merge_log)} duplicates merged",
    ]
    for m in merge_log[:10]:
        lines.append(f"  - [{m['agent']}] `{m['topic'][:60]}` → merged into id={m['into_id']}")
    if len(merge_log) > 10:
        lines.append(f"  - ... and {len(merge_log)-10} more")

    lines += ["", f"## Decay: {len(decayed)} entries decayed (×{DECAY_FACTOR}/week)"]
    for d in decayed[:10]:
        lines.append(f"  - [{d['agent']}] `{d['topic'][:50]}` {d['old_score']:.3f} → {d['new_score']:.3f}")
    if len(decayed) > 10:
        lines.append(f"  - ... and {len(decayed)-10} more")

    lines += ["", f"## Archive: {len(archived)} entries moved to memories_archive (quality < {ARCHIVE_THRESHOLD})"]
    for a in archived[:10]:
        lines.append(f"  - [{a['agent']}] `{a['topic'][:50]}` (score={a['quality_score']:.3f})")
    if len(archived) > 10:
        lines.append(f"  - ... and {len(archived)-10} more")

    lines += ["", "---", f"*Generated by memory_consolidator.py | D-022*"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="D-022: Sleep-Time Memory Consolidation")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--decay-only", action="store_true")
    parser.add_argument("--dedup-only", action="store_true")
    parser.add_argument("--archive-only", action="store_true")
    parser.add_argument("--report", action="store_true", help="Print report to stdout only")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}", file=sys.stderr)
        return 1

    conn = get_conn()
    dry_run = args.dry_run or args.report

    merge_log, decayed, archived = [], [], []

    try:
        if not args.decay_only and not args.archive_only:
            merge_log = run_dedup(conn, dry_run=dry_run)
        if not args.dedup_only and not args.archive_only:
            decayed = run_decay(conn, dry_run=dry_run)
        if not args.dedup_only and not args.decay_only:
            archived = run_archive(conn, dry_run=dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        conn.close()
        return 1

    conn.close()

    report = build_report(merge_log, decayed, archived, dry_run)
    print(report)

    if args.json:
        print(json.dumps({
            "duplicates_merged": len(merge_log),
            "entries_decayed": len(decayed),
            "entries_archived": len(archived),
            "dry_run": dry_run,
        }))

    # Write output file
    if not dry_run:
        ts_str = datetime.now().strftime("%Y-%m-%d-%H")
        out_path = OUTPUTS / f"{ts_str}-memory-consolidation.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report)
        print(f"\nReport written to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
