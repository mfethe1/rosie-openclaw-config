#!/usr/bin/env python3
"""
acl_safety.py — ACL Phase 1: Safety rails.

Kill switch, cost caps, circuit breaker, idle detection, diagnostics.

Kill switch: ACL_ENABLED=0 env var OR ~/.openclaw/workspace/.acl/disabled file
Circuit breaker: 3 consecutive failures → pause 1 hour
Cost cap: max 20 primer API calls per hour
Idle detection: no message in 15min → stop priming
"""

import json
import os
import time
from datetime import datetime

ACL_DIR = os.path.expanduser("~/.openclaw/workspace/.acl")
STATE_FILE = os.path.join(ACL_DIR, "safety_state.json")
DISABLED_FILE = os.path.join(ACL_DIR, "disabled")

MAX_CALLS_PER_HOUR = 20
CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_PAUSE_S = 3600  # 1 hour
IDLE_TIMEOUT_S = 900  # 15 minutes


class ACLSafety:
    """Safety controller for ACL system."""

    def __init__(self):
        os.makedirs(ACL_DIR, exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "calls_this_hour": 0,
            "hour_start": time.time(),
            "consecutive_failures": 0,
            "circuit_breaker_until": 0,
            "last_message_at": time.time(),
            "total_calls": 0,
            "total_hits": 0,
            "total_misses": 0,
        }

    def _save_state(self):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(self._state, f, indent=2)
        except IOError:
            pass

    # ── Kill Switch ─────────────────────────────────────────────

    def is_enabled(self) -> bool:
        """Check if ACL is enabled (kill switch not engaged)."""
        if os.environ.get("ACL_ENABLED", "1") == "0":
            return False
        if os.path.exists(DISABLED_FILE):
            return False
        return True

    def disable(self, reason: str = "manual"):
        """Engage kill switch."""
        with open(DISABLED_FILE, "w") as f:
            f.write(json.dumps({
                "disabled_at": datetime.now().isoformat(),
                "reason": reason,
            }))

    def enable(self):
        """Disengage kill switch."""
        if os.path.exists(DISABLED_FILE):
            os.remove(DISABLED_FILE)
        self._state["consecutive_failures"] = 0
        self._state["circuit_breaker_until"] = 0
        self._save_state()

    # ── Cost Cap ────────────────────────────────────────────────

    def check_cost_cap(self) -> bool:
        """Check if we're within the hourly cost cap."""
        now = time.time()
        if now - self._state["hour_start"] > 3600:
            self._state["calls_this_hour"] = 0
            self._state["hour_start"] = now
        return self._state["calls_this_hour"] < MAX_CALLS_PER_HOUR

    def record_call(self):
        """Record a primer API call."""
        self._state["calls_this_hour"] += 1
        self._state["total_calls"] += 1
        self._save_state()

    # ── Circuit Breaker ─────────────────────────────────────────

    def check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows execution."""
        now = time.time()
        if now < self._state.get("circuit_breaker_until", 0):
            return False  # Still paused
        return True

    def record_success(self):
        """Reset failure counter on success."""
        self._state["consecutive_failures"] = 0
        self._save_state()

    def record_failure(self):
        """Record a failure. Trips breaker at threshold."""
        self._state["consecutive_failures"] += 1
        if self._state["consecutive_failures"] >= CIRCUIT_BREAKER_THRESHOLD:
            self._state["circuit_breaker_until"] = time.time() + CIRCUIT_BREAKER_PAUSE_S
            # Publish NATS alert
            try:
                import subprocess
                subprocess.run(
                    ["python3", os.path.expanduser(
                        "~/.openclaw/workspace/infra/nats/nats_bridge.py"
                    ), "broadcast", "system",
                     f"ACL circuit breaker tripped: {CIRCUIT_BREAKER_THRESHOLD} consecutive failures"],
                    capture_output=True, timeout=5,
                )
            except Exception:
                pass
        self._save_state()

    # ── Idle Detection ──────────────────────────────────────────

    def record_message(self):
        """Record that a message was received."""
        self._state["last_message_at"] = time.time()
        self._save_state()

    def is_idle(self) -> bool:
        """Check if user has been idle for >15 minutes."""
        return (time.time() - self._state.get("last_message_at", 0)) > IDLE_TIMEOUT_S

    # ── Cache Hit Tracking ──────────────────────────────────────

    def record_hit(self):
        self._state["total_hits"] = self._state.get("total_hits", 0) + 1
        self._save_state()

    def record_miss(self):
        self._state["total_misses"] = self._state.get("total_misses", 0) + 1
        self._save_state()

    # ── Gate Check ──────────────────────────────────────────────

    def can_prime(self) -> tuple[bool, str]:
        """Master check: should we prime? Returns (allowed, reason)."""
        if not self.is_enabled():
            return False, "kill_switch"
        if not self.check_circuit_breaker():
            return False, "circuit_breaker"
        if not self.check_cost_cap():
            return False, "cost_cap"
        if self.is_idle():
            return False, "idle"
        return True, "ok"

    # ── Diagnostics ─────────────────────────────────────────────

    def status(self) -> dict:
        """Full ACL status for diagnostics."""
        allowed, reason = self.can_prime()
        hits = self._state.get("total_hits", 0)
        misses = self._state.get("total_misses", 0)
        total = hits + misses
        return {
            "enabled": self.is_enabled(),
            "can_prime": allowed,
            "block_reason": reason if not allowed else None,
            "calls_this_hour": self._state.get("calls_this_hour", 0),
            "max_calls_per_hour": MAX_CALLS_PER_HOUR,
            "consecutive_failures": self._state.get("consecutive_failures", 0),
            "circuit_breaker_active": not self.check_circuit_breaker(),
            "idle": self.is_idle(),
            "total_calls": self._state.get("total_calls", 0),
            "cache_hits": hits,
            "cache_misses": misses,
            "hit_rate": round(hits / total * 100, 1) if total > 0 else 0,
            "last_message_ago_s": round(time.time() - self._state.get("last_message_at", 0)),
        }


if __name__ == "__main__":
    import sys

    safety = ACLSafety()

    if "--status" in sys.argv or "status" in sys.argv:
        print(json.dumps(safety.status(), indent=2))
    elif "--disable" in sys.argv:
        reason = sys.argv[sys.argv.index("--disable") + 1] if len(sys.argv) > sys.argv.index("--disable") + 1 else "manual"
        safety.disable(reason)
        print(f"ACL disabled: {reason}")
    elif "--enable" in sys.argv:
        safety.enable()
        print("ACL enabled")
    else:
        print("Usage: acl_safety.py [status|--disable [reason]|--enable]")
        print(json.dumps(safety.status(), indent=2))
