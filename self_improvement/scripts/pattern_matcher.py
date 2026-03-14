#!/usr/bin/env python3
"""pattern_matcher.py — Find and classify code patterns in the workspace.

Built on top of code_search.py logic. Detects common structural patterns:
- Error handling (try/except, error callbacks)
- API calls (requests, urllib, curl subprocess)
- Database operations (sqlite3, SQL strings)
- File I/O (open, read, write, Path operations)
- Config loading (env vars, json config, argparse)
- Testing (assert, unittest, pytest)
- Logging (print to stderr, logging module)

Usage:
  python3 pattern_matcher.py --root /path/to/project
  python3 pattern_matcher.py --pattern error-handling --root .
  python3 pattern_matcher.py --json
  python3 pattern_matcher.py --summary
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
from collections import defaultdict
from pathlib import Path

PATTERNS: dict[str, list[re.Pattern]] = {
    "error-handling": [
        re.compile(r"\btry\s*:", re.IGNORECASE),
        re.compile(r"\bexcept\b.*:", re.IGNORECASE),
        re.compile(r"\braise\s+\w+", re.IGNORECASE),
    ],
    "api-call": [
        re.compile(r"\brequests\.(get|post|put|delete|patch)\b"),
        re.compile(r"\burllib\.request\b"),
        re.compile(r"\bcurl\s+(-[sS]|--)", re.IGNORECASE),
        re.compile(r"\bfetch\s*\("),
    ],
    "database": [
        re.compile(r"\bsqlite3\.connect\b"),
        re.compile(r"\bconn\.execute\b"),
        re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|ALTER|CREATE)\s+", re.IGNORECASE),
    ],
    "file-io": [
        re.compile(r"\bopen\s*\(.*['\"].*[rwa]"),
        re.compile(r"\.read_text\s*\("),
        re.compile(r"\.write_text\s*\("),
        re.compile(r"\bshutil\.(copy|move|rmtree)\b"),
    ],
    "config-loading": [
        re.compile(r"\bos\.environ\b"),
        re.compile(r"\bargparse\b"),
        re.compile(r"\bjson\.loads?\b.*read"),
        re.compile(r"\bload_dotenv\b"),
    ],
    "subprocess": [
        re.compile(r"\bsubprocess\.(run|Popen|call|check_output)\b"),
        re.compile(r"\bos\.system\s*\("),
    ],
    "logging": [
        re.compile(r"\bprint\s*\(.*file\s*=\s*sys\.stderr"),
        re.compile(r"\blogging\.(info|warning|error|debug|critical)\b"),
        re.compile(r"\beprint\s*\("),
    ],
}

DEFAULT_INCLUDES = ["*.py", "*.sh"]
DEFAULT_EXCLUDES = [".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", "archive"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Find and classify code patterns")
    p.add_argument("--root", default="/Users/harrisonfethe/.openclaw/workspace", help="Root directory")
    p.add_argument("--pattern", choices=list(PATTERNS.keys()), default=None, help="Filter to one pattern type")
    p.add_argument("--include", action="append", default=None, help="Glob include (repeatable)")
    p.add_argument("--exclude-dir", action="append", default=None, help="Dir names to skip")
    p.add_argument("--limit", type=int, default=200, help="Max matches per pattern")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--summary", action="store_true", help="Summary counts only")
    return p.parse_args()


def scan(root: Path, includes: list[str], excludes: list[str],
         patterns: dict[str, list[re.Pattern]], limit: int) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = defaultdict(list)

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(exc in path.parts for exc in excludes):
            continue
        if not any(fnmatch.fnmatch(path.name, pat) for pat in includes):
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rel = str(path.relative_to(root))

        for line_no, line in enumerate(text.splitlines(), 1):
            for pname, regexes in patterns.items():
                if len(results[pname]) >= limit:
                    continue
                for rx in regexes:
                    if rx.search(line):
                        results[pname].append({
                            "file": rel,
                            "line": line_no,
                            "text": line.strip()[:120],
                            "regex": rx.pattern[:40],
                        })
                        break  # one match per pattern per line

    return dict(results)


def main() -> int:
    ns = parse_args()
    root = Path(ns.root)
    includes = ns.include or DEFAULT_INCLUDES
    excludes = ns.exclude_dir or DEFAULT_EXCLUDES

    if ns.pattern:
        active = {ns.pattern: PATTERNS[ns.pattern]}
    else:
        active = PATTERNS

    results = scan(root, includes, excludes, active, ns.limit)

    if ns.json:
        summary = {k: {"count": len(v), "sample": v[:3]} for k, v in results.items()}
        print(json.dumps(summary, indent=2))
    elif ns.summary:
        total = 0
        for pname in sorted(results.keys()):
            count = len(results[pname])
            total += count
            files = len({m["file"] for m in results[pname]})
            print(f"  {pname:20s}: {count:4d} matches across {files:3d} files")
        print(f"  {'TOTAL':20s}: {total:4d}")
    else:
        for pname in sorted(results.keys()):
            matches = results[pname]
            if not matches:
                continue
            print(f"\n=== {pname} ({len(matches)} matches) ===")
            for m in matches[:20]:
                print(f"  {m['file']}:{m['line']}: {m['text']}")
            if len(matches) > 20:
                print(f"  ... and {len(matches) - 20} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
