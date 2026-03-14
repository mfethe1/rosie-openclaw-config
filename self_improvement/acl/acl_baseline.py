#!/usr/bin/env python3
"""
acl_baseline.py — Phase 0: Measure baseline response times.

Scans recent OpenClaw session logs to extract response latency
for Michael's top request categories. Outputs acl_baseline.json.

Categories: status, build, fix, revenue, research, coordination, review
"""

import json
import os
import glob
import re
from datetime import datetime, timedelta

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
OUTPUT = os.path.join(WORKSPACE, "self_improvement", "acl", "acl_baseline.json")
LOG_DIR = os.path.expanduser("~/.openclaw/logs")

# Category keywords for rough classification
CATEGORY_PATTERNS = {
    "status": r"(status|health|what.?s (going on|happening|broken|running)|cron|uptime|check)",
    "build": r"(build|create|implement|add|make|ship|develop|write|code)",
    "fix": r"(fix|bug|error|broken|failing|crash|issue|debug|repair)",
    "revenue": r"(revenue|sales|outreach|customer|deal|pricing|money|invoice)",
    "research": r"(research|investigate|find|look into|compare|evaluate|assess|analyze)",
    "coordination": r"(where are we|update|progress|team|assign|delegate|who)",
    "review": r"(review|pr|pull request|check (this|my)|look at|feedback|approve)",
}


def classify_message(text: str) -> str:
    """Classify a message into a category based on keywords."""
    text_lower = text.lower()
    scores = {}
    for cat, pattern in CATEGORY_PATTERNS.items():
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            scores[cat] = matches
    if scores:
        return max(scores, key=scores.get)
    return "other"


def scan_session_logs():
    """Scan session log files for message/response pairs with timing."""
    results = []
    
    # Check for session log files
    log_patterns = [
        os.path.join(LOG_DIR, "**", "*.jsonl"),
        os.path.join(LOG_DIR, "**", "*.json"),
        os.path.join(LOG_DIR, "*.jsonl"),
    ]
    
    log_files = []
    for pattern in log_patterns:
        log_files.extend(glob.glob(pattern, recursive=True))
    
    if not log_files:
        print(f"No log files found in {LOG_DIR}")
        return results
    
    for log_file in log_files[:50]:  # limit scan
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if isinstance(entry, dict) and entry.get("role") == "user":
                        content = entry.get("content", "")
                        if isinstance(content, list):
                            content = " ".join(
                                item.get("text", "") for item in content 
                                if isinstance(item, dict)
                            )
                        if content:
                            cat = classify_message(content)
                            results.append({
                                "category": cat,
                                "timestamp": entry.get("timestamp", ""),
                                "file": os.path.basename(log_file),
                            })
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception:
            continue
    
    return results


def build_baseline():
    """Build baseline measurements."""
    print("📏 ACL Phase 0: Building baseline measurements...")
    
    entries = scan_session_logs()
    
    # Count by category
    category_counts = {}
    for entry in entries:
        cat = entry["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Build baseline structure
    baseline = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "phase": 0,
        "measurement_method": "session_log_scan",
        "total_messages_scanned": len(entries),
        "category_distribution": category_counts,
        "top_5_categories": sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True
        )[:5],
        "estimated_response_times": {
            "status": {"avg_ms": None, "note": "To be measured during Phase 0 active monitoring"},
            "build": {"avg_ms": None, "note": "To be measured during Phase 0 active monitoring"},
            "fix": {"avg_ms": None, "note": "To be measured during Phase 0 active monitoring"},
            "coordination": {"avg_ms": None, "note": "To be measured during Phase 0 active monitoring"},
            "research": {"avg_ms": None, "note": "To be measured during Phase 0 active monitoring"},
            "review": {"avg_ms": None, "note": "To be measured during Phase 0 active monitoring"},
            "revenue": {"avg_ms": None, "note": "To be measured during Phase 0 active monitoring"},
        },
        "phase_0_deadline": (datetime.now() + timedelta(hours=72)).isoformat(),
        "gate_status": "IN_PROGRESS",
        "notes": [
            "Category distribution establishes which request types to prioritize",
            "Response times will be measured via request_logger.py instrumentation",
            "Phase 1 gate: this file must have avg_ms values for top-5 categories",
        ],
    }
    
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"✅ Baseline written to {OUTPUT}")
    print(f"   Total messages scanned: {len(entries)}")
    print(f"   Category distribution: {json.dumps(category_counts, indent=2)}")
    print(f"   Top 5: {baseline['top_5_categories']}")
    print(f"   Phase 0 deadline: {baseline['phase_0_deadline']}")
    
    return baseline


if __name__ == "__main__":
    build_baseline()
