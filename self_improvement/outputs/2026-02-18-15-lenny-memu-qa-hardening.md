# Lenny — memU QA Hardening Cycle (2026-02-18 15:52 EST)

## Scope
- Contract drift checks
- Duplicate/idempotency edge cases
- Stale recovery behavior
- Observability for failures/denials
- Blocking issue triage

## Evidence
1) Contract check against bridge endpoint:
- `GET /api/v1/memu/health` => 200
- `POST /api/v1/memu/store` => 200
- `GET /health` => 404 (legacy/bare route absent)
- Store proof ID: `934022b0-1d57-4cd2-896b-d06ef1c74c1a`

2) Idempotency edge tests:
- First write with idempotency key => `id=f73be6af-e6ea-42f7-9a05-d0a19c4e008e`, `idempotent=false`
- Retry same payload + same key => same ID, `idempotent=true`
- Retry DIFFERENT payload + same key => same ID, `idempotent=true`, returned original content (`same payload A`)
- Finding: idempotency is key-only replay; no payload hash mismatch warning/deny.

3) Stale recovery behavior:
- Forced server restart (`pkill` + `start.sh`) and health recovered (`status=ok`, `version=1.2.0`, `wal_exists=true`)
- Prior WAL replay proof exists in log: `WAL recovery replayed 1 op(s)`.

4) Observability for failures/denials:
- Unauthorized store attempt => 401 with explicit error body
- Bad payload (authorized) => 400 with explicit validation error
- Gap: request-denial events are not clearly logged as structured security/audit events in memu_server.log.

## Blocking triage
- **BLOCKER-NEW (HIGH):** Idempotency collision risk — same idempotency key silently replays even when payload differs. Could mask dropped updates/retries with mutated content.
  - Suggested fix: store request digest with idempotency key and return 409 on mismatch.
- **BLOCKER-NEW (MEDIUM):** Denial observability gap — 401/400 responses lack dedicated structured audit logs (path, client, reason, request_id).
  - Suggested fix: add auth/validation failure logging counters and periodic summary.
- **BLOCKER-WATCH (MEDIUM):** Route shape split still active (`/api/v1/memu/*` vs bare service routes elsewhere); contract must stay pinned in all scripts.

## Verdict
- **Status:** PARTIAL PASS (functional core healthy; hardening gaps remain)
- **Reason:** contract and restart behavior are healthy; idempotency mismatch handling and denial observability are not yet hardened.
