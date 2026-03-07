# memU Health Sweep (last 24h) — 2026-02-24 03:02 EST

## Scope
- Verified local/bridge route contract and endpoint behavior
- Ran memU smoke checks
- Reviewed last 24h memU runtime activity
- Compared current implementation against canonical mem0/LangChain/Zep API patterns

## Findings
1. **Route contract = bridge and healthy**
   - `GET /api/v1/memu/health` returns `status=ok`, version `2.2.0`.
   - Canonical paths in use: `/api/v1/memu/health`, `/api/v1/memu/store`, `/api/v1/memu/search`.
   - Legacy/non-canonical checks: `/health` returns 404 (expected); no contract drift observed on localhost.

2. **Smoke checks**
   - `memu_server/test_memu.sh` passed endpoint checks (health/store/search/list).
   - `memu_server/smoke_test.sh` initially failed only due to missing output artifact, then passed after report creation.

3. **Last-24h runtime quality**
   - `memory/memu_server.log`: 614 recent lines, **0 errors/exceptions**.
   - SQLite store activity in last 24h: **223 rows** written.
   - Health telemetry: TTL active (180d), GC pending=0, WAL checkpointing active.

4. **Canonical + competitor pattern comparison**
   - **Aligned:** explicit health endpoint, auth-guarded mutating endpoints, idempotency/dedup, metadata fields, TTL, and search endpoint separation.
   - **Gap vs common API patterns (mem0-style/OpenAPI-first):** no discoverable `/docs` OpenAPI contract, and route naming differs from common `/memories` CRUD shape.
   - **Gap vs LangGraph/Zep usage patterns:** lacks first-class namespace/run/thread scoping and filterable search dimensions beyond current fields.

## Concrete fixes (next actions)
1. **Add OpenAPI/JSON schema endpoint** for route discoverability and contract linting (`/api/v1/memu/schema` or migrate to FastAPI with `/docs`).
2. **Add compatibility aliases** for `/memories` and `/memories/search` (with deprecation headers) to reduce integration friction.
3. **Add namespace fields** (`org_id`, `thread_id`, `run_id`) + indexed filters for competitor-parity retrieval.
4. **Close known ops debt:** resolve `memory/issues.md` B-015 (canonical IP drift in prompts) and B-017 (ensure ANTHROPIC_API_KEY sourced in `start.sh`) to prevent partial-feature regressions.

## Command evidence
- `curl -sS http://localhost:8711/api/v1/memu/health`
- `bash memu_server/test_memu.sh`
- `bash memu_server/smoke_test.sh rosie memu-health-sweep-24h memory/memu_health_sweep_2026-02-24.md "cron 24h sweep"`
