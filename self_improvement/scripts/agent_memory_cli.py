#!/usr/bin/env python3
"""agent_memory_cli.py

A tiny, dependency-free CLI for OpenClaw "agent memory" backed by SQLite + FTS5.

Design goals (per Winnie D-007/D-008/D-009):
- Use LOCAL db path by default: ~/.openclaw/agent-memory.db
- Enable WAL mode (requires local filesystem; SMB blocks WAL)
- After writes, rsync db -> EDrive as durable backup (best-effort)

Schema expected (Phase 1):
  agent_memories(
    id, agent, cycle, topic, body, source_file, tags, context, created_at
  )
  agent_memories_fts(body, tags, context) with triggers

Usage examples:
  python3 agent_memory_cli.py init
  python3 agent_memory_cli.py store \
    --agent mack --cycle 2026-02-18-08-mack \
    --topic "auto-tagging" --body "..." \
    --tags "memory,sqlite" --context "why/when/how this matters"
  python3 agent_memory_cli.py search "wal mode" --limit 5
  python3 agent_memory_cli.py get 56
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

DEFAULT_LOCAL_DB = Path.home() / ".openclaw" / "agent-memory.db"
DEFAULT_EDRIVE_DB = Path("/Volumes/EDrive/Projects/agent-coordination/agent-memory.db")

# NOTE: For existing DBs, CREATE TABLE / CREATE VIRTUAL TABLE are not enough
# to evolve schema. We run explicit migrations in connect().
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_memories (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  agent       TEXT NOT NULL,
  cycle       TEXT NOT NULL,
  topic       TEXT NOT NULL,
  body        TEXT NOT NULL,
  source_file TEXT,
  tags        TEXT,
  context     TEXT,
  memory_type TEXT NOT NULL DEFAULT 'factual' CHECK(memory_type IN ('factual','experiential','working','procedural')),
  provenance_score REAL NOT NULL DEFAULT 0.5 CHECK(provenance_score >= 0.0 AND provenance_score <= 1.0),
  quality_score REAL NOT NULL DEFAULT 0.5 CHECK(quality_score >= 0.0 AND quality_score <= 1.0),
  use_count INTEGER NOT NULL DEFAULT 0,
  outcome TEXT,
  expires_at TEXT DEFAULT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS agent_memories_fts USING fts5(
  body,
  tags,
  context,
  content='agent_memories',
  content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS fts_insert AFTER INSERT ON agent_memories BEGIN
  INSERT INTO agent_memories_fts(rowid, body, tags, context)
  VALUES (new.id, new.body, new.tags, new.context);
END;

CREATE TRIGGER IF NOT EXISTS fts_delete AFTER DELETE ON agent_memories BEGIN
  INSERT INTO agent_memories_fts(agent_memories_fts, rowid, body, tags, context)
  VALUES ('delete', old.id, old.body, old.tags, old.context);
END;

CREATE TRIGGER IF NOT EXISTS fts_update AFTER UPDATE ON agent_memories BEGIN
  INSERT INTO agent_memories_fts(agent_memories_fts, rowid, body, tags, context)
  VALUES ('delete', old.id, old.body, old.tags, old.context);

  INSERT INTO agent_memories_fts(rowid, body, tags, context)
  VALUES (new.id, new.body, new.tags, new.context);
END;

CREATE TABLE IF NOT EXISTS skills (
  name TEXT PRIMARY KEY,
  trigger TEXT,
  inputs TEXT,
  steps TEXT,
  outputs TEXT,
  agent_owner TEXT,
  use_count INTEGER DEFAULT 0,
  last_used TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
  name,
  trigger,
  steps,
  content='skills',
  content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS skills_fts_insert AFTER INSERT ON skills BEGIN
  INSERT INTO skills_fts(rowid, name, trigger, steps)
  VALUES (new.rowid, new.name, new.trigger, new.steps);
END;

CREATE TRIGGER IF NOT EXISTS skills_fts_delete AFTER DELETE ON skills BEGIN
  INSERT INTO skills_fts(skills_fts, rowid, name, trigger, steps)
  VALUES ('delete', old.rowid, old.name, old.trigger, old.steps);
END;

CREATE TRIGGER IF NOT EXISTS skills_fts_update AFTER UPDATE ON skills BEGIN
  INSERT INTO skills_fts(skills_fts, rowid, name, trigger, steps)
  VALUES ('delete', old.rowid, old.name, old.trigger, old.steps);
  INSERT INTO skills_fts(rowid, name, trigger, steps)
  VALUES (new.rowid, new.name, new.trigger, new.steps);
END;
""".strip()


