#!/usr/bin/env python3
"""code_search.py

Fast codebase grep wrapper for Self-Improvement tasks.

Usage:
  python3 code_search.py "memu" \
    --root /Users/harrisonfethe/.openclaw/workspace \
    --include "*.py" --limit 50
"""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fast code search wrapper")
    p.add_argument("query", help="Substring query (case-insensitive by default)")
    p.add_argument("--root", default="/Users/harrisonfethe/.openclaw/workspace", help="Root directory to scan")
    p.add_argument("--include", action="append", default=["*.py", "*.sh", "*.md", "*.json"], help="Glob include pattern (repeatable)")
    p.add_argument("--exclude-dir", action="append", default=[".git", "node_modules", "venv", ".venv", "dist", "build"], help="Directory names to skip")
    p.add_argument("--case-sensitive", action="store_true", help="Enable case-sensitive matching")
    p.add_argument("--limit", type=int, default=100, help="Maximum number of matches to print")
    return p.parse_args()


def allowed_file(path: Path, includes: list[str]) -> bool:
    return any(fnmatch.fnmatch(path.name, pat) for pat in includes)


def run_search(ns: argparse.Namespace) -> int:
    root = Path(ns.root)
    if not root.exists():
        print(f"ERROR: root not found: {root}")
        return 2

    query = ns.query if ns.case_sensitive else ns.query.lower()
    hits = 0

    for p in root.rglob("*"):
        if p.is_dir() and p.name in ns.exclude_dir:
            # skip recursion into excluded directories
            continue
        if not p.is_file() or not allowed_file(p, ns.include):
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for i, line in enumerate(text.splitlines(), 1):
            candidate = line if ns.case_sensitive else line.lower()
            if query in candidate:
                rel = p.relative_to(root)
                print(f"{rel}:{i}: {line.strip()}")
                hits += 1
                if hits >= ns.limit:
                    print(f"-- limit reached ({ns.limit}) --")
                    return 0

    print(f"-- done: {hits} match(es) --")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_search(parse_args()))
