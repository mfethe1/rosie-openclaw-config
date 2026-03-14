#!/usr/bin/env python3
"""
request_logger.py — ACL Phase 1: SQLite post-message hook logger.

Logs every Michael request with category, timing, and cache-hit status.
WAL mode enabled. 7-day rolling window with auto-prune.

Usage:
    from request_logger import log_request, get_stats
    log_request("status", response_time_ms=3200, used_cache=True)
    stats = get_stats()
"""

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta

ACL_DIR = os.path.expanduser("~/.openclaw/workspace/.acl")
DB_PATH = os.path.join(ACL_DIR, "request_log.db")
RETENTION_DAYS = 7

CATEGORY_PATTERNS = {
    "status": r"(status|health|what.?s (going on|happening|broken|running)|cron|uptime)",
    "build": r"(build|create|implement|add|make|ship|develop|write|code|set up|setup)",
    "fix": r"(fix|bug|error|broken|failing|crash|issue|debug|repair)",
    "revenue": r"(revenue|sales|outreach|customer|deal|pricing|money|invoice)",
    "research": r"(research|investigate|find|look into|compare|evaluate|assess|analyze|where are we)",
    "coordination": r"(update|progress|team|assign|delegate|who|all.+agents)",
    "review": r"(review|pr|pull request|check.+(this|my)|look at|feedback|approve)",
    "self_improvement": r"(self.?improv|predict|anticipat|inferr|refine|deliberat|optimize)",
}


def _get_db() -> sqlite3.Connection:
    """Get SQLite connection with WAL mode."""
    os.makedirs(ACL_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS request_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            time_of_day TEXT,
            day_of_week TEXT,
            context_json TEXT,
            response_time_ms INTEGER,
            used_cached_context BOOLEAN DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_request_log_timestamp 
        ON request_log(timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_request_log_category 
        ON request_log(category)
    """)
    conn.commit()
    return conn


def _time_of_day(hour: int) -> str:
    """Classify hour into time-of-day bucket."""
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 22:
        return "evening"
    return "night"


def classify_message(text: str) -> str:
    """Classify a message into a category."""
    # Strip Telegram metadata if present
    parts = text.split("@RosieFetheBot")
    if len(parts) > 1:
        text = parts[-1]
    idx = text.rfind("```\n\n")
    if idx > 0:
        text = text[idx + 5:]

    text_lower = text.lower()[:500]
    scores = {}
    for cat, pattern in CATEGORY_PATTERNS.items():
        matches = len(re.findall(pattern, text_lower))
        if matches > 0:
            scores[cat] = matches
    return max(scores, key=scores.get) if scores else "other"


def log_request(
    category: str,
    response_time_ms: int = 0,
    used_cache: bool = False,
    context: dict = None,
):
    """Log a request to SQLite. Auto-prunes old entries."""
    now = datetime.now()
    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO request_log 
               (timestamp, category, time_of_day, day_of_week, context_json, 
                response_time_ms, used_cached_context)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                now.isoformat(),
                category,
                _time_of_day(now.hour),
                now.strftime("%A"),
                json.dumps(context) if context else None,
                response_time_ms,
                1 if used_cache else 0,
            ),
        )
        # Auto-prune: delete rows older than RETENTION_DAYS
        cutoff = (now - timedelta(days=RETENTION_DAYS)).isoformat()
        conn.execute("DELETE FROM request_log WHERE timestamp < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()


def get_stats() -> dict:
    """Get current ACL statistics."""
    conn = _get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM request_log").fetchone()[0]
        cache_hits = conn.execute(
            "SELECT COUNT(*) FROM request_log WHERE used_cached_context = 1"
        ).fetchone()[0]
        
        categories = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM request_log GROUP BY category ORDER BY cnt DESC"
        ).fetchall()

        avg_response = conn.execute(
            "SELECT category, AVG(response_time_ms) FROM request_log "
            "WHERE response_time_ms > 0 GROUP BY category"
        ).fetchall()

        oldest = conn.execute(
            "SELECT MIN(timestamp) FROM request_log"
        ).fetchone()[0]

        return {
            "total_requests": total,
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hits / total * 100, 1) if total > 0 else 0,
            "categories": {cat: cnt for cat, cnt in categories},
            "avg_response_ms": {cat: round(avg, 1) for cat, avg in avg_response},
            "oldest_entry": oldest,
            "retention_days": RETENTION_DAYS,
            "db_path": DB_PATH,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if "--stats" in sys.argv:
        stats = get_stats()
        print(json.dumps(stats, indent=2))
    elif "--log-test" in sys.argv:
        log_request("status", response_time_ms=3200, used_cache=False)
        log_request("build", response_time_ms=12000, used_cache=True)
        log_request("review", response_time_ms=8500, used_cache=True)
        print("Logged 3 test entries")
        print(json.dumps(get_stats(), indent=2))
    else:
        print("Usage: request_logger.py [--stats|--log-test]")
