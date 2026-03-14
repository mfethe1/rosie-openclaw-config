# memU Health Sweep (last 24h) — 2026-02-24 09:02 EST

## Scope
- Verified route contract (bridge vs direct/local)
- Ran live smoke checks (health/store/search + endpoint test suite)
- Reviewed eval outcomes for last 24h
- Compared current bridge API surface to canonical memU-server and common competitor patterns (mem0/Zep-style)

## Findings
1) Contract + health
- `GET /api/v1/memu/health` = healthy (`status: ok`, version `2.2.0`, row_count `543+`).
- Direct-style probe `GET /health` returns `404 Unknown endpoint` (expected for bridge-only server).
- `start.sh` confirms service already healthy (PID present, no restart required).

2) Smoke checks
- `memu_server/test_memu.sh` completed successfully on bridge endpoints.
- Live probe store/search PASS:
  - store id: `33b5d78b-f10e-45ea-89ee-a918d67b281b`
  - search count: `1` for probe key.

3) Last-24h eval quality snapshot
- Eval entries in 24h: `32` total (`26 PASS`, `6 FAIL`).
- FAILs were gate-artifact issues (missing/stale output or stale changelog), not memU endpoint outages.
- Latest PASS proofs include: `5c60feef-cc87-4077-a62e-9b80006daa8f`, `bc62cd27-e688-4dec-be83-6222bf1e90a6`, `32a82e8d-da55-4a0a-97aa-6645c2374dbc`.

4) Canonical + competitor comparison
- Aligned:
  - Auth-guarded writes/search, idempotency, TTL/expires_at, recency-aware scoring, WAL-backed persistence.
- Gaps vs canonical memU-server (FastAPI/OpenAPI-first):
  - No discoverable OpenAPI docs (`/docs`/`/openapi.json`) for contract linting/client generation.
- Gaps vs mem0/Zep-style memory APIs:
  - No compatibility aliases for `/memories` CRUD/query shape.
  - Limited first-class multi-tenant/thread scoping fields (`org_id`, `thread_id`, `run_id`) in API filters.

## Concrete fixes
1. Add read-only schema endpoint (`/api/v1/memu/schema`) now; optional future move to FastAPI docs parity.
2. Add compatibility aliases:
   - `POST /memories` -> proxy to `/api/v1/memu/store`
   - `POST /memories/search` -> proxy to `/api/v1/memu/search`
   (include deprecation headers).
3. Add optional filter fields and indexes: `org_id`, `thread_id`, `run_id`.
4. Reduce noisy FAIL churn in sweep crons by pre-touching output artifact before smoke gate.

## Evidence commands
- `bash memu_server/start.sh`
- `curl -sS http://localhost:8711/api/v1/memu/health`
- `curl -sS -o /tmp/memu_direct_health.json -w '%{http_code}' http://localhost:8711/health`
- `bash memu_server/test_memu.sh`
- Python live store/search probe (bridge endpoints)
- Python parse of `memory/eval-log.md` for 24h PASS/FAIL counts
