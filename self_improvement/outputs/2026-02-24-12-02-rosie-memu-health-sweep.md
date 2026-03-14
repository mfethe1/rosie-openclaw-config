# memU Health Sweep (last 24h) — 2026-02-24 12:02 EST

## Scope completed
- Verified local/bridge route contract behavior
- Ran eval-gate smoke checks
- Compared current memU bridge API against canonical memU-server patterns and competitor memory APIs (Mem0, Zep, LangMem)

## Findings
1) **Route contract status: PASS (bridge)**
- `GET /api/v1/memu/health` returns `status: ok`
- `POST /api/v1/memu/store` and `POST /api/v1/memu/search` operational
- Direct `/health` on root returns unknown endpoint (intentional for bridge-only contract right now)
- Contract proof ID: `f7e06753-8e74-491e-a03c-c2331cdbd5bb`

2) **Smoke gate status: PASS after one contract-compliant retry**
- First run failed due stale CHANGELOG window (policy gate)
- After CHANGELOG refresh, rerun passed all checks
- Eval proof ID (PASS): `6b47dea3-9760-4363-845d-c564a486edb4`

3) **24h operational pulse**
- Eval log entries in last 24h: 26 total
- Agent distribution: rosie 11, lenny 8, winnie 3, mack 2, hephaestus 1, sisyphus 1
- memU health currently reports DB/WAL normal and `pending_gc=0`

4) **API pattern comparison (gap scan)**
- Current bridge is strong on reliability/idempotency/TTL and lightweight search
- Relative gaps versus canonical & competitors:
  - No standardized ingest/retrieve aliases (`/memorize`, `/retrieve`) for easier drop-in parity
  - No explicit pagination/cursor contract on list/search responses
  - No hybrid retrieval option (keyword + vector/rerank toggle) surfaced as API parameter
  - No OpenAPI schema endpoint for client auto-generation

## Concrete fixes
1. Add compatibility aliases:
   - `POST /memorize` -> bridge `store`
   - `POST /retrieve` -> bridge `search`/`semantic-search`
2. Add `limit/offset` (or cursor) response envelope consistency:
   - `{results, count, next_cursor}`
3. Add retrieval mode param:
   - `mode=keyword|semantic|hybrid` (default `hybrid` once embeddings/reranker path is available)
4. Publish OpenAPI JSON + minimal SDK usage snippets for local agents.
5. Keep smoke gate strict: fail-first on stale CHANGELOG was correct; retain as-is.
