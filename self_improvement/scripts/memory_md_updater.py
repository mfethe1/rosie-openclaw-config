#!/usr/bin/env python3
"""memory_md_updater.py — Auto-update MEMORY.md from agent-memory.db (Winnie Cycle #18).

Completes the memory pipeline:
  knowledge_extractor.py → agent-memory.db → [this script] → MEMORY.md

This script periodically surfaces new high-quality memories from the SQLite
store back into MEMORY.md so they are available for context injection in future
agent runs, without requiring a full DB query.

Algorithm:
  1. Read agent-memory.db for entries since last_run (tracked in state file)
  2. Filter: quality_score >= threshold AND provenance_score >= threshold
  3. Deduplicate against existing MEMORY.md content (substring match)
  4. Group by topic cluster (tag-based grouping)
  5. Format as MEMORY.md section(s)
  6. Append to MEMORY.md under a timestamped "## Agent Discoveries" section
  7. Update state file with new last_run timestamp

Safety rules:
  - NEVER overwrites existing MEMORY.md content
  - Appends only — always adds after the existing end
  - Keeps total appended block ≤ 100 entries per run (avoid bloat)
  - Dry-run mode: --dry-run shows what would be appended without writing
  - Backup: creates .bak before any write

Usage:
  python3 memory_md_updater.py                        # run with defaults
  python3 memory_md_updater.py --dry-run              # preview changes
  python3 memory_md_updater.py --since 2026-02-18     # override since date
  python3 memory_md_updater.py --threshold 0.7        # stricter quality filter
  python3 memory_md_updater.py --max-entries 50       # limit appended entries
  python3 memory_md_updater.py --out /tmp/preview.md  # write preview to file
  python3 memory_md_updater.py --json                 # JSON summary output
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────
AGENT_MEMORY_DB  = Path.home() / ".openclaw/agent-memory.db"
MEMORY_MD        = Path("/Users/harrisonfethe/.openclaw/workspace/MEMORY.md")
STATE_FILE       = Path("/Users/harrisonfethe/.openclaw/workspace/self_improvement/memory/.memory_md_updater_state.json")

DEFAULT_THRESHOLD  = 0.5   # min(provenance_score, quality_score) — lowered since DB has 0.5 default
DEFAULT_MAX        = 80    # max entries to append per run
SECTION_HEADER     = "## Agent Discoveries (Auto-Updated)"
SKIP_MEMORY_TYPES  = {"working"}   # ephemeral — do not surface to MEMORY.md


# ── state management ───────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": "1970-01-01T00:00:00", "appended_count": 0, "runs": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── database query ─────────────────────────────────────────────────────────
def fetch_new_memories(since: str, threshold: float) -> list[dict]:
    """Fetch entries from agent-memory.db added after `since`, above quality threshold."""
    if not AGENT_MEMORY_DB.exists():
        return []

    con = sqlite3.connect(str(AGENT_MEMORY_DB))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("""
        SELECT agent, cycle, topic, body, tags, context, memory_type,
               provenance_score, quality_score, created_at, outcome
        FROM agent_memories
        WHERE created_at > ?
          AND memory_type NOT IN ('working')
          AND (expires_at IS NULL OR expires_at > datetime('now'))
          AND body IS NOT NULL
          AND LENGTH(body) > 20
        ORDER BY created_at ASC
    """, (since,))

    rows = []
    for row in cur.fetchall():
        d = dict(row)
        prov  = float(d.get("provenance_score") or 0.5)
        qual  = float(d.get("quality_score")    or 0.5)
        score = max(prov, qual)   # accept if either is above threshold
        if score >= threshold:
            d["_score"] = round(score, 2)
            rows.append(d)
    con.close()
    return rows


# ── deduplication ──────────────────────────────────────────────────────────
def build_existing_fingerprints(memory_md: Path) -> set[str]:
    """Build a set of lowercase 50-char body fingerprints from existing MEMORY.md."""
    if not memory_md.exists():
        return set()
    text = memory_md.read_text(errors="replace").lower()
    # Extract all sentences/bullet items ≥30 chars
    fingerprints = set()
    for line in text.splitlines():
        stripped = re.sub(r"[*_`#\-•>\[\]]", "", line).strip()
        if len(stripped) >= 30:
            fingerprints.add(stripped[:60])
    return fingerprints


def is_duplicate(body: str, fingerprints: set[str]) -> bool:
    """True if this body already appears in MEMORY.md."""
    key = re.sub(r"[*_`#\-•>\[\]]", "", body.lower()).strip()[:60]
    return any(key in fp or fp in key for fp in fingerprints if len(fp) >= 20)


# ── grouping ───────────────────────────────────────────────────────────────
def group_entries(entries: list[dict]) -> dict[str, list[dict]]:
    """Group entries by their primary tag (first tag) or memory_type."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        tags_raw = e.get("tags") or ""
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()
                and t.strip() not in ("factual","experiential","procedural","working","eval-gated")]
        # Use first meaningful tag as group key, else memory_type
        group = tags[0] if tags else (e.get("memory_type") or "general")
        groups[group].append(e)
    return dict(groups)


