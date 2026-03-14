#!/usr/bin/env python3
"""Proactive Blocker Detection & Delegation Script.

Scans TODO.md, LOOPS.md, and recent outputs for stalled items.
Outputs JSON with stalled_items array, recommended owners, and escalation flag.
Wire into hourly_self_reflect.py as a pre-improvement gate.
"""

import json, re, sys, os
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent  # workspace root
SI = BASE / "self_improvement"
STALE_HOURS = 6  # items older than this without update are flagged

def parse_todo_items(path):
    """Parse TODO.md for items with status and timestamps."""
    items = []
    if not path.exists():
        return items
    text = path.read_text()
    # Match lines like: - [ ] TASK_KEY: description (owner: X) [2026-02-22]
    # or: - [x] TASK_KEY: done
    # Also match BLOCKED, URGENT tags
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- ["):
            continue
        done = line.startswith("- [x]") or line.startswith("- [X]")
        if done:
            continue
        blocked = "BLOCKED" in line.upper()
        urgent = "URGENT" in line.upper()
        # Try to extract a date
        date_match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', line)
        # Try to extract owner
        owner_match = re.search(r'\(owner:\s*(\w+)\)', line, re.I)
        items.append({
            "line": line,
            "blocked": blocked,
            "urgent": urgent,
            "date": date_match.group(1) if date_match else None,
            "owner": owner_match.group(1) if owner_match else None,
        })
    return items

def check_stale_outputs(outputs_dir, hours=24):
    """Check for recent output files that contain FAIL or error indicators."""
    issues = []
    if not outputs_dir.exists():
        return issues
    cutoff = datetime.now() - timedelta(hours=hours)
    for f in sorted(outputs_dir.glob("*.md"), reverse=True)[:20]:
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                continue
            text = f.read_text()
            # Check for actual failures, not just section headers or "0 failed"
            # Look for patterns like "X failed" where X > 0, or "FAIL" in non-header context
            has_nonzero_fail = bool(re.search(r'[1-9]\d*\s+failed', text, re.I))
            has_fail_result = bool(re.search(r'\bFAIL\b(?!ed)', text))  # FAIL but not Failed
            has_fail_item = bool(re.search(r'^## Failed\n(?!\(none\)|\n|$).+', text, re.M))
            if has_nonzero_fail or has_fail_result or has_fail_item:
                issues.append({
                    "file": f.name,
                    "issue": "Contains failed improvements",
                    "mtime": mtime.isoformat(),
                })
        except (OSError, UnicodeDecodeError):
            pass
    return issues

def detect_blockers():
    now = datetime.now()
    stalled = []
    
    # 1. Scan TODO.md
    todo_path = SI / "TODO.md"
    for item in parse_todo_items(todo_path):
        reasons = []
        if item["blocked"] and not item["owner"]:
            reasons.append("BLOCKED without assigned owner")
        if item["date"]:
            try:
                item_date = datetime.strptime(item["date"], "%Y-%m-%d")
                age_hours = (now - item_date).total_seconds() / 3600
                if age_hours > STALE_HOURS:
                    reasons.append(f"Stale ({age_hours:.0f}h since last date)")
            except ValueError:
                pass
        if item["urgent"]:
            reasons.append("Marked URGENT")
        if reasons:
            stalled.append({
                "source": "TODO.md",
                "item": item["line"][:120],
                "reasons": reasons,
                "recommended_owner": item.get("owner") or "rosie",
            })

    # 2. Scan LOOPS.md for incomplete loops
    loops_path = SI / "LOOPS.md"
    if loops_path.exists():
        text = loops_path.read_text()
        # Look for loops marked as open/incomplete
        for match in re.finditer(r'(?:^|\n)#+\s+(.*?)\n(.*?)(?=\n#+|\Z)', text, re.S):
            header = match.group(1)
            body = match.group(2)
            if "OPEN" in body.upper() or "INCOMPLETE" in body.upper() or "STALLED" in body.upper():
                # Only flag if these appear as explicit status markers, not casual mentions
                status_pattern = re.compile(
                    r'(?:^|\n)\s*(?:[-*]?\s*)?(?:status|state|progress)\s*[:=]\s*(?:open|incomplete|stalled)',
                    re.I
                )
                has_stalled_marker = bool(re.search(r'\bSTALLED\b', body))
                if status_pattern.search(body) or has_stalled_marker:
                    stalled.append({
                    "source": "LOOPS.md",
                    "item": header[:120],
                    "reasons": ["Loop marked open/incomplete/stalled"],
                    "recommended_owner": "rosie",
                })

    # 3. Check recent outputs for failures
    for issue in check_stale_outputs(SI / "outputs"):
        stalled.append({
            "source": f"outputs/{issue['file']}",
            "item": issue["issue"],
            "reasons": ["Recent output has failures needing retry"],
            "recommended_owner": "mack",
        })

    escalation_needed = any(
        "URGENT" in " ".join(s.get("reasons", []))
        or "BLOCKED without" in " ".join(s.get("reasons", []))
        for s in stalled
    )

    result = {
        "timestamp": now.isoformat(),
        "stalled_items": stalled,
        "count": len(stalled),
        "escalation_needed": escalation_needed,
    }
    return result

if __name__ == "__main__":
    result = detect_blockers()
    print(json.dumps(result, indent=2))
    if result["escalation_needed"]:
        sys.exit(1)
    sys.exit(0)
