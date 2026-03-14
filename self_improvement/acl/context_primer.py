#!/usr/bin/env python3
"""
context_primer.py — ACL Phase 1: Parallel context fetcher.

Fires 3 data fetches in parallel when Michael sends a message.
Results cached for 60s. Debounce: skip if last fetch <30s ago.

Usage:
    from context_primer import ContextPrimer
    primer = ContextPrimer()
    context = primer.prime()  # Returns cached or fresh context dict
"""

import json
import os
import subprocess
import time
import threading
from datetime import datetime

ACL_DIR = os.path.expanduser("~/.openclaw/workspace/.acl")
CACHE_FILE = os.path.join(ACL_DIR, "context_cache.json")
CACHE_TTL = 60  # seconds
DEBOUNCE = 30  # seconds — skip if last fetch was within this window
ENABLED_FILE = os.path.join(ACL_DIR, "enabled")


def _acl_enabled() -> bool:
    """Check kill switch."""
    if os.environ.get("ACL_ENABLED", "1") == "0":
        return False
    if os.path.exists(os.path.join(ACL_DIR, "disabled")):
        return False
    return True


def _run_cmd(cmd: list[str], timeout: int = 10) -> str:
    """Run a command, return stdout or error string."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else f"ERROR: {r.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        return "ERROR: timeout"
    except Exception as e:
        return f"ERROR: {str(e)[:200]}"


def fetch_cron_health() -> dict:
    """Fetch openclaw status + recent cron errors."""
    status = _run_cmd(["openclaw", "status"], timeout=15)
    cron_list = _run_cmd(["openclaw", "cron", "list"], timeout=10)
    return {
        "type": "cron_health",
        "status": status[:2000],
        "cron_summary": cron_list[:2000],
        "fetched_at": time.time(),
    }


def fetch_git_status() -> dict:
    """Fetch recent commits, open PRs, CI status."""
    # Last 5 commits across workspace repos
    commits = _run_cmd(
        ["git", "-C", os.path.expanduser("~/.openclaw/workspace"), "log", "--oneline", "-5"],
        timeout=5,
    )
    # Check for open PRs via gh if available
    prs = _run_cmd(["gh", "pr", "list", "--limit", "5", "--state", "open"], timeout=10)
    return {
        "type": "git_status",
        "recent_commits": commits[:1000],
        "open_prs": prs[:1000],
        "fetched_at": time.time(),
    }


def fetch_agent_status() -> dict:
    """Check which agents ran recently and any failures."""
    # Check cron job history for agent runs
    jobs = _run_cmd(["openclaw", "cron", "list"], timeout=10)
    return {
        "type": "agent_status",
        "cron_jobs": jobs[:2000],
        "fetched_at": time.time(),
    }


class ContextPrimer:
    """Parallel context fetcher with caching and debounce."""

    def __init__(self):
        os.makedirs(ACL_DIR, exist_ok=True)
        self._cache = {}
        self._last_fetch = 0
        self._fetch_count = 0
        self._hourly_reset = time.time()
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE) as f:
                    data = json.load(f)
                if time.time() - data.get("fetched_at", 0) < CACHE_TTL:
                    self._cache = data
                    self._last_fetch = data.get("fetched_at", 0)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_cache(self):
        """Persist cache to disk."""
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f, indent=2)
        except IOError:
            pass

    def _check_cost_cap(self) -> bool:
        """Enforce max 20 API calls per hour."""
        now = time.time()
        if now - self._hourly_reset > 3600:
            self._fetch_count = 0
            self._hourly_reset = now
        return self._fetch_count < 20

    def prime(self) -> dict:
        """Fetch context data. Returns cached if fresh, fetches if stale."""
        if not _acl_enabled():
            return {"acl": "disabled"}

        now = time.time()

        # Debounce: skip if last fetch was <30s ago
        if now - self._last_fetch < DEBOUNCE and self._cache:
            return self._cache

        # Check cache TTL
        if self._cache and now - self._cache.get("fetched_at", 0) < CACHE_TTL:
            return self._cache

        # Cost cap check
        if not self._check_cost_cap():
            return self._cache if self._cache else {"acl": "cost_cap_reached"}

        # Parallel fetch
        results = {}
        errors = []
        threads = []

        fetchers = {
            "cron_health": fetch_cron_health,
            "git_status": fetch_git_status,
            "agent_status": fetch_agent_status,
        }

        def _fetch(name, fn):
            try:
                results[name] = fn()
            except Exception as e:
                errors.append(f"{name}: {str(e)[:100]}")
                results[name] = {"type": name, "error": str(e)[:200]}

        for name, fn in fetchers.items():
            t = threading.Thread(target=_fetch, args=(name, fn))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=15)

        self._cache = {
            "fetched_at": now,
            "fetched_at_iso": datetime.now().isoformat(),
            "errors": errors,
            **results,
        }
        self._last_fetch = now
        self._fetch_count += 1
        self._save_cache()

        return self._cache

    def get_cached(self) -> dict:
        """Return current cache without fetching."""
        return self._cache

    def invalidate(self):
        """Force next prime() to fetch fresh data."""
        self._last_fetch = 0
        self._cache = {}


# Singleton instance
_primer = None

def get_primer() -> ContextPrimer:
    global _primer
    if _primer is None:
        _primer = ContextPrimer()
    return _primer


def prime_context() -> dict:
    """Convenience function: get or create primer, return context."""
    return get_primer().prime()


if __name__ == "__main__":
    import sys
    if "--status" in sys.argv:
        p = get_primer()
        cached = p.get_cached()
        if cached:
            print(json.dumps(cached, indent=2, default=str))
        else:
            print("No cached context. Run without --status to fetch.")
    else:
        print("Priming context...")
        ctx = prime_context()
        print(json.dumps(ctx, indent=2, default=str))
