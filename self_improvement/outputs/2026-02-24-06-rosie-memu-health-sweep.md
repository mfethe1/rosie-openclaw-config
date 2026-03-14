# memU health sweep (last 24h)

Time: 2026-02-24 06:02 America/Indianapolis
Scope: route contract, smoke checks, canonical/competitor comparison, fixes

## Live checks
- Direct contract probe (`/health`): returns `Unknown endpoint` (expected for bridge-only server).
- Bridge health (`/api/v1/memu/health`): PASS.
  - version: `2.2.0`
  - row_count: `541`
  - db_bytes: `724,992`
  - wal_bytes: `78,312`
  - pending_gc: `0`
- Bridge store/search roundtrip: PASS.
  - store id: `52631557-4784-4312-b64e-e74e5cd65e8f`
  - search count: `1`

## 24h data snapshot (SQLite)
- Total memories written in last 24h: `88`
- Eval-category writes in last 24h: `23`
- Top writers: rosie `24`, shared `21`, lenny `13`, mack `12`, winnie `12`

## Contract verification result
- Current server is **bridge canonical** (`/api/v1/memu/*`) not direct mem0-oss style (`/health`, `/memories`, `/search`).
- Smoke script auto-detection is functioning and correctly routes to bridge.

## Canonical API / competitor comparison (concise)
- mem0-style REST pattern: CRUD + semantic search + entity scoping + events/webhooks.
  - memU status: partial alignment (store/search/list/health/log_event present; update/delete/history/webhooks absent).
- Zep pattern: hybrid retrieval (semantic + lexical + graph/temporal relationships).
  - memU status: lexical + TF-IDF + recency/use-boost present; graph/relationship memory absent.
- LangMem pattern: schema-aware extraction + background consolidation.
  - memU status: has compression/auto-tags and periodic GC/checkpoints; lacks schema-validated memory types and first-class consolidation jobs.

## Findings
1) Route contract is stable and healthy on bridge endpoints.
2) No current WAL/GC pressure (`wal_bytes` low, `pending_gc=0`).
3) Known platform blocker persists: `memory_search` tool unavailable (OpenAI embeddings quota 429).
4) Feature gap vs canonical memory APIs: no update/delete endpoint and no paginated query contract.
5) Retrieval gap vs competitors: no hybrid BM25+vector rerank, no graph/relationship retrieval.

## Concrete fixes
- F1 (today): Keep all cron/client calls pinned to `/api/v1/memu/*`; fail-fast if bare `/health` used in production flows.
- F2 (today): Add bridge API contract test in CI/cron: verify `/health` fails and `/api/v1/memu/health` passes to catch drift.
- F3 (next): Add `POST /api/v1/memu/update` + `POST /api/v1/memu/delete` to close core CRUD gap.
- F4 (next): Add paginated list/search (`cursor` or `offset+limit`) for canonical API parity.
- F5 (later): Add optional vector backend (FastEmbed/SQLite-vec) with hybrid rerank to narrow gap with Zep/mem0 retrieval quality.
- F6 (platform owner): Restore `memory_search` embedding quota or switch provider wiring so recall tool comes back online.