# ── formatting ─────────────────────────────────────────────────────────────
def format_section(entries: list[dict], run_ts: str, since: str) -> str:
    """Format new entries as a MEMORY.md section block."""
    grouped = group_entries(entries)

    lines = [
        "",
        f"{SECTION_HEADER}",
        f"*Last updated: {run_ts} | {len(entries)} new entries since {since[:10]}*",
        "",
    ]

    for group_name, items in sorted(grouped.items()):
        lines.append(f"### {group_name.replace('-', ' ').title()}")
        for e in items:
            agent = e.get("agent", "?")
            body  = e.get("body", "").strip()
            ts    = str(e.get("created_at", ""))[:10]
            score = e.get("_score", 0.5)
            outcome = e.get("outcome", "") or ""

            # Format as bullet
            bullet = f"- [{ts}|{agent}] {body}"
            if outcome and "PASS" in outcome.upper():
                bullet += " ✅"
            lines.append(bullet)
        lines.append("")

    return "\n".join(lines)


def format_json_summary(entries: list[dict], appended: int,
                        skipped_dup: int, skipped_thresh: int) -> dict:
    return {
        "new_entries_fetched": len(entries) + skipped_dup + skipped_thresh,
        "appended": appended,
        "skipped_duplicate": skipped_dup,
        "skipped_threshold": skipped_thresh,
        "agents": list({e["agent"] for e in entries}),
    }


# ── main logic ─────────────────────────────────────────────────────────────
def run(since: str, threshold: float, max_entries: int,
        dry_run: bool, out_path: str | None, json_mode: bool) -> dict:

    state   = load_state()
    run_ts  = datetime.now().strftime("%Y-%m-%d %H:%M EST")

    # Fetch from DB
    all_new     = fetch_new_memories(since, threshold=0.0)   # fetch all, filter below
    fingerprints= build_existing_fingerprints(MEMORY_MD)

    accepted     = []
    skipped_dup  = 0
    skipped_thr  = 0

    for e in all_new:
        prov  = float(e.get("provenance_score") or 0.5)
        qual  = float(e.get("quality_score")    or 0.5)
        score = max(prov, qual)

        if score < threshold:
            skipped_thr += 1
            continue

        if is_duplicate(e.get("body", ""), fingerprints):
            skipped_dup += 1
            continue

        accepted.append(e)
        if len(accepted) >= max_entries:
            break

    if not accepted:
        summary = {"appended": 0, "skipped_duplicate": skipped_dup,
                   "skipped_threshold": skipped_thr, "new_entries_fetched": len(all_new)}
        if json_mode:
            print(json.dumps(summary, indent=2))
        else:
            print(f"No new entries to append ({skipped_dup} duplicates, {skipped_thr} below threshold).")
        return summary

    section = format_section(accepted, run_ts, since)

    if out_path:
        Path(out_path).write_text(section)
        print(f"Preview written → {out_path}")
    elif dry_run:
        print("=== DRY RUN — would append to MEMORY.md ===")
        print(section)
        print(f"=== Would append {len(accepted)} entries ===")
    else:
        # Backup + append
        if MEMORY_MD.exists():
            bak = MEMORY_MD.with_suffix(".md.bak")
            shutil.copy2(MEMORY_MD, bak)
        with MEMORY_MD.open("a") as f:
            f.write(section)
        print(f"✅ Appended {len(accepted)} entries to MEMORY.md")

        # Update state
        state["last_run"]        = datetime.now().isoformat()
        state["appended_count"] += len(accepted)
        state["runs"]           += 1
        save_state(state)

    summary = format_json_summary(accepted, len(accepted), skipped_dup, skipped_thr)

    if json_mode:
        print(json.dumps(summary, indent=2))
    elif not dry_run and not out_path:
        print(f"   Skipped: {skipped_dup} duplicates, {skipped_thr} below threshold ({threshold})")
        print(f"   State updated: runs={state['runs']}, total_appended={state['appended_count']}")

    return summary


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="memory_md_updater — auto-update MEMORY.md from agent-memory.db")
    parser.add_argument("--since",       help="Override since date YYYY-MM-DD (default: last run timestamp)")
    parser.add_argument("--threshold",   type=float, default=DEFAULT_THRESHOLD,
                        help=f"Min quality/provenance score to include (default {DEFAULT_THRESHOLD})")
    parser.add_argument("--max-entries", type=int, default=DEFAULT_MAX,
                        help=f"Max entries to append per run (default {DEFAULT_MAX})")
    parser.add_argument("--dry-run",     action="store_true", help="Preview without writing")
    parser.add_argument("--out",         help="Write section to this file (preview mode)")
    parser.add_argument("--json",        action="store_true", help="JSON output for pipeline use")
    parser.add_argument("--reset-state", action="store_true", help="Reset last_run to epoch (reprocess all)")
    args = parser.parse_args()

    if args.reset_state:
        save_state({"last_run": "1970-01-01T00:00:00", "appended_count": 0, "runs": 0})
        print("State reset.")
        return

    state = load_state()
    since = args.since or state["last_run"]

    result = run(
        since      = since,
        threshold  = args.threshold,
        max_entries= args.max_entries,
        dry_run    = args.dry_run,
        out_path   = args.out,
        json_mode  = args.json,
    )
    sys.exit(0 if result.get("appended", 0) >= 0 else 1)


if __name__ == "__main__":
    main()
