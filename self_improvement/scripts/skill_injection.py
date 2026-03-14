#!/usr/bin/env python3
"""
skill_injection.py — D-014: Skill Context Injector
Pre-fetches top-N skills by use_count for an agent and outputs a context block.

Usage:
  python3 skill_injection.py [agent_name] [--top N] [--format markdown|plain]

Output: skill context block suitable for prepending to cron prompts.
Agents should call this at the start of each cycle and inject the output.
"""

import json
import sqlite3
import sys
import os
from pathlib import Path
from typing import Optional

MEMU_DB = Path("/Users/harrisonfethe/.openclaw/workspace/memory/memu_store/memu.db")
SKILLS_DIR = Path("/opt/homebrew/lib/node_modules/openclaw/skills")

# Skills + their categories for warm-start before DB has use_count data
DEFAULT_SKILL_MAP = {
    "rosie":   ["code-search", "git-master", "doc-fetch", "github", "apple-notes"],
    "mack":    ["code-search", "git-master", "doc-fetch", "github", "coding-agent"],
    "winnie":  ["code-search", "doc-fetch", "github", "summarize", "gemini"],
    "lenny":   ["code-search", "healthcheck", "doc-fetch", "github", "git-master"],
    "default": ["code-search", "doc-fetch", "git-master", "github", "summarize"],
}


def get_top_skills_from_db(agent: str, top_n: int = 5):
    """Query memU DB for top skills by use_count for this agent.
    Returns list of (skill_name, quality_score, use_count).
    """
    if not MEMU_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(MEMU_DB), timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT key, COALESCE(quality_score, 0.5), COALESCE(use_count, 0)
            FROM memories
            WHERE agent_id = ?
              AND (category = 'skill' OR key LIKE '%skill%' OR key LIKE '%SKILL%')
            ORDER BY COALESCE(use_count, 0) DESC, COALESCE(quality_score, 0.5) DESC
            LIMIT ?
        """, (agent, top_n))
        rows = [(r[0], r[1], r[2]) for r in c.fetchall()]
        conn.close()
        return rows
    except (sqlite3.Error, OSError):
        return []


def get_skill_description(skill_name: str) -> Optional[str]:
    """Read the description from a skill's SKILL.md front matter."""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.exists():
        return None
    try:
        content = skill_file.read_text(encoding="utf-8")
        # Parse YAML front matter for description
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].splitlines():
                    if line.strip().startswith("description:"):
                        desc = line.split("description:", 1)[1].strip().strip('"\'')
                        return desc[:120]
    except (OSError, UnicodeDecodeError):
        pass
    return None


def list_available_skills():
    """List all installed skills."""
    if not SKILLS_DIR.exists():
        return []
    return [d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]


def build_context_block(agent: str, top_n: int = 5, fmt: str = "markdown") -> str:
    """Build the skill context block for injection."""
    # Try DB first
    db_skills = get_top_skills_from_db(agent, top_n)

    # Get installed skill names for matching
    available = set(list_available_skills())
    available_set = available

    skill_names = []
    if db_skills and any(uc > 0 for _, _, uc in db_skills):
        # DB has real use_count data — extract skill name from key
        # Keys look like: "eval-git-master-skill-<ts>" or "skill-code-search"
        seen = {}  # type: dict
        for key, _, uc in db_skills:
            # Try to match any installed skill name within the key
            for sname in available_set:
                if sname in key and sname not in seen:
                    seen[sname] = uc
        # Sort by use_count descending
        skill_names = [k for k, _ in sorted(seen.items(), key=lambda x: x[1], reverse=True)][:top_n]

    if not skill_names:
        # Fall back to agent default warm-start list
        agent_lower = agent.lower()
        skill_names = DEFAULT_SKILL_MAP.get(agent_lower, DEFAULT_SKILL_MAP["default"])[:top_n]

    # Filter to only installed skills
    skill_names = [s for s in skill_names if s in available]

    if not skill_names:
        return ""

    lines = []
    if fmt == "markdown":
        lines.append(f"## 🔧 Top Skills for {agent.title()} (use these tools):\n")
        for name in skill_names:
            desc = get_skill_description(name) or "See SKILL.md for details"
            skill_path = str(SKILLS_DIR / name / "SKILL.md")
            lines.append(f"- **{name}** — {desc}")
            lines.append(f"  Path: `{skill_path}`")
    else:
        lines.append(f"TOP SKILLS for {agent.upper()}:")
        for name in skill_names:
            desc = get_skill_description(name) or ""
            lines.append(f"  {name}: {desc}")

    return "\n".join(lines)


def record_skill_usage(agent: str, skill_name: str) -> None:
    """Increment use_count for a skill in memU DB."""
    if not MEMU_DB.exists():
        return
    try:
        conn = sqlite3.connect(str(MEMU_DB), timeout=5)
        c = conn.cursor()
        c.execute("""
            UPDATE memories
            SET use_count = COALESCE(use_count, 0) + 1
            WHERE agent_id = ? AND key LIKE ?
        """, (agent, f"%{skill_name}%"))
        conn.commit()
        conn.close()
    except (sqlite3.Error, OSError):
        pass


def main():
    args = sys.argv[1:]

    # Parse args
    agent = "default"
    top_n = 5
    fmt = "markdown"

    i = 0
    while i < len(args):
        if args[i] == "--top" and i + 1 < len(args):
            top_n = int(args[i + 1])
            i += 2
        elif args[i] == "--format" and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        elif args[i] == "--list":
            skills = list_available_skills()
            print(f"Installed skills ({len(skills)}):")
            for s in sorted(skills):
                desc = get_skill_description(s) or ""
                print(f"  {s}: {desc[:80]}")
            return
        elif not args[i].startswith("--"):
            agent = args[i]
            i += 1
        else:
            i += 1

    block = build_context_block(agent, top_n, fmt)
    if block:
        print(block)
    else:
        print(f"# No skills found for agent: {agent}")


if __name__ == "__main__":
    main()
