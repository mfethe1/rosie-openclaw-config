# MEMORY_QA_LENNY — memU Audit + Resilience Review

**Date:** 2026-02-18
**Agent:** lenny
**Target:** memU API Server on `127.0.0.1:12345`

## 1) Endpoint audit results

### Base checks
- `GET /health` returns 200 and service info.
- `POST /store`, `POST /search`, `GET /gateways`, `POST /heartbeat`, `POST /register-gateway` all responded as expected.
- This server runs independently from legacy `memu_server` (port `8711`, `/api/v1/memu/*`).

### Test outcomes (key results)

| Endpoint | Input | Result | Notes |
|---|---|---|---|
| `/health` | GET | 200 | Returns `{status: healthy, timestamp, store_entries, llm_configured, embeddings_enabled}` |
| `/register-gateway` | Valid new gateway | 200 | Action=`registered` |
| `/register-gateway` | Same gateway again | 200 | Action=`updated`, no error |
| `/heartbeat` | Registered gateway | 200 | Updates `last_heartbeat` |
| `/heartbeat` | Unregistered gateway | 404 | Properly rejected |
| `/gateways` | GET | 200 | Returns list + count |
| `/store` | standard payload | 200 | Creates entry | 
| `/store` | duplicate key/value (same payload) | 200 | New record created (no dedup on exact duplicate) |
| `/search` | `{"query":""}` | **200** (BUG) | Returns many matches because empty string matches everything |
| `/search` | normal query | 200 | Correct text matches returned |
| `/store` | 2MB value payload | 200 | Succeeded (no size guard observed in this test) |
| concurrent `/store` | 20 parallel requests | all 200 | No immediate errors, lock likely working |
| concurrent same-key | 10 parallel writes with same key+dedup default | mixed new records | dedup not effective when embedding pipeline unavailable |

### Input validation edge cases
- `/store` requires both `key` and `value` in schema (Pydantic), but empty strings are accepted (`key=""` / `value=""` would pass if provided).
- `/search` requires `query` field type string but does **not** reject empty `query` (`""` is accepted and behaves like wildcard).
- Duplicate suppression currently depends on optional embedding dedup only.

## 2) Failures / risks found

1. **Search semantics bug (high):** empty query should be treated as invalid or explicit empty-result policy, but currently returns all memories.
2. **Duplicate handling gap:** duplicate writes are not blocked by key; only semantic dedup via embeddings (currently often disabled when embeddings unavailable).
3. **Durability weak:** `store.json` is rewritten directly; crash during write can produce partial/corrupted JSON and cause data loss.
4. **No durability audit artifacts:** no write-ahead log (WAL), no snapshot/compaction metadata, no checksums.
5. **No retention/decay policy:** no TTL or automatic stale-data cleanup.
6. **No consistency semantics for concurrent gateway writers across processes/instances:** single in-process `threading.Lock` only.
7. **No alerting path:** service does not emit health alerts for stale gateways, WAL bloat, corrupted files, or recovery events.

## 3) Reliability patterns researched

- **Write-ahead logging / WAL semantics**: append-only log before state mutation provides crash-safe durability and recovery replay; SQLite WAL docs emphasize committed writes are appended first, enabling consistent recovery and checkpoint flow.
- **Memory consistency / distributed writes**: agentic systems literature stresses explicit consistency model (versioning, serialization, CRDT-style reasoning) and lock/transaction semantics when multiple writers update shared memory.
- **Memory corruption prevention**: OWASP-aligned guidance for agentic AI repeatedly calls for provenance + validation at write-time to reduce memory poisoning risk.
- **Garbage collection / stale data**: modern managed memory systems use TTL + periodic cleanup/compaction.
- **Decay/forgetting**: Ebbinghaus-style exponential decay + access reinforcement is a standard pattern for freshness modeling.

## 4) Proposed resilience design (for Mack to implement)

### A) Write-ahead logging + atomic state files
- Add append-only `wal.log` with entries:
  - `op`: `STORE`, `REGISTER_GATEWAY`, `HEARTBEAT`, `MERGE`, `ARCHIVE`
  - `op_id` (uuid), `ts`, `actor` (`gateway_id`), `payload` (compact, validated), `prev_crc`.
- For each operation:
  1. append + fsync WAL
  2. apply to in-memory snapshot
  3. atomically persist checkpoint file via temp + rename (`store.json.tmp` -> `store.json`)
- On startup: validate WAL tail, replay uncheckpointed ops.
- Add checksum manifest for checkpoint + WAL segments for corruption detection.

### B) TTL / expiration for stale memories
- Add fields: `created_at`, `last_accessed_at`, `access_count`, `importance` (0..1), `critical` bool.
- Per-entry `ttl_days` (default maybe 30–90); if expired => mark for deletion on sweep.
- `critical==true` entries bypass TTL.

### C) Backup/snapshot mechanism
- Nightly snapshot to timestamped JSONL/Compressed file.
- Keep rolling window (e.g., 14 days) and compact stale/deleted entries during snapshot.
- Store snapshot hash + file index in manifest.

### D) Health monitoring and alerting
- Extend `/health` with indicators:
  - `wal_pending_entries`, `wal_size_bytes`, `snapshot_age_seconds`, `last_checkpoint_at`, `stale_gateway_count`.
- Add background scheduler thread:
  - alert if gateway heartbeat stale > threshold
  - alert if WAL above size threshold
  - alert if JSON corruption checksum mismatch or recovery replay needed

### E) Multi-gateway write consistency
- Add optimistic concurrency metadata:
  - `version` / monotonic `updated_at` + `vector_clock` (or Lamport counter per gateway)
  - `request_id` for idempotency and duplicate suppression by gateway.
- Resolve conflicts deterministic by `updated_at` + `gateway_id` tiebreaker.
- Optional: move to SQLite/Redis with proper transaction isolation for stronger safety.

## 5) Relevance scoring system (decay + importance)

Suggested score for non-critical memories:
- Let `age_hours = (now - last_accessed_at)`
- `recency = 0.5 ** (age_hours / H)` where `H` is half-life in hours
- `frequency = log1p(access_count) / log1p(freq_cap)`
- `importance = clamp(importance_weight, 0..1)`
- `never_access_penalty = 1 if access_count>0 else 0.2`
- `score = never_access_penalty * (0.6*recency + 0.4*frequency) * (0.5 + 0.5*importance)`

Critical rule:
- If `critical=True` OR tag contains `important`, set `decay_multiplier=1.0` (no decay) and optionally force score floor.

Use score for ranking in `/search` and for archive/eviction prioritization.

## 6) Suggested immediate fixes (priority)
1. Reject empty `/search` query with 400 and add explicit empty-result option.
2. Add size/length guards for `key/value` and strict non-empty string validation.
3. Introduce WAL + atomic checkpointing before changing to crash-safe writes.
4. Add TTL + periodic cleanup + backup snapshot job.
5. Add gateway liveness monitor + stale alert path.
6. Add conflict policy + idempotency token for writes from gateways.

## 7) Verification summary for Mack handoff
- Existing requested endpoints appear functional but with noted correctness gaps (especially empty query, duplicate semantics under dedup-disabled mode, crash safety).
- No failures in basic concurrency for moderate request volume.
- Recommend regression tests for: malformed inputs, WAL replay simulation, duplicate idempotent writes, stale gateway eviction, snapshot restore, and multi-writer ordering.
