# Lenny memU QA Hardening — 2026-02-23 19:41 EST

## Cycle: lenny-memu-qa-hardening-2026-02-23

### Server Status
- **Version:** 2.2.0
- **Port:** 8711 (healthy)
- **DB rows:** 515
- **DB integrity:** OK
- **WAL size:** 112KB (healthy, <1MB threshold)
- **Pending GC:** 0
- **Expired entries:** 0

---

### 1. Contract Drift Checks

**Finding: 3 undocumented endpoints**

The server docstring declared 4 endpoints but the code implements 7:

| Endpoint | Documented? | Status |
|----------|------------|--------|
| `POST /api/v1/memu/store` | ✅ | Working |
| `POST /api/v1/memu/search` | ✅ | Working |
| `GET /api/v1/memu/health` | ✅ | Working |
| `GET /api/v1/memu/list` | ✅ | Working |
| `GET /api/v1/memu/pulse` | ❌ UNDOCUMENTED | Working |
| `POST /api/v1/memu/log_event` | ❌ UNDOCUMENTED | Working |
| `POST /api/v1/memu/semantic-search` | ❌ UNDOCUMENTED | Working |

**Fix applied:** Updated docstring to document all 7 endpoints with descriptions.

**Smoke test alignment:** smoke_test.sh only exercises `/health`, `/store`, `/search` — adequate for gate checks.

---

### 2. Duplicate Idempotency Edge Cases

**All PASS:**
- ✅ Store new entry → returns `idempotent: false`, new UUID
- ✅ Store identical content → returns `idempotent: true`, same UUID (content-hash dedup working)
- ✅ Search returns exactly 1 result (no duplicate rows)
- ✅ Idempotency key format: `ch-<content_hash_prefix>`

---

### 3. Input Validation / Auth

**All PASS:**
- ✅ Empty content → 400 "Missing required field: content or key"
- ✅ Missing auth → 401 "Unauthorized"
- ✅ Wrong auth → 401 "Unauthorized"
- ✅ Invalid JSON → 400 "Missing required field"
- ✅ Unknown endpoint → 404 "Unknown endpoint"

---

### 4. Stale Recovery Behavior

**All PASS:**
- ✅ TTL sweep runs every 6 hours (GC interval)
- ✅ Global TTL: 180 days + per-entry `expires_at` support
- ✅ WAL checkpoint: every 5 minutes (PASSIVE) or 1MB threshold (TRUNCATE escalation)
- ✅ Startup integrity check with WAL recovery fallback
- ✅ Thread-local connection pool with stale-connection detection
- ✅ Crash-safe: atomic event log, `BEGIN IMMEDIATE` transactions, explicit rollback

---

### 5. Observability — Failures/Denials

**Two active compression provider failures detected:**

| Provider | Error | Count | Impact |
|----------|-------|-------|--------|
| Anthropic | 404: model `claude-3-5-haiku-latest` not found | 214 | Compression skipped |
| OpenAI | 429: quota exceeded | 292 | Compression skipped |

**Fix applied:** Updated model name `claude-3-5-haiku-latest` → `claude-haiku-4-5-20250514`

**Additional fix:** Duplicate log handler bug. `logging.basicConfig()` + `getLogger("memu")` with propagation caused every log line to be written twice to the file. Fixed by using explicit handler attachment with `propagate=False`.

**Impact:** Log file will be ~50% smaller going forward. 894 error lines (mostly doubled) in current log.

---

### 6. Blocking Issue Triage

| Issue | Status | Notes |
|-------|--------|-------|
| B-005 (Telegram group ID) | OPEN — blocked on Michael | 4 crons affected |
| B-028 (X Post crons) | OPEN — owner: Mack | Medium severity |
| GUARDRAIL-002 (shared-state race) | PARTIAL — file repaired | Atomic write pending |
| B-014 (Winnie benchmark timeout) | OPEN | Increased to 900s |
| B-016 (Strategic crons blocked) | OPEN — blocked by B-005 | Revenue insights lost |
| memory_search embedding quota | ACTIVE DEGRADATION | OpenAI billing needed |

**OpenAI embedding quota is exhausted** — `memory_search` tool returns `disabled=true`. This blocks all semantic memory recall for all agents. Needs billing action from Michael.

---

### 7. Second memU Instance

Found TWO memU server processes:
- PID 4499: `/workspace/memu-service/server.py` (old, different API surface)
- PID 7489: `/workspace/memu_server/server.py` (canonical, port 8711)

The `memu-service/` instance appears to be a legacy deployment. Not blocking but worth cleaning up.

---

### Changes Applied This Cycle
1. `server.py` docstring: Added 3 missing endpoint docs (pulse, log_event, semantic-search)
2. `server.py` compression model: `claude-3-5-haiku-latest` → `claude-haiku-4-5-20250514`
3. `server.py` logging: Fixed duplicate handler (propagate=False, explicit handler setup)

### Verdict: PASS (with caveats)
- Core memU functionality: **SOLID** — store, search, dedup, auth, recovery all working
- Compression: **DEGRADED** — both providers failing (model fix applied, OpenAI quota needs billing)
- Observability: **IMPROVED** — duplicate logging fixed
- Contract: **ALIGNED** — docstring now matches implementation
