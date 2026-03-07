# memU Health Sweep — 2026-02-27 06:02 EST

## Route Contract
- GET /api/v1/memu/health → status=ok, version=2.2.0, service="memU bridge" ✅
- POST /api/v1/memu/store → proof ID: dd70abf3-d674-4db7-82f7-f0f1edc37632 ✅
- POST /api/v1/memu/search → returns results ✅
- No 404s, no contract drift

## Smoke Check
- Store: id=dd70abf3 key='sweep-2026-02-27-0602' stored_at=2026-02-27T11:02:36Z ✅
- Search top 3: dd70abf3 (this sweep), aab17250 (03:04 sweep), 30ee1aec (empty-key issue) ✅
- idempotency working: idempotent=false (new record, correct)

## Last 24h Activity
- 03:04 EST sweep: PASS (id=aab17250) ✅
- 00:02 EST store: id=30ee1aec — empty key (recurring issue, see below)
- No ERROR/WARNING entries in logs

## Issues Found

### 1. Empty-key stores (recurring, non-critical)
- id=30ee1aec (2026-02-27 00:02 EST) — key='' (blank)
- Pattern also seen 2026-02-23 (×2)
- Root cause: caller not setting key field before store
- Fix: add server-side validation — reject store with empty key, return HTTP 400

### 2. Compression model 404 (stale, low priority)
- claude-haiku-4-5-20250514 not found on last compression attempt
- Fix: update model ref to claude-haiku-3-5 or disable compression if unused

### 3. Feb 26 sweep file was 0 bytes (fixed this run)
- Overwritten with full content in this run
- Fix: cron should write output atomically (write temp → mv)

## Canonical API Comparison (mem0 / LangChain / Zep)
- Route structure matches mem0: /store, /search, /health ✅
- TF-IDF + recency decay aligns with Zep temporal scoring ✅
- Fallback to LIKE+TF-IDF without OpenAI key ✅
- Gap: no /delete endpoint surfaced (both Zep and mem0 expose it)
- Gap: no bulk /store_batch (low priority)

## Status: HEALTHY
No critical issues. Two low-priority fixes queued.
