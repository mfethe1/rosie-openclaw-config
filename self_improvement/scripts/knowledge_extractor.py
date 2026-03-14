#!/usr/bin/env python3
"""knowledge_extractor.py — ProMem-style proactive memory extraction (D-017).

Pattern:
  1. Initial Extract — scan recent agent outputs, pull candidate facts/decisions
  2. Self-Question Verify — verify each candidate appears in source
  3. Store — write verified items to agent-memory.db via agent_memory_cli.py

Usage:
  python3 knowledge_extractor.py [--outputs-dir DIR] [--last N] [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
CLI = Path(__file__).parent / "agent_memory_cli.py"
PYTHON = sys.executable

# Patterns that signal an extractable fact/decision
EXTRACT_PATTERNS = [
    re.compile(r"(?i)(DECISION|ADOPT|SKIP|RESOLVED|DONE|→|✅|⚠️|🔴|🟠).*:.+"),
    re.compile(r"^\s*[-*]\s+\*\*[^*]+\*\*.*:\s*.{20,}", re.MULTILINE),
    re.compile(r"(?i)(implemented|shipped|fixed|added|created|deployed)\s+.{15,}"),
    re.compile(r"(?i)(key (lesson|finding|constraint|rule|note)|critical|important):\s*.+"),
]

MIN_LENGTH = 30
MAX_LENGTH = 400


def extract_candidates(text: str, source_file: str) -> list[dict]:
    """Pass 1: extract candidate facts from text."""
    candidates = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if len(line) < MIN_LENGTH or len(line) > MAX_LENGTH:
            continue
        for pat in EXTRACT_PATTERNS:
            if pat.search(line):
                key = line[:80].lower()
                if key not in seen:
                    seen.add(key)
                    # Derive a short topic from first meaningful words
                    topic = re.sub(r"[*_`#\[\]→✅⚠️🔴🟠]", "", line)[:60].strip(" :-")
                    candidates.append({"body": line, "topic": topic, "source": source_file})
                break
    return candidates


def verify_candidate(candidate: dict, source_text: str) -> bool:
    """Pass 2: verify the candidate body appears meaningfully in the source."""
    body = candidate["body"]
    # Simple heuristic: at least 60% of significant words must appear in source
    words = [w for w in re.split(r"\W+", body.lower()) if len(w) > 3]
    if not words:
        return False
    matches = sum(1 for w in words if w in source_text.lower())
    return matches / len(words) >= 0.6


def store_fact(candidate: dict, agent: str = "rosie", cycle: str = "") -> bool:
    """Store a verified fact via agent_memory_cli.py."""
    cmd = [
        PYTHON, str(CLI), "store",
        "--agent", agent,
        "--cycle", cycle,
        "--topic", candidate["topic"][:100],
        "--body", candidate["body"][:400],
        "--tags", "promem,auto-extract",
        "--type", "factual",
        "--context", f"auto-extracted from {candidate['source']}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def process_file(path: Path, dry_run: bool = False) -> list[dict]:
    """Extract, verify, and optionally store facts from one output file."""
    text = path.read_text(errors="replace")
    candidates = extract_candidates(text, path.name)
    verified = [c for c in candidates if verify_candidate(c, text)]

    if not dry_run:
        cycle = path.stem  # e.g. 2026-02-19-08-mack
        for c in verified:
            store_fact(c, agent="rosie", cycle=cycle)

    return verified


def main():
    parser = argparse.ArgumentParser(description="ProMem knowledge extractor")
    parser.add_argument("--outputs-dir", default=str(OUTPUTS_DIR))
    parser.add_argument("--last", type=int, default=5, help="Number of recent files to scan")
    parser.add_argument("--dry-run", action="store_true", help="Extract but do not store")
    args = parser.parse_args()

    outputs_dir = Path(args.outputs_dir)
    # Only scan dated agent output files (YYYY-MM-DD-HH-agent.md pattern)
    agent_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\w+\.md$")
    files = sorted(f for f in outputs_dir.glob("*.md") if agent_pattern.match(f.name))[-args.last:]

    if not files:
        print("No output files found.")
        sys.exit(0)

    all_verified: list[dict] = []
    report_lines = [
        f"# ProMem Knowledge Extraction Report",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} EST_",
        f"_Scanned: {len(files)} files | Dry-run: {args.dry_run}_",
        "",
    ]

    for f in files:
        verified = process_file(f, dry_run=args.dry_run)
        all_verified.extend(verified)
        if verified:
            report_lines.append(f"## {f.name} ({len(verified)} facts)")
            for item in verified:
                report_lines.append(f"- **{item['topic'][:60]}**")
                report_lines.append(f"  > {item['body'][:200]}")
            report_lines.append("")

    report_lines += [
        "---",
        f"**Total extracted & {'stored' if not args.dry_run else 'found (dry-run)'}: {len(all_verified)}**",
    ]

    # Write output
    ts = datetime.now().strftime("%Y-%m-%d-%H")
    out_path = outputs_dir / f"{ts}-mack-promem.md"
    out_path.write_text("\n".join(report_lines))
    print(f"Report written: {out_path}")
    print(f"Total facts {'stored' if not args.dry_run else 'found'}: {len(all_verified)}")


if __name__ == "__main__":
    main()
