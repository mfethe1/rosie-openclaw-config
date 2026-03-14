#!/usr/bin/env python3
"""awesome_memory_tracker.py — Track Awesome-Memory-for-Agents monthly updates.

Purpose:
- Replaces manual scan task by creating a local snapshot + diff report.
- Fetches the upstream paper list README and extracts paper titles.
- Compares against previous snapshot and reports newly added papers.

Usage:
  python3 awesome_memory_tracker.py
  python3 awesome_memory_tracker.py --out /tmp/awesome-memory-report.md
  python3 awesome_memory_tracker.py --json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request

URL = "https://raw.githubusercontent.com/Shichun-Liu/Agent-Memory-Paper-List/main/README.md"
STATE_PATH = Path("/Users/harrisonfethe/.openclaw/workspace/self_improvement/memory/awesome_memory_tracker_state.json")


def fetch_readme() -> str:
    req = Request(URL, headers={"User-Agent": "openclaw-awesome-memory-tracker/1.0"})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_papers(md: str) -> list[str]:
    # Match bullets like: [2026/01] MAGMA: ... [paper]
    papers = []
    for line in md.splitlines():
        line = line.strip()
        m = re.match(r"^-\s*\[(\d{4}/\d{2})\]\s*(.+?)\s*\[paper\]", line)
        if m:
            title = m.group(2).strip()
            # Clean markdown residue from some lines
            title = re.sub(r"\s*\[\s*$", "", title).strip()
            papers.append(title)
    # Dedup preserving order
    seen = set()
    out = []
    for p in papers:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def normalize_title(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s*\[\s*$", "", s).strip()
    return s


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            st = json.loads(STATE_PATH.read_text())
            st["papers"] = [normalize_title(x) for x in st.get("papers", [])]
            return st
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    return {"last_checked": None, "papers": []}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def build_report(added: list[str], total: int, prev_total: int) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M EST")
    lines = [
        f"# Awesome-Memory Tracker Report",
        f"**Generated:** {ts}",
        f"**Source:** {URL}",
        "",
        f"- Previous papers tracked: {prev_total}",
        f"- Current papers tracked: {total}",
        f"- Newly detected: {len(added)}",
        "",
    ]
    if added:
        lines.append("## New Papers Since Last Check")
        for p in added[:25]:
            lines.append(f"- {p}")
    else:
        lines.append("## No New Papers Detected")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    md = fetch_readme()
    papers = [normalize_title(p) for p in extract_papers(md)]
    state = load_state()
    prev = [normalize_title(p) for p in state.get("papers", [])]
    added = [p for p in papers if p not in prev]

    new_state = {
        "last_checked": datetime.now().isoformat(),
        "source": URL,
        "papers": papers,
        "count": len(papers),
    }
    save_state(new_state)

    report = build_report(added, len(papers), len(prev))

    if args.out:
        Path(args.out).write_text(report)
        print(f"Report written → {args.out}")

    if args.json:
        print(json.dumps({
            "previous": len(prev),
            "current": len(papers),
            "new": len(added),
            "added": added[:50],
            "state": str(STATE_PATH),
        }, indent=2))
    else:
        print(report)


if __name__ == "__main__":
    main()