@dataclass
class DbConfig:
    db_path: Path
    edrive_path: Path
    rsync: bool


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(r[1] == col for r in rows)


def _rebuild_fts(conn: sqlite3.Connection) -> None:
    # Drop triggers first (safe if missing)
    conn.executescript(
        """
        DROP TRIGGER IF EXISTS fts_insert;
        DROP TRIGGER IF EXISTS fts_delete;
        DROP TRIGGER IF EXISTS fts_update;
        DROP TABLE IF EXISTS agent_memories_fts;
        """.strip()
    )

    # Recreate FTS + triggers using current schema.
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS agent_memories_fts USING fts5(
          body,
          tags,
          context,
          content='agent_memories',
          content_rowid='id'
        );

        CREATE TRIGGER IF NOT EXISTS fts_insert AFTER INSERT ON agent_memories BEGIN
          INSERT INTO agent_memories_fts(rowid, body, tags, context)
          VALUES (new.id, new.body, new.tags, new.context);
        END;

        CREATE TRIGGER IF NOT EXISTS fts_delete AFTER DELETE ON agent_memories BEGIN
          INSERT INTO agent_memories_fts(agent_memories_fts, rowid, body, tags, context)
          VALUES ('delete', old.id, old.body, old.tags, old.context);
        END;

        CREATE TRIGGER IF NOT EXISTS fts_update AFTER UPDATE ON agent_memories BEGIN
          INSERT INTO agent_memories_fts(agent_memories_fts, rowid, body, tags, context)
          VALUES ('delete', old.id, old.body, old.tags, old.context);

          INSERT INTO agent_memories_fts(rowid, body, tags, context)
          VALUES (new.id, new.body, new.tags, new.context);
        END;
        """.strip()
    )

    # Backfill from content table.
    conn.execute("INSERT INTO agent_memories_fts(agent_memories_fts) VALUES ('rebuild');")


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent, forward-only migrations.

    - Adds agent_memories.context if missing.
    - Adds agent_memories.memory_type if missing.
    - Rebuilds FTS table/triggers if they don't include context.
    """
    if not _has_column(conn, "agent_memories", "context"):
        conn.execute("ALTER TABLE agent_memories ADD COLUMN context TEXT;")

    if not _has_column(conn, "agent_memories", "memory_type"):
        conn.execute(
            "ALTER TABLE agent_memories "
            "ADD COLUMN memory_type TEXT NOT NULL DEFAULT 'factual' "
            "CHECK(memory_type IN ('factual','experiential','working','procedural'));"
        )

    if not _has_column(conn, "agent_memories", "provenance_score"):
        conn.execute(
            "ALTER TABLE agent_memories "
            "ADD COLUMN provenance_score REAL NOT NULL DEFAULT 0.5 "
            "CHECK(provenance_score >= 0.0 AND provenance_score <= 1.0);"
        )

    if not _has_column(conn, "agent_memories", "quality_score"):
        conn.execute(
            "ALTER TABLE agent_memories "
            "ADD COLUMN quality_score REAL NOT NULL DEFAULT 0.5 "
            "CHECK(quality_score >= 0.0 AND quality_score <= 1.0);"
        )

    if not _has_column(conn, "agent_memories", "use_count"):
        conn.execute("ALTER TABLE agent_memories ADD COLUMN use_count INTEGER NOT NULL DEFAULT 0;")

    if not _has_column(conn, "agent_memories", "outcome"):
        conn.execute("ALTER TABLE agent_memories ADD COLUMN outcome TEXT;")

    if not _has_column(conn, "agent_memories", "expires_at"):
        conn.execute("ALTER TABLE agent_memories ADD COLUMN expires_at TEXT DEFAULT NULL;")

    # Virtual table schema evolution isn't automatic; rebuild if needed.
    if not _has_column(conn, "agent_memories_fts", "context"):
        _rebuild_fts(conn)

    # Ensure skills table exists (for existing DBs where SCHEMA_SQL ran before update)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skills (
          name TEXT PRIMARY KEY,
          trigger TEXT,
          inputs TEXT,
          steps TEXT,
          outputs TEXT,
          agent_owner TEXT,
          use_count INTEGER DEFAULT 0,
          last_used TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    # Ensure skills FTS exists
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
          name,
          trigger,
          steps,
          content='skills',
          content_rowid='rowid'
        );
        """
    )
    # Ensure triggers exist
    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS skills_fts_insert AFTER INSERT ON skills BEGIN
          INSERT INTO skills_fts(rowid, name, trigger, steps)
          VALUES (new.rowid, new.name, new.trigger, new.steps);
        END;

        CREATE TRIGGER IF NOT EXISTS skills_fts_delete AFTER DELETE ON skills BEGIN
          INSERT INTO skills_fts(skills_fts, rowid, name, trigger, steps)
          VALUES ('delete', old.rowid, old.name, old.trigger, old.steps);
        END;

        CREATE TRIGGER IF NOT EXISTS skills_fts_update AFTER UPDATE ON skills BEGIN
          INSERT INTO skills_fts(skills_fts, rowid, name, trigger, steps)
          VALUES ('delete', old.rowid, old.name, old.trigger, old.steps);
          INSERT INTO skills_fts(rowid, name, trigger, steps)
          VALUES (new.rowid, new.name, new.trigger, new.steps);
        END;
        """
    )


