#!/usr/bin/env python3
"""lenny_lesson_encoder.py

Verify that recent `lesson_captured` entries are represented in executable code.
This replaces a previously corrupted file that had multiple concatenated script bodies.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
REFLECTION_CANDIDATES = [
    WORKSPACE / "self_improvement" / "reflections",
    WORKSPACE / "self_improvement" / "outputs",
    WORKSPACE / "reflections",
]
SCRIPT_DIR = WORKSPACE / "self_improvement" / "scripts"
AGENT_FILES = [
    WORKSPACE / "agents" / "lenny.md",
    WORKSPACE / "agents" / "mack.md",
]

MIN_LESSON_CHARS = 12
MAX_RECENT = 5


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _extract_lessons_from_json(path: Path) -> list[str]:
    lessons: list[str] = []
    try:
        data = json.loads(_safe_read_text(path))
    except (json.JSONDecodeError, TypeError, ValueError):
        return lessons

    lesson = data.get("lesson_captured") if isinstance(data, dict) else None
    if isinstance(lesson, str) and len(lesson.strip()) >= MIN_LESSON_CHARS:
        lessons.append(lesson.strip())
    return lessons


def _extract_lessons_from_text(path: Path) -> list[str]:
    lessons: list[str] = []
    text = _safe_read_text(path)
    if not text:
        return lessons

    # Handles JSON-ish lines and markdown bullets.
    patterns = [
        re.compile(r"lesson_captured[\"']?\s*[:=]\s*[\"']([^\"'\n]+)", re.IGNORECASE),
        re.compile(r"(?:^|\n)\s*(?:[-*]|\d+[.)])?\s*Lesson\s*:\s*(.+)$", re.IGNORECASE),
    ]

    for pattern in patterns:
        for match in pattern.finditer(text):
            lesson = match.group(1).strip()
            if len(lesson) >= MIN_LESSON_CHARS:
                lessons.append(lesson)
    return lessons


def collect_recent_lessons(limit: int = MAX_RECENT) -> list[str]:
    files: list[Path] = []
    for directory in REFLECTION_CANDIDATES:
        if directory.exists():
            files.extend([p for p in directory.glob("*.json")])
            files.extend([p for p in directory.glob("*.md")])

    files = sorted(set(files), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    lessons: list[str] = []
    seen: set[str] = set()
    for path in files:
        extracted = _extract_lessons_from_json(path) if path.suffix == ".json" else _extract_lessons_from_text(path)
        for lesson in extracted:
            key = lesson.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            lessons.append(lesson)
            if len(lessons) >= limit:
                return lessons
    return lessons


def _lesson_keywords(lesson: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]{4,}", lesson.lower())
    stopwords = {
        "that",
        "this",
        "with",
        "from",
        "into",
        "when",
        "then",
        "must",
        "should",
        "have",
        "been",
        "only",
        "not",
        "code",
        "lesson",
    }
    return [t for t in tokens if t not in stopwords][:5]


def verify_encoding(lessons: list[str]) -> tuple[bool, list[str]]:
    corpus_parts = []
    for py in SCRIPT_DIR.glob("*.py"):
        corpus_parts.append(_safe_read_text(py))
    for agent in AGENT_FILES:
        if agent.exists():
            corpus_parts.append(_safe_read_text(agent))

    corpus = "\n".join(corpus_parts).lower()
    failures: list[str] = []

    for lesson in lessons:
        keywords = _lesson_keywords(lesson)
        if not keywords:
            continue
        hits = sum(1 for kw in keywords if kw in corpus)
        if hits == 0:
            failures.append(lesson)
    return (len(failures) == 0, failures)


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: lenny_lesson_encoder.py [--verify] [--json]")
        return 0

    lessons = collect_recent_lessons()
    if not lessons:
        print("OK: No lessons found to verify.")
        return 0

    ok, failed = verify_encoding(lessons)
    if "--json" in sys.argv:
        payload = {
            "lessons_checked": len(lessons),
            "ok": ok,
            "failed": failed,
        }
        print(json.dumps(payload, indent=2))
    elif ok:
        print(f"OK: All {len(lessons)} recent lessons show code/profile keyword coverage.")
    else:
        print(f"FAIL: {len(failed)} lessons appear unencoded:")
        for item in failed:
            print(f"  - {item}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
