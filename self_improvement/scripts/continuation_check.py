#!/usr/bin/env python3
"""
continuation_check.py — Rosie's Continuation Enforcement Tool

Reads TODO.md and surfaces each agent's incomplete tasks grouped by priority.
Call this at the START of each agent cycle to enforce the "no skip" contract.

Usage:
    python3 continuation_check.py                    # All agents
    python3 continuation_check.py --agent rosie      # Rosie only
    python3 continuation_check.py --agent mack       # Mack only
    python3 continuation_check.py --agent winnie     # Winnie only
    python3 continuation_check.py --agent lenny      # Lenny only
    python3 continuation_check.py --agent all        # All agents (explicit)
    python3 continuation_check.py --urgent-only      # Only URGENT section tasks
    python3 continuation_check.py --json             # JSON output for machine parsing

Exit codes:
    0 = All tasks complete (no pending items for requested agent)
    1 = Pending URGENT tasks found
    2 = Pending non-urgent tasks found (no urgent)

Author: Rosie (Cycle #3, 2026-02-18 03:10 EST)
Patched: Winnie (Cycle #5, 2026-02-18 04:06 EST)
  - Bug fix: subsection headers (###/####) now inherit parent tier (fixes HIGH/MEDIUM tasks showing as OTHER)
  - Bug fix: [All] tagged tasks now visible in per-agent filter (not only --agent all)
"""

import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────

TODO_PATH = Path(__file__).parent.parent / "TODO.md"
AGENTS = ["rosie", "mack", "winnie", "lenny", "all"]

# Section priority tiers (matched by header keywords in TODO.md)
URGENT_HEADERS   = {"urgent", "urgent (do first)"}
HIGH_HEADERS     = {"high priority", "high priority (this week)"}
MEDIUM_HEADERS   = {"medium priority", "medium priority (next 2 weeks)"}
LOW_HEADERS      = {"low priority", "low priority (month 2+)"}
BLOCKER_HEADERS  = {"blockers"}
SKIP_HEADERS     = {"completed", "completed (archive weekly)", "discoveries",
                    "template", "blockers"}  # Don't scan these for tasks

# ── Parsers ──────────────────────────────────────────────────────────────────

def parse_todo(path: Path) -> dict:
    """
    Returns a dict structured as:
    {
      "URGENT": [{"agent": str, "text": str, "raw": str}, ...],
      "HIGH": [...],
      "MEDIUM": [...],
      "LOW": [...],
      "OTHER": [...],
    }
    Only incomplete tasks ([ ]) are returned.
    """
    sections: dict[str, list] = {
        "URGENT": [], "HIGH": [], "MEDIUM": [], "LOW": [], "OTHER": []
    }
    current_tier = "OTHER"

    if not path.exists():
        print(f"ERROR: TODO.md not found at {path}", file=sys.stderr)
        sys.exit(3)

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    for line in lines:
        # Detect section headers (## or ###)
        header_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if header_match:
            level = len(header_match.group(1))  # 1=#, 2=##, 3=###, 4=####
            header_text = header_match.group(2).lower().strip()
            # Strip markdown formatting
            header_clean = re.sub(r"[*_`]", "", header_text).strip()
            if any(h in header_clean for h in URGENT_HEADERS):
                current_tier = "URGENT"
            elif any(h in header_clean for h in HIGH_HEADERS):
                current_tier = "HIGH"
            elif any(h in header_clean for h in MEDIUM_HEADERS):
                current_tier = "MEDIUM"
            elif any(h in header_clean for h in LOW_HEADERS):
                current_tier = "LOW"
            elif any(h in header_clean for h in SKIP_HEADERS):
                current_tier = "SKIP"
            elif level <= 2:
                # Top-level sections (# or ##) without a tier keyword reset to OTHER.
                # Sub-sections (### or ####) inherit the parent tier so that tasks
                # under e.g. "### Skills to Build" (inside "## High Priority") are
                # correctly tagged HIGH rather than falling through to OTHER.
                current_tier = "OTHER"
            # else: sub-section (###/####) with no tier keyword → keep current_tier
            continue

        if current_tier == "SKIP":
            continue

        # Match incomplete task lines: - [ ] or * [ ]
        task_match = re.match(r"^\s*[-*]\s+\[ \]\s+(.+)$", line)
        if not task_match:
            continue

        task_text = task_match.group(1).strip()

        # Extract agent tag from **[AgentName]** pattern
        agent_match = re.match(r"\*\*\[(\w+)\]\*\*\s*(.+)", task_text)
        if agent_match:
            agent = agent_match.group(1).lower()
            description = agent_match.group(2).strip()
        else:
            agent = "unassigned"
            description = task_text

        # Strip trailing status markers
        description = re.sub(r"\s+✅.*$", "", description).strip()

        sections[current_tier].append({
            "agent": agent,
            "text": description,
            "raw": line.strip(),
        })

    return sections