def _seed_skills(conn: sqlite3.Connection) -> None:
    """Seed initial skills if table empty."""
    count = conn.execute("SELECT count(*) FROM skills").fetchone()[0]
    if count > 0:
        return

    skills = [
        (
            "smoke-test",
            "verify task completion",
            "agent_name, task_key, output_file",
            "bash /Users/harrisonfethe/.openclaw/workspace/memu_server/smoke_test.sh <agent> <key> <file>",
            "exit code 0 (PASS) or 1 (FAIL)",
            "mack",
        ),
        (
            "memu-handoff",
            "store cycle result",
            "agent_id, key, content",
            "curl -X POST http://localhost:12345/store -d ...",
            "json response",
            "mack",
        ),
        (
            "db-search",
            "recall memory",
            "query",
            "python3 agent_memory_cli.py search <query>",
            "text snippet",
            "mack",
        ),
    ]
    conn.executemany(
        "INSERT INTO skills(name, trigger, inputs, steps, outputs, agent_owner) VALUES (?,?,?,?,?,?)",
        skills,
    )
    print(f"Seeded {len(skills)} initial skills.")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Make reads/writes resilient under occasional contention.
    conn.execute("PRAGMA busy_timeout=2500;")

    # Prefer WAL for concurrency (only works on local filesystems).
    # If WAL is unsupported, SQLite will return the active mode; we just proceed.
    try:
        mode = conn.execute("PRAGMA journal_mode=WAL;").fetchone()[0]
    except sqlite3.Error:
        mode = None

    # Sensible defaults for WAL workloads.
    try:
        conn.execute("PRAGMA synchronous=NORMAL;")
    except sqlite3.Error:
        pass

    # Ensure schema exists (idempotent) then run migrations.
    conn.executescript(SCHEMA_SQL)
    _migrate(conn)
    _seed_skills(conn)
    conn.commit()

    if mode and mode.lower() != "wal":
        # Not fatal; common if user points to SMB.
        eprint(f"NOTE: journal_mode requested WAL but active mode is '{mode}'.")

    return conn


def maybe_bootstrap_from_edrive(local_db: Path, edrive_db: Path) -> str:
    """If local db missing and EDrive db exists, copy it over. Returns action string."""
    if local_db.exists():
        return "local_exists"

    if edrive_db.exists():
        local_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(edrive_db, local_db)
        return "copied_from_edrive"

    return "created_new"


def rsync_to_edrive(local_db: Path, edrive_db: Path) -> None:
    edrive_db.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-az", str(local_db), str(edrive_db)]
    # Best-effort: don't crash caller on rsync errors.
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        eprint("WARNING: rsync not found; skipping sync.")
    except Exception as ex:
        eprint(f"WARNING: rsync failed to start: {ex}")


def cmd_init(cfg: DbConfig) -> int:
    action = maybe_bootstrap_from_edrive(cfg.db_path, cfg.edrive_path)
    conn = connect(cfg.db_path)
    conn.close()

    # Always do a one-shot rsync on init when requested.
    if cfg.rsync and cfg.db_path.exists():
        rsync_to_edrive(cfg.db_path, cfg.edrive_path)

    print(f"db={cfg.db_path} action={action}")
    return 0


