#!/usr/bin/env python3
"""
winnie_lesson_inject.py — Pre-task lesson retrieval for Winnie.

Queries agent-memory.db for top-N relevant past lessons by keyword overlap
with a task brief. Outputs a lesson block to prepend to any research task context.

Usage:
  python3 winnie_lesson_inject.py --task-brief "evaluate memU REST API"
  python3 winnie_lesson_inject.py --task-brief "dependency analysis" --limit 3
  python3 winnie_lesson_inject.py --task-brief "API timeout" --json
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

MEMORY_DB = Path.home() / ".openclaw" / "agent-memory.db"


def search_lessons(brief: str, limit: int = 5, agent: str = "winnie") -> list:
    """Search agent-memory.db FTS5 for lessons relevant to the task brief."""
    if not MEMORY_DB.exists():
        return []

    conn = sqlite3.connect(str(MEMORY_DB))
    conn.row_factory = sqlite3.Row

    # Build FTS5 query from brief keywords (AND matching)
    words = [w.strip(".,;:!?\"'()") for w in brief.split() if len(w) > 2]
    if not words:
        return []

    # Try FTS5 match first, fall back to LIKE
    results = []
    try:
        fts_query = " OR ".join(f'"{w}"' for w in words[:8])
        rows = conn.execute(
            """SELECT id, agent, cycle, topic, body, tags, created_at, outcome,
                      quality_score, memory_type
               FROM agent_memories_fts
               JOIN agent_memories ON agent_memories.rowid = agent_memories_fts.rowid
               WHERE agent_memories_fts MATCH ?
               AND (agent = ? OR agent = 'all')
               AND (expires_at IS NULL OR expires_at > datetime('now'))
               ORDER BY rank
               LIMIT ?""",
            (fts_query, agent, limit),
        ).fetchall()
        results = [dict(r) for r in rows]
    except sqlite3.Error:
        # Fallback: LIKE-based search
        like_clauses = " OR ".join(["body LIKE ?"] * len(words[:5]))
        like_params = [f"%{w}%" for w in words[:5]]
        try:
            rows = conn.execute(
                f"""SELECT id, agent, cycle, topic, body, tags, created_at, outcome,
                           quality_score, memory_type
                    FROM agent_memories
                    WHERE ({like_clauses})
                    AND (agent = ? OR agent = 'all')
                    AND (expires_at IS NULL OR expires_at > datetime('now'))
                    ORDER BY created_at DESC
                    LIMIT ?""",
                like_params + [agent, limit],
            ).fetchall()
            results = [dict(r) for r in rows]
        except sqlite3.Error:
            pass

    conn.close()
    return results


def format_lessons_markdown(lessons: list) -> str:
    """Format lessons as a markdown context block."""
    if not lessons:
        return "## Prior Lessons\n(No relevant lessons found)\n"

    lines = [
        "## Prior Lessons (auto-injected by winnie_lesson_inject.py)",
        f"_Retrieved {len(lessons)} lesson(s) at {datetime.now().strftime('%H:%M EST')}_\n",
    ]
    for i, l in enumerate(lessons, 1):
        outcome = f" [{l.get('outcome', '?')}]" if l.get('outcome') else ""
        quality = f" (q={l['quality_score']:.1f})" if l.get('quality_score') else ""
        body_preview = (l.get('body') or '')[:200]
        lines.append(f"**{i}. {l.get('topic', 'untitled')}**{outcome}{quality}")
        lines.append(f"   {body_preview}")
        lines.append(f"   _cycle: {l.get('cycle', '?')} | type: {l.get('memory_type', '?')}_\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Pre-task lesson injector for Winnie")
    parser.add_argument("--task-brief", required=True, help="Task description to match against")
    parser.add_argument("--limit", type=int, default=5, help="Max lessons to return")
    parser.add_argument("--agent", default="winnie", help="Agent to filter by")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    lessons = search_lessons(args.task_brief, limit=args.limit, agent=args.agent)

    if args.json:
        print(json.dumps(lessons, indent=2, default=str))
    else:
        print(format_lessons_markdown(lessons))


if __name__ == "__main__":
    main()
