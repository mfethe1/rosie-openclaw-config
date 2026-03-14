# Lenny Hourly Self-Improvement — 2026-02-22 22:07 EST

## Self-Healing Actions (3 fixes shipped)

### Fix 1: hourly_self_reflect.py — API timeout & prompt size (SHIPPED)
- **Problem:** Script had 100% API timeout rate (12s too short for haiku JSON responses). Prompt input sizes (profile 3000 chars, TODO 2000 chars, 3-day memory) were too large.
- **Fix:** Increased timeout 12s→25s. Reduced prompt inputs: profile 3000→1500, TODO 2000→800, memory 3-day→2-day with tighter truncation. Removed incorrect LOCKED comment from Mack (the lock was causing 100% failure).
- **Result:** Script now successfully calls haiku and gets structured JSON responses. Verified live.
- **Files:** `self_improvement/scripts/hourly_self_reflect.py`

### Fix 2: Fail-scanner field name bug (SHIPPED)
- **Problem:** Lenny's inline fail-scanner (in `agents/lenny.md`) read `root_cause` field, but `fail-reflections.jsonl` entries use `probable_cause`. The scanner would NEVER detect 3+ recurrence escalations — it was silently broken.
- **Fix:** Updated scanner to check `probable_cause` first, fallback to `root_cause`. Matches standalone `lenny_fail_scanner.py` which already had the correct dual-field logic.
- **File:** `agents/lenny.md`

### Fix 3: Verified all 4 agent loops active (NO FIX NEEDED)
- **Proactive check:** All 4 agents produced output within last 1h (rosie, mack, winnie, lenny). 6 new eval-log entries on Feb 22, all PASS. No staleness detected. System is healthy.

## Proactive Scan Results
- memU: ✅ healthy (v1.4.0)
- shared-state.json: ✅ valid, cycle 51
- Fail-reflections: 9 entries, 0 in last 24h → no escalation triggers
- All agent outputs fresh (<1h)
- B-027/B-028: RESOLVED
- B-005/B-016: still CRITICAL/HIGH (awaiting Michael)