def filter_by_agent(sections: dict, agent: str) -> dict:
    """Filter tasks to only those matching the requested agent (or 'all').

    Tasks tagged **[All]** are shared-responsibility and shown to every agent,
    not only when running --agent all.
    """
    if agent == "all":
        return sections
    filtered = {}
    for tier, tasks in sections.items():
        filtered[tier] = [t for t in tasks if t["agent"] == agent or t["agent"] == "all"]
    return filtered


def count_tasks(sections: dict) -> int:
    return sum(len(tasks) for tasks in sections.values())


# ── Formatters ───────────────────────────────────────────────────────────────

TIER_EMOJI = {
    "URGENT": "🔴",
    "HIGH":   "🟠",
    "MEDIUM": "🟡",
    "LOW":    "⚪",
    "OTHER":  "🔵",
}

def format_human(sections: dict, agent: str) -> str:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M %Z")
    label = agent.upper() if agent != "all" else "ALL AGENTS"
    lines.append(f"╔══ CONTINUATION CHECK — {label} — {now} ══╗")

    total = count_tasks(sections)
    if total == 0:
        lines.append("  ✅ No pending tasks found. Good work!")
        lines.append("╚" + "═" * 50 + "╝")
        return "\n".join(lines)

    urgent_count = len(sections.get("URGENT", []))
    if urgent_count > 0:
        lines.append(f"  ⚠️  {urgent_count} URGENT TASK(S) PENDING — address first!")

    lines.append(f"  📋 Total pending: {total}\n")

    tier_order = ["URGENT", "HIGH", "MEDIUM", "LOW", "OTHER"]
    for tier in tier_order:
        tasks = sections.get(tier, [])
        if not tasks:
            continue
        emoji = TIER_EMOJI.get(tier, "•")
        lines.append(f"  {emoji} {tier} ({len(tasks)} task{'s' if len(tasks)>1 else ''})")
        for t in tasks:
            owner = f"[{t['agent'].upper()}] " if agent == "all" else ""
            lines.append(f"    • {owner}{t['text']}")
        lines.append("")

    lines.append("╚" + "═" * 50 + "╝")
    return "\n".join(lines)


def format_json(sections: dict, agent: str) -> str:
    total = count_tasks(sections)
    urgent = len(sections.get("URGENT", []))
    return json.dumps({
        "agent": agent,
        "total_pending": total,
        "urgent_pending": urgent,
        "has_urgent": urgent > 0,
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "tasks": {tier: tasks for tier, tasks in sections.items() if tasks}
    }, indent=2)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Continuation enforcement — check pending TODO tasks for an agent."
    )
    parser.add_argument(
        "--agent", "-a",
        choices=AGENTS,
        default="all",
        help="Agent to check (rosie|mack|winnie|lenny|all). Default: all",
    )
    parser.add_argument(
        "--urgent-only", "-u",
        action="store_true",
        help="Only show URGENT section tasks",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_output",
        help="Output JSON instead of human-readable text",
    )
    parser.add_argument(
        "--todo-path",
        type=Path,
        default=TODO_PATH,
        help=f"Path to TODO.md (default: {TODO_PATH})",
    )
    args = parser.parse_args()

    # Parse
    all_sections = parse_todo(args.todo_path)

    # Filter by agent
    sections = filter_by_agent(all_sections, args.agent)

    # Optionally limit to URGENT
    if args.urgent_only:
        sections = {"URGENT": sections.get("URGENT", [])}

    # Output
    if args.json_output:
        print(format_json(sections, args.agent))
    else:
        print(format_human(sections, args.agent))

    # Exit codes
    total = count_tasks(sections)
    urgent = len(sections.get("URGENT", []))
    if total == 0:
        sys.exit(0)
    elif urgent > 0:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
