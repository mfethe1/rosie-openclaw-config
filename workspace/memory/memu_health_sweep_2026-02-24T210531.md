# memU health sweep 2026-02-24T210531

## Route contract checks
- GET /api/v1/memu/health: OK
{
  "status": "ok",
  "service": "memU bridge",
  "version": "2.2.0",
  "features": [
    "sqlite-storage",
    "like-and-tfidf-search",
    "tfidf-semantic-search",
    "recency-decay",
    "use-count-boost",
    "idempotency",
    "content-hash-dedup",
    "event-stream",
    "wal-auto-checkpoint",
    "wal-threshold-escalation",
    "periodic-gc",
    "crash-recovery",
    "atomic-event-log",
    "thread-local-conn-pool",
    "begin-immediate",
    "explicit-rollback",
    "health-triggered-checkpoint",
    "expires-at-ttl",
    "event-log-rotation",
    "connection-recovery"
  ],
  "db_path": "/Users/harrisonfethe/.openclaw/workspace/memory/memu_store/memu.db",
  "db_bytes": 729088,
  "wal_bytes": 86552,
  "row_count": 549,
  "pending_gc": 0,
  "ttl_days": 180,
  "timestamp": "2026-02-25T02:05:31.812315+00:00"
}
- GET /health (direct contract probe): HTTP 404
- POST /memorize (canonical memU-server alias probe): HTTP 401
- POST /retrieve (canonical memU-server alias probe): HTTP 401
- POST /api/v1/memu/store without auth (security probe): HTTP 401

## API parity notes
- Bridge contract is healthy and authenticated on /api/v1/memu/*.
- Canonical memU-server endpoints (/memorize, /retrieve) are not currently exposed in this bridge.
- Direct /health endpoint not exposed; current contract is bridge-only.
