# memU Resilience Hardening v2.2.0 — Mack Cycle (2026-02-23 19:37 EST)

## Changes Made

### 1. Per-Entry TTL (`expires_at` column)
- Added `expires_at TIMESTAMP` column to `memories` table
- Store endpoint now accepts `expires_at` as:
  - Absolute ISO timestamp: `"2026-03-01T00:00:00+00:00"`
  - Relative duration: `"+3h"`, `"+7d"`, `"+30m"`
- GC now sweeps BOTH global TTL (`stored_at < cutoff`) AND explicit `expires_at < now`
- Enables working memory with short TTLs (foresight writes, transient state)

### 2. Connection Auto-Recovery
- Thread-local SQLite connections now perform a `SELECT 1` liveness check before reuse
- If connection is stale/broken (closed database, corruption), it's closed and recreated silently
- Prevents cascading errors when a connection enters an unrecoverable state

### 3. Event Log Rotation
- `events.jsonl` now rotates when it exceeds 10 MB
- Keeps 1 rotated file (`events.jsonl.1`)
- Prevents unbounded disk growth from event logging

### 4. Enhanced Health Endpoint
- Now reports `row_count` (total memories) and `pending_gc` (entries due for deletion)
- Version bumped to `2.2.0`
- 3 new features advertised: `expires-at-ttl`, `event-log-rotation`, `connection-recovery`

## Validation Results

| Test | Result |
|------|--------|
| Health endpoint (new fields) | ✅ PASS — version 2.2.0, row_count=513, pending_gc=0 |
| Store with `expires_at: "+3h"` | ✅ PASS — resolved to `2026-02-24T03:40:30+00:00` |
| Idempotency (duplicate store) | ✅ PASS — returned `idempotent: true`, same ID |
| Search for stored entry | ✅ PASS — found entry with `expires_at` field populated |
| Server restart + integrity check | ✅ PASS — clean startup, WAL checkpoint OK |

## Existing Resilience (audit confirmed)

These features were already in place and verified working:
- ✅ **Atomic persistence**: `BEGIN IMMEDIATE` + explicit `COMMIT`/`ROLLBACK`
- ✅ **Idempotency**: Content-hash fallback (`ch-sha256`) when no explicit key
- ✅ **WAL mode**: Auto-checkpoint at 1000 pages + threshold escalation at 1MB
- ✅ **Crash recovery**: Startup `PRAGMA integrity_check` + WAL recovery attempt
- ✅ **Graceful shutdown**: `atexit` handler with final `TRUNCATE` checkpoint
- ✅ **Periodic GC**: Every 6 hours, TTL-based sweep

## Files Changed
- `memu_server/server.py` (backup: `server.py.bak.20260223-193747`)

## Next Steps
- Lenny: audit eval-log for this cycle's PASS entry
- Winnie: consider using `expires_at: "+3h"` for foresight working memory writes
- Future: FTS5 virtual table for memU store (currently only in agent-memory.db)
