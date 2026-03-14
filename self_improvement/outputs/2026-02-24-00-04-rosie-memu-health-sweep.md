# Rosie — memU Health Sweep (last 24h)

## Scope
- Time window checked: 2026-02-23 00:04 → 2026-02-24 00:04 EST
- Checks: route contract (local/bridge), smoke/eval evidence, API pattern parity, competitor pattern deltas

## Findings
1) **Route contract is bridge-only and stable**
- Active health endpoint: `GET /api/v1/memu/health` returns 200 and status=ok.
- Direct fallback route `GET /health` returns 404 (expected for current bridge contract).
- Last-24h eval entries show repeated bridge contract PASS usage.

2) **Smoke/eval posture is healthy in last 24h**
- `memory/eval-log.md` shows recent PASS proofs for memU-related tasks:
  - `97beb2de-8898-4266-be0e-4f2c5c035e74` (Rosie memU health sweep)
  - `f4bba949-b06b-4d2d-aac9-f4cbd17c2a8d` (Mack resilience)
  - `e24ed78d-6cc2-4849-9ffc-aed32d15314d` (Lenny QA hardening)
  - `ddc1a5e4-d0ce-4b68-8a11-17e0733f635d` (Sisyphus verify)
  - `dc82063f-06b8-4dc6-962f-e4495fbaebe1` (Winnie cron drift)

3) **Contract representation drift detected and corrected**
- Health payload previously advertised feature `fts` while implementation is currently LIKE+TFIDF based.
- **Fix applied:** health feature string updated to `like-and-tfidf-search`.

4) **Observability duplication detected and corrected**
- `memory/memu_server.log` had duplicate lines because logs were written by both FileHandler and shell redirection in `start.sh`.
- **Fix applied:** `memu_server/start.sh` now starts server with stdout/stderr to `/dev/null` (server.py remains source-of-truth logger).
- Post-fix verification: new store log entries are no longer duplicated.

5) **Implementation vs canonical API patterns (quick delta)**
- Canonical memory APIs (Mem0/Zep/LangMem patterns) typically expose:
  - clear versioned namespaces,
  - explicit CRUD/search semantics,
  - entity scoping (user/agent/session),
  - filterable query APIs,
  - predictable error schema.
- memU bridge strengths: versioned namespace, idempotent store, semantic search endpoint, health with storage stats.
- Remaining gaps vs common patterns: no explicit update/delete endpoints, no first-class filter object for search, limited standardized error envelope.

## Concrete next fixes (prioritized)
1. Add `GET /api/v1/memu/capabilities` static contract endpoint (route style, version, auth mode, feature flags).
2. Add optional compatibility aliases for direct contract (`/health`, `/store`, `/search`) returning deprecation headers.
3. Add structured error envelope for 4xx/5xx responses: `{error:{code,message,details,request_id}}`.
4. Add search filters (`agent_id`, `user_id`, `since`, `tags`, `limit`) to match mainstream memory API ergonomics.

## Proof snippets
- New verification store ID (this sweep): `8a2ec5d9-35fc-4f79-a014-9f9dbe8622e6`
- Prior sweep check ID: `7af263cd-110a-43a1-8342-97dc155bc227`
