# Lenny QA Hardening — memU Bridge Server
**Date:** 2026-02-23 09:45 EST  
**Agent:** Lenny (QA/Health/Resilience)  
**Task:** memU QA hardening cycle — contract drift, idempotency, stale recovery, observability

---

## Verdict: PASS (with 5 findings, 0 critical blockers)

### Summary
memU bridge v2.1.0 is **operationally healthy** — DB integrity OK, idempotency working correctly (both explicit key and content-hash fallback), auth denial enforced, WAL size healthy (86KB), 258 successful stores today with 0 failures. Five non-critical findings require remediation.

---

## Test Results

### 1. Contract Drift Check
| Endpoint | Status | Notes |
|----------|--------|-------|
| GET /health | ✅ PASS | v2.1.0, 17 features, db_bytes=647168 |
| GET /list | ✅ PASS | Returns entries correctly |
| POST /store | ✅ PASS | Stores and returns entry |
| POST /search | ✅ PASS | LIKE-based search works |
| POST /semantic-search | ✅ PASS | TF-IDF ranking works |
| POST /log_event | ✅ PASS | Atomic append with fsync |
| GET /pulse | ✅ PASS | Event ledger readable |

**FINDING F-001 (MEDIUM):** Health endpoint advertises `"fts"` as a feature, but no FTS5 virtual table (`memories_fts`) exists in the database. The `/search` endpoint uses `LIKE %query%` fallback. This is a **contract misrepresentation** — the feature list should either say `"like-search"` or FTS5 should be created.

### 2. Duplicate Idempotency Edge Cases
| Test | Result | Notes |
|------|--------|-------|
| Explicit idempotency_key (same key, same content) | ✅ PASS | Returns same ID |
| Content-hash dedup (no key, same content) | ✅ PASS | Returns same ID |
| Different content, same user | ✅ PASS | Creates new entry |
| Empty content | ✅ PASS | Rejected with 400 |
| Missing content field | ✅ PASS | Rejected with 400 |
| Missing user_id | ⚠️ MINOR | Accepted (defaults to agent_id) — acceptable |

### 3. Stale Recovery / DB Health
| Check | Result |
|-------|--------|
| SQLite integrity_check | ✅ ok |
| WAL size | ✅ 86KB (healthy) |
| Total entries | 492 |
| Idempotency collisions | ✅ 0 |
| NULL idempotency_keys | ✅ 0 |
| Startup integrity check | ✅ Has crash recovery logic |
| Graceful shutdown hook | ✅ atexit registered |

### 4. Observability
| Check | Result |
|-------|--------|
| Structured logging | ✅ File + stdout |
| Auth denial logging | ✅ 13 denials today (401 returned) |
| Store success logging | ✅ 258 stores logged |
| Store failure logging | ✅ 0 failures (would be logged) |
| Event ledger (/pulse) | ✅ Works |
| SSE /events endpoint | ❌ Not implemented (advertised nowhere, acceptable) |

**FINDING F-002 (MEDIUM):** 270 WARNINGs today — all from compression failures. Anthropic `claude-3-5-haiku-latest` returns 404 (model renamed/retired). OpenAI `gpt-4o-mini` returns 429 (quota exhausted). Compression silently degrades to passthrough (safe), but log noise is extreme. **Fix: update model name to `claude-haiku-4-5-20250514` or equivalent; add circuit breaker to suppress repeated failures.**

### 5. Agent ID Anomalies
**FINDING F-003 (LOW):** 3 non-standard agent_id values in DB:
- `'Mack'` (3 entries) — case mismatch, should be `'mack'`
- `'lenny-qa'` (2 entries) — from prior QA probes
- `'--help'` (1 entry) — CLI argument leaking as agent_id (smoke_test.sh invocation error)

**Recommendation:** Add server-side agent_id normalization (lowercase, reject if starts with `-`).

### 6. Dual Process
**FINDING F-004 (LOW):** Two memU server processes running:
- PID 1033 → `memu-service/server.py` (started 6:30 AM)
- PID 35859 → `memu_server/server.py` (started 9:21 AM)

Both may bind different ports. Only port 8711 is in use by active agents. The other process is wasting ~400MB memory.

### 7. OpenAI Embedding Quota
**FINDING F-005 (HIGH):** `memory_search` (OpenClaw's built-in) is **completely unavailable** — OpenAI embedding quota exhausted (429). This breaks MEMORY.md semantic recall for all agents. **Fix: top up OpenAI billing or switch embedding provider.**

---

## Proof Keys
- memU store proof: (pending smoke_test.sh run)
- DB integrity: `PRAGMA integrity_check = ok`
- Idempotency verified: explicit key + content-hash both confirmed
- Contract coverage: 7/7 endpoints tested

## Remediation Priority
1. **F-005** (HIGH) — OpenAI quota: affects all memory_search
2. **F-001** (MEDIUM) — FTS feature label drift
3. **F-002** (MEDIUM) — Compression model 404 + log noise
4. **F-003** (LOW) — Agent ID normalization
5. **F-004** (LOW) — Dual process cleanup
