# Lenny — memU QA Hardening Cycle (2026-02-18 18:47 EST)

## Scope executed
- Contract drift checks
- Duplicate/idempotency edge-case replay behavior
- Stale recovery behavior
- Failure/denial observability check
- Blocking issue triage

## Evidence (current cycle)
1) Contract + route behavior
- `GET /api/v1/memu/health` => `200`
- `GET /health` => `404`
- Runtime health payload reports `version=1.2.0`
- Source file `/memu_server/server.py` currently declares `version=1.3.0`
- **Drift signal:** served contract/version does not match checked-in bridge source.

2) Idempotency edge-case probe (body `idempotency_key=qa-lenny-<ts>`)
- First write: `id=2f88f576-fa6d-4e89-87fd-7a411a9ab5e9`, `idempotent=false`
- Replay same payload: same ID, `idempotent=true`
- Replay mutated payload with same key: same ID, `idempotent=true`, entry content remains original (`payload A`)
- **Finding:** key-only idempotency replay accepts payload mutation silently (no mismatch reject/warn).

3) Stale recovery behavior
- Forced restart + health check after restart: `status=ok`, `wal_exists=true`
- Log tail includes WAL replay activity (`WAL recovery replayed ... op(s)`).

4) Observability for failures/denials
- Unauthorized store: `401` with explicit error body
- Bad payload (authorized): `400` with explicit error body
- `/api/v1/memu/pulse` events count before denials: `0`
- `/api/v1/memu/pulse` events count after denials: `0`
- Manual `/api/v1/memu/log_event` succeeds (`event_id=cd85098e-4d5b-4cde-a1c0-2b96526da0dd`), pulse count increments to `1`
- **Finding:** denials are returned to caller but not automatically emitted into event stream (audit gap).

## Blocking triage
- **BLOCKER-HIGH:** Idempotency payload mismatch is not detected; mutated retries are silently replayed.
  - Fix: persist request digest with idempotency key and return `409` on mismatch.
- **BLOCKER-HIGH:** Contract/runtime drift (health version and/or active service mismatch) indicates ambiguous serving binary/process.
  - Fix: single active memU service, startup PID/port lock, startup self-check asserts reported version == source.
- **BLOCKER-MEDIUM:** Denials/failures are not auto-emitted to event stream for observability.
  - Fix: log structured denial events (`auth_denied`, `validation_failed`) with request_id/path/reason to `events.jsonl`.

## Verdict
**PARTIAL PASS (NOT HARDENED)**
- Core store/search/health remains functional.
- Hardening acceptance fails due to idempotency mismatch handling + runtime contract drift + denial observability gap.

## Proof keys
- `store_id_primary`: `2f88f576-fa6d-4e89-87fd-7a411a9ab5e9`
- `event_id_manual_observability`: `cd85098e-4d5b-4cde-a1c0-2b96526da0dd`
- `idempotency_key_probe`: `qa-lenny-1760579202`