def cmd_store(
    cfg: DbConfig,
    agent: str,
    cycle: str,
    topic: str,
    body: str,
    tags: str | None,
    context: str | None,
    memory_type: str,
    provenance_score: float,
    expires_at: str | None,
    source_file: str | None,
) -> int:
    conn = connect(cfg.db_path)
    cur = conn.execute(
        """
        INSERT INTO agent_memories(
          agent, cycle, topic, body, source_file, tags, context, memory_type, provenance_score, expires_at
        ) VALUES (
          ?,?,?,?,?,?,?,?, ?,
          CASE
            WHEN ? IS NOT NULL THEN ?
            WHEN ? = 'working' THEN datetime('now', '+3 hours')
            ELSE NULL
          END
        )
        """,
        (
            agent,
            cycle,
            topic,
            body,
            source_file,
            tags,
            context,
            memory_type,
            provenance_score,
            expires_at,
            expires_at,
            memory_type,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    if cfg.rsync:
        rsync_to_edrive(cfg.db_path, cfg.edrive_path)

    print(str(new_id))
    return 0


def cmd_get(cfg: DbConfig, mem_id: int) -> int:
    conn = connect(cfg.db_path)
    row = conn.execute(
        "SELECT id, agent, cycle, topic, body, source_file, tags, context, memory_type, provenance_score, quality_score, use_count, outcome, expires_at, created_at FROM agent_memories WHERE id=?",
        (mem_id,),
    ).fetchone()
    conn.close()

    if not row:
        eprint("not_found")
        return 2

    print(
        "\n".join(
            [
                f"id: {row['id']}",
                f"agent: {row['agent']}",
                f"cycle: {row['cycle']}",
                f"topic: {row['topic']}",
                f"tags: {row['tags']}",
                f"context: {row['context']}",
                f"memory_type: {row['memory_type']}",
                f"provenance_score: {row['provenance_score']}",
                f"quality_score: {row['quality_score']}",
                f"use_count: {row['use_count']}",
                f"outcome: {row['outcome']}",
                f"expires_at: {row['expires_at']}",
                f"source_file: {row['source_file']}",
                f"created_at: {row['created_at']}",
                "body:",
                str(row["body"]),
            ]
        )
    )
    return 0


def cmd_search(cfg: DbConfig, query: str, limit: int, intent=None, query_type=None) -> int:
    conn = connect(cfg.db_path)

    base_filter = "AND (m.expires_at IS NULL OR m.expires_at > datetime('now'))"

    if query_type == "temporal":
        # Prefer recent memories: rank by created_at DESC, then score
        sql = f"""
            SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                   bm25(agent_memories_fts) AS score,
                   snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
            FROM agent_memories_fts
            JOIN agent_memories m ON m.id = agent_memories_fts.rowid
            WHERE agent_memories_fts MATCH ? {base_filter}
            ORDER BY m.created_at DESC, score
            LIMIT ?;
        """
        rows = conn.execute(sql, (query, limit)).fetchall()

    elif query_type == "causal":
        # Causal queries: weight context field + causal tags (why, because, caused, result)
        sql = f"""
            SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                   bm25(agent_memories_fts) AS score,
                   snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
            FROM agent_memories_fts
            JOIN agent_memories m ON m.id = agent_memories_fts.rowid
            WHERE agent_memories_fts MATCH ? {base_filter}
              AND (
                lower(COALESCE(m.context, '')) LIKE '%why%'
                OR lower(COALESCE(m.context, '')) LIKE '%because%'
                OR lower(COALESCE(m.context, '')) LIKE '%caused%'
                OR lower(COALESCE(m.tags, '')) LIKE '%causal%'
                OR lower(COALESCE(m.tags, '')) LIKE '%root-cause%'
                OR lower(COALESCE(m.tags, '')) LIKE '%lesson%'
              )
            ORDER BY score
            LIMIT ?;
        """
        rows = conn.execute(sql, (query, limit)).fetchall()
        # If too few results, fall back to full search
        if len(rows) < 2:
            rows = conn.execute(
                f"""SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                       bm25(agent_memories_fts) AS score,
                       snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
                    FROM agent_memories_fts
                    JOIN agent_memories m ON m.id = agent_memories_fts.rowid
                    WHERE agent_memories_fts MATCH ? {base_filter}
                    ORDER BY score LIMIT ?;""",
                (query, limit),
            ).fetchall()

    elif query_type == "entity":
        # Entity queries: search primarily in topic (entities are named in topics)
        sql = f"""
            SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                   bm25(agent_memories_fts) AS score,
                   snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
            FROM agent_memories_fts
            JOIN agent_memories m ON m.id = agent_memories_fts.rowid
            WHERE agent_memories_fts MATCH ? {base_filter}
              AND lower(m.topic) LIKE lower(?)
            ORDER BY m.provenance_score DESC, score
            LIMIT ?;
        """
        rows = conn.execute(sql, (query, f"%{query.split()[0]}%", limit)).fetchall()
        if len(rows) < 2:
            rows = conn.execute(
                f"""SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                       bm25(agent_memories_fts) AS score,
                       snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
                    FROM agent_memories_fts
                    JOIN agent_memories m ON m.id = agent_memories_fts.rowid
                    WHERE agent_memories_fts MATCH ? {base_filter}
                    ORDER BY m.provenance_score DESC, score LIMIT ?;""",
                (query, limit),
            ).fetchall()

    elif query_type == "hybrid":
        # 2-stage search: Stage 1 = tags/context exact, Stage 2 = FTS5; merge + rank by provenance_score
        seen_ids = set()
        merged = []

        # Stage 1: tags/context match (high precision)
        stage1 = conn.execute(
            f"""
            SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                   0.0 AS score,
                   COALESCE(substr(m.body, 1, 120), '') AS body_snippet
            FROM agent_memories m
            WHERE (
                lower(COALESCE(m.tags, '')) LIKE lower(?)
                OR lower(COALESCE(m.context, '')) LIKE lower(?)
                OR lower(m.topic) LIKE lower(?)
            )
            {base_filter}
            ORDER BY m.provenance_score DESC
            LIMIT ?;
            """,
            (f"%{query.split()[0]}%", f"%{query}%", f"%{query.split()[0]}%", limit),
        ).fetchall()
        for r in stage1:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                merged.append(dict(r))

        # Stage 2: FTS5 full-text (high recall)
        stage2 = conn.execute(
            f"""
            SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                   bm25(agent_memories_fts) AS score,
                   snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
            FROM agent_memories_fts
            JOIN agent_memories m ON m.id = agent_memories_fts.rowid
            WHERE agent_memories_fts MATCH ?
              {base_filter}
            ORDER BY score
            LIMIT ?;
            """,
            (query, limit),
        ).fetchall()
        for r in stage2:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                merged.append(dict(r))

        # Rank merged by provenance_score DESC (proxy for quality; quality_score in separate DB)
        merged.sort(key=lambda x: x["provenance_score"], reverse=True)
        rows = merged[:limit]

    elif intent:
        rows = conn.execute(
            f"""
            SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                   bm25(agent_memories_fts) AS score,
                   snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
            FROM agent_memories_fts
            JOIN agent_memories m ON m.id = agent_memories_fts.rowid
            WHERE agent_memories_fts MATCH ?
              AND (
                lower(COALESCE(m.context, '')) LIKE lower(?)
                OR lower(COALESCE(m.tags, '')) LIKE lower(?)
              )
              {base_filter}
            ORDER BY score
            LIMIT ?;
            """,
            (query, f"%{intent}%", f"%{intent}%", limit),
        ).fetchall()
    else:
        # Default (factual): standard FTS5
        rows = conn.execute(
            f"""
            SELECT m.id, m.agent, m.cycle, m.topic, m.tags, m.context, m.memory_type, m.provenance_score, m.created_at,
                   bm25(agent_memories_fts) AS score,
                   snippet(agent_memories_fts, 0, '[', ']', '…', 12) AS body_snippet
            FROM agent_memories_fts
            JOIN agent_memories m ON m.id = agent_memories_fts.rowid
            WHERE agent_memories_fts MATCH ?
              {base_filter}
            ORDER BY score
            LIMIT ?;
            """,
            (query, limit),
        ).fetchall()

    conn.close()

    for r in rows:
        print(
            f"#{r['id']} score={r['score']:.3f} agent={r['agent']} cycle={r['cycle']} "
            f"topic={r['topic']} type={r['memory_type']} prov={r['provenance_score']:.2f} tags={r['tags']} at={r['created_at']}"
        )
        if r["context"]:
            print(f"  context: {r['context']}")
        print(f"  {r['body_snippet']}")

    return 0


def cmd_reflect(
    cfg: DbConfig,
    agent: str,
    cycle: str,
    outcome: str,
    quality_delta: float,
    proof: str | None = None,
) -> int:
    conn = connect(cfg.db_path)
    cur = conn.execute(
        """
        UPDATE agent_memories
        SET
          outcome = ?,
          use_count = COALESCE(use_count, 0) + 1,
          quality_score = MIN(1.0, MAX(0.0, COALESCE(quality_score, 0.5) + ?))
        WHERE agent = ? AND cycle = ?
        """,
        (outcome, quality_delta, agent, cycle),
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()

    if cfg.rsync and updated > 0:
        rsync_to_edrive(cfg.db_path, cfg.edrive_path)

    if proof:
        print(f"reflected={updated} proof={proof}")
    else:
        print(f"reflected={updated}")
    return 0


def cmd_gc(cfg: DbConfig) -> int:
    """Garbage-collect expired memories."""
    conn = connect(cfg.db_path)
    deleted = conn.execute(
        "DELETE FROM agent_memories WHERE expires_at IS NOT NULL AND expires_at < datetime('now')"
    ).rowcount
    conn.commit()
    remaining = conn.execute("SELECT COUNT(*) FROM agent_memories").fetchone()[0]
    conn.close()
    print(f"gc: deleted={deleted} remaining={remaining}")
    if cfg.rsync and deleted > 0:
        rsync_to_edrive(cfg.db_path, cfg.edrive_path)
    return 0


def cmd_skill(cfg: DbConfig, subcommand: str, args: argparse.Namespace) -> int:
    conn = connect(cfg.db_path)
    
    if subcommand == "add":
        try:
            conn.execute(
                "INSERT INTO skills(name, trigger, inputs, steps, outputs, agent_owner) VALUES (?,?,?,?,?,?)",
                (args.name, args.trigger, args.inputs, args.steps, args.outputs, args.agent_owner),
            )
            print(f"Added skill: {args.name}")
            conn.commit()
            if cfg.rsync:
                rsync_to_edrive(cfg.db_path, cfg.edrive_path)
        except sqlite3.IntegrityError:
            eprint(f"Skill '{args.name}' already exists.")
            return 1
    
    elif subcommand == "search":
        rows = conn.execute(
            """
            SELECT s.name, s.trigger, s.inputs, s.steps, s.outputs, s.use_count, s.agent_owner,
                   bm25(skills_fts) AS score
            FROM skills_fts
            JOIN skills s ON s.rowid = skills_fts.rowid
            WHERE skills_fts MATCH ?
            ORDER BY score
            LIMIT ?;
            """,
            (args.query, args.limit),
        ).fetchall()
        
        for r in rows:
            print(f"SKILL: {r['name']} (score={r['score']:.2f})")
            print(f"  Trigger: {r['trigger']}")
            print(f"  Steps: {r['steps']}")
            print(f"  Inputs: {r['inputs']} -> Outputs: {r['outputs']}")
            print(f"  Owner: {r['agent_owner']} | Used: {r['use_count']}")
            print()

    elif subcommand == "get":
        row = conn.execute("SELECT * FROM skills WHERE name=?", (args.name,)).fetchone()
        if not row:
            eprint("not_found")
            return 2
        print(f"SKILL: {row['name']}")
        print(f"  Trigger: {row['trigger']}")
        print(f"  Steps: {row['steps']}")
        print(f"  Inputs: {row['inputs']} -> Outputs: {row['outputs']}")
        print(f"  Owner: {row['agent_owner']} | Used: {row['use_count']}")

    conn.close()
    return 0


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Agent memory CLI (SQLite + FTS5, local-first + rsync backup)")
    p.add_argument("--db", default=str(DEFAULT_LOCAL_DB), help=f"SQLite path (default: {DEFAULT_LOCAL_DB})")
    p.add_argument(
        "--edrive-db",
        default=str(DEFAULT_EDRIVE_DB),
        help=f"Backup path for rsync (default: {DEFAULT_EDRIVE_DB})",
    )
    p.add_argument("--no-rsync", action="store_true", help="Disable rsync after writes")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create/open DB, ensure schema, enable WAL, bootstrap from EDrive if present")

    ps = sub.add_parser("store", help="Insert a memory row")
    ps.add_argument("--agent", required=True)
    ps.add_argument("--cycle", required=True)
    ps.add_argument("--topic", required=True)
    ps.add_argument("--body", required=True)
    ps.add_argument("--tags", default=None)
    ps.add_argument("--context", default=None)
    ps.add_argument(
        "--type",
        dest="memory_type",
        default="factual",
        choices=["factual", "experiential", "working", "procedural"],
        help="Memory type taxonomy (default: factual)",
    )
    ps.add_argument("--provenance-score", type=float, default=0.5, help="Confidence/provenance score in [0.0, 1.0]")
    ps.add_argument("--expires-at", default=None, help="Optional expiry timestamp (SQLite datetime format). If omitted and --type working, defaults to now+3h.")
    ps.add_argument("--source-file", default=None)

    pg = sub.add_parser("get", help="Get a memory row by id")
    pg.add_argument("id", type=int)

    pq = sub.add_parser("search", help="FTS5 search (MATCH query)")
    pq.add_argument("query")
    pq.add_argument("--limit", type=int, default=5)
    pq.add_argument("--intent", default=None, help="Optional intent filter applied to context/tags (case-insensitive substring)")
    pq.add_argument("--query-type", choices=["temporal", "causal", "entity", "factual", "hybrid"], default=None,
                    help="Optimised SQL dispatch: temporal=recent-first, causal=why/lesson, entity=topic, factual=FTS5, hybrid=2-stage tags+FTS5 ranked by provenance_score")

    pr = sub.add_parser("reflect", help="Apply hindsight reflection update to memories by agent+cycle")
    pr.add_argument("--agent", required=True)
    pr.add_argument("--cycle", required=True)
    pr.add_argument("--outcome", required=True, choices=["PASS", "FAIL"])
    pr.add_argument("--quality-delta", type=float, default=0.05, help="Delta added to quality_score (negative allowed)")
    pr.add_argument("--proof", default=None, help="Optional proof id (for logging only)")

    sub.add_parser("gc", help="Garbage-collect expired memories (working memories past TTL)")

    # Skills subcommand
    pskill = sub.add_parser("skill", help="Manage skills")
    skill_sub = pskill.add_subparsers(dest="skill_cmd", required=True)

    # skill add
    pskill_add = skill_sub.add_parser("add", help="Add a new skill")
    pskill_add.add_argument("name")
    pskill_add.add_argument("--trigger", required=True)
    pskill_add.add_argument("--inputs", required=True)
    pskill_add.add_argument("--steps", required=True)
    pskill_add.add_argument("--outputs", required=True)
    pskill_add.add_argument("--agent-owner", default="mack")

    # skill search
    pskill_search = skill_sub.add_parser("search", help="Search skills")
    pskill_search.add_argument("query")
    pskill_search.add_argument("--limit", type=int, default=5)

    # skill get
    pskill_get = skill_sub.add_parser("get", help="Get skill by name")
    pskill_get.add_argument("name")

    return p.parse_args(argv)


def main() -> int:
    ns = parse_args()
    cfg = DbConfig(
        db_path=Path(ns.db).expanduser(),
        edrive_path=Path(ns.edrive_db),
        rsync=(not ns.no_rsync),
    )

    if ns.cmd == "init":
        return cmd_init(cfg)
    if ns.cmd == "store":
        if not (0.0 <= ns.provenance_score <= 1.0):
            eprint("provenance_score must be between 0.0 and 1.0")
            return 2
        return cmd_store(
            cfg,
            ns.agent,
            ns.cycle,
            ns.topic,
            ns.body,
            ns.tags,
            ns.context,
            ns.memory_type,
            ns.provenance_score,
            ns.expires_at,
            ns.source_file,
        )
    if ns.cmd == "get":
        return cmd_get(cfg, ns.id)
    if ns.cmd == "search":
        return cmd_search(cfg, ns.query, ns.limit, ns.intent, getattr(ns, 'query_type', None))
    if ns.cmd == "reflect":
        return cmd_reflect(cfg, ns.agent, ns.cycle, ns.outcome, ns.quality_delta, ns.proof)
    if ns.cmd == "gc":
        return cmd_gc(cfg)
    if ns.cmd == "skill":
        return cmd_skill(cfg, ns.skill_cmd, ns)

    eprint("unknown_cmd")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
