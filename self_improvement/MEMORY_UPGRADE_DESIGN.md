# memU Memory Architecture Upgrade Design
**Date:** 2026-02-18
**Owner:** Rosie (Coordinator)
**Objective:** Evolve memU from key-value + text search memory to a state-of-the-art tiered, vectorized, graph-aware, task-aware memory fabric competitive with Mem0, Letta/MemGPT, Zep, and Supermemory.

## 1) Research Findings (Non-Consensus / Beyond Vanilla Vector Search)

### A) Cognitive-inspired memory stack (beyond flat vector DB)
- Cognitive-memory literature increasingly frames agent memory as **multi-layer lifecycle** (encode → consolidate → retrieve → utilize), with explicit short/long-term roles and hippocampal-like replay/consolidation dynamics.
- Source: *AI Meets Brain: A Unified Survey on Memory Systems from Cognitive Neuroscience to Autonomous Agents* emphasizes lifecycle and mapping between biological short-term/long-term paradigms and agent systems.
  - https://arxiv.org/html/2512.23343v1

### B) Consolidation + replay concepts
- Brain-inspired work repeatedly points to **offline consolidation/replay** to prevent forgetting and improve integration across experiences.
- Key idea for systems: periodic asynchronous consolidation jobs can “compress & rebind” related recent memories.
- Sources:
  - *A model of autonomous interactions between hippocampus and neocortex driving sleep-dependent consolidation* (PNAS/PMC)
    - https://pmc.ncbi.nlm.nih.gov/articles/PMC9636926/
  - *Sleep-like unsupervised replay reduces catastrophic forgetting* (Nature/PMC)
    - https://pmc.ncbi.nlm.nih.gov/articles/PMC9755223/

### C) Temporal/knowledge-graph memory (clear non-vector breakthrough)
- Zep/Graphiti positions memory as **incremental temporal knowledge graph** with event time + ingestion time, entity conflict resolution, and low-latency retrieval without full recompute.
- Source: *Zep: A Temporal Knowledge Graph Architecture for Agent Memory* + Neo4j Graphiti notes on bi-temporal edges and real-time updates.
  - https://arxiv.org/abs/2501.13956
  - https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/

### D) Structured memory classes in production systems
- Mem0-style systems explicitly separate memory classes (conversation/session/user/org, episodic, semantic, procedural) and use both retrieval and update operations to prevent bloat.
- Source: Mem0 memory type docs.
  - https://docs.mem0.ai/core-concepts/memory-types

### E) Letta-style core/archival mechanics
- Letta’s architecture demonstrates a clear “context-pinned memory + archival memory + messages” split, with tool-based updates to memory blocks and explicit run/message persistence.
- Source: Letta memory docs.
  - https://docs.letta.com/guides/agents/memory/

### F) Supermemory implementation direction
- Supermemory docs describe a “memory + semantic understanding graph + temporal user profile + managed RAG” stack and explicitly frame vector retrieval and entity relationships together.
- Source: Supermemory docs.
  - https://supermemory.ai/docs/intro

## 2) Current memU baseline (as observed)

Current implementation already includes:
- `/store`, `/search`, `/semantic-search`
- optional sentence-transformers embeddings (`MEMU_EMBEDDING_MODEL`)
- dedup on store (`DEDUP_THRESHOLD`)
- `/consolidate` clustering and summary generation
- `/tasks` create/list/update workflow delegation primitives
- `/register-gateway`, `/gateways`, `/heartbeat`, `/gateways/{id}/memories`

Gaps vs target:
1. Tiering is not first-class (no explicit Core/Working/Long-term policy in API/models).
2. Consolidation exists but is batch/manual-like and not session-aware nor semantic-graph-aware.
3. Consolidation and dedup metadata are minimal and not policy-driven.
4. No knowledge graph entities/relationships layer.
5. Task delegation exists but lacks fairness/polling/lease semantics and completion history.
6. No structured retrieval ranking policy across tiers and memory classes.

## 3) Proposed Upgraded Architecture

### 3.1 Memory model

#### Three tiers
- **Core (always-in-context)**
  - Immutable or pinned memories for current system identity and active goals.
  - Small, high-priority set; injected into every request.
  - Stored with `tier="core"`, `pin=true`, TTL/retention policy managed.

- **Working (session)**
  - TTL-scoped memory for active thread/job and intermediate artifacts.
  - Auto-created from session ID + recent tool outputs.
  - Expires on session close / inactivity threshold.

- **Long-Term (archival)**
  - Consolidated, semantic + episodic + procedural + profile memory.
  - Can be consolidated into higher-level summaries and entities.
  - Candidate source for search with stronger decay/recency weighting.

#### Memory types (orthogonal)
- **Episodic:** eventful user/agent interactions, task outcomes.
- **Semantic:** facts, preferences, concepts, rules, entities/properties.
- **Procedural:** how-to patterns, runbook steps, playbooks.
- **Task-memory:** pending/claimed/done assignments and handoff state.

#### Storage strategy
- Keep JSON-backed baseline for now (minimal dependency), with clear migration to SQLite/Postgres for production.
- Add two stores:
  1. `memu_service.memories` (document records, embeddings optional)
  2. `memu_service.memory_graph` (nodes/edges + timestamps)

### 3.2 Semantic dedup strategy

Use hybrid duplicate check in `/store`:
1. Lexical + hash dedup (exact/near-exact fast path).
2. Vector similarity (embedding cosine) threshold candidate matching.
3. LLM merge summarizer (optional API) when semantic similarity is high but semantics diverge.
4. Keep `merge_group_id`, `merge_score`, and `provenance` in metadata.

Fallback policy:
- If embedding unavailable, degrade to lexical + metadata dedup.
- Never auto-delete originals; consolidate by creating linked summary + provenance.

### 3.3 Consolidation pipeline

Add periodic jobs (cron/callback):
- **Hourly light pass** on working/long-term:
  - dedupe cleanup, stale candidate pruning, TTL cleanup.
- **Daily deep pass**:
  - clustering by semantic + temporal proximity + agent context.
  - generate `summary_id` records, move source records to `archived=true` if confidence > threshold.
  - update entity graph with extracted relations.
- **Replay pass** (inspired by hippocampal replay):
  - sample high-salience older memories not accessed recently,
  - rerank into “reconstruction context” and re-run extractor for missed links/contradictions.

### 3.4 Task delegation via memory

Define canonical task contract:
- `task_id`, `type`, `title`, `description`, `priority`, `status{pending|claimed|in_progress|done|blocked}`, `assignee`, `owner`, `created_at`, `claimed_by`, `claimed_at`, `heartbeat_at`, `result_summary`, `proof`.

Add endpoints:
- `GET /tasks/poll?agent=<id>&limit=<n>`: return oldest pending tasks with optional affinity tags.
- `POST /tasks/{id}/claim`: atomic claim with TTL lease.
- `POST /tasks/{id}/heartbeat`: keep claim alive.
- `POST /tasks/{id}/result`: close + provenance.

### 3.5 Faster embedding search

- Use sentence-transformers locally by default (`all-MiniLM-L6-v2`), with optional fallback to API-based embedding providers (OpenAI/Gemini/Voyage) to avoid Ollama.
- ANN index later optional (FAISS/HNSW in SQLite extension / Postgres pgvector) when >10k records.
- Query routing:
  1. Core and task queries bypass ANN.
  2. Working-memory search uses vector+recency.
  3. Long-term search uses vector + type filter + consolidation score.

### 3.6 Knowledge graph layer

Introduce entity-relation graph as first-class projection:
- **Node:** entity (`type`, `name`, `canonical_id`, `aliases`, `facts`, `state`)
- **Edge:** relation (`predicate`, `source`, `target`, `confidence`, `valid_from`, `valid_to`, `source_mem_id`)
- **Bi-temporal fields:** `event_time` + `ingested_at`.
- Graph updated asynchronously from store/consolidation stages.
- Retrieval query returns both:
  - direct semantic hits and
  - graph expansions to 1–2 hops for causal/entity context.

## 4) Proposed API Surface (v1.2+)

- `POST /store` (enhanced): `tier`, `memory_type`, `entity_refs`, `consolidation_group`, dedup policy options.
- `POST /search` remains for legacy keyword matching.
- `POST /semantic-search` enhanced with `scopes`, `include_archived`, per-tier boosts.
- `POST /consolidate` extended with `strategy={semantic|graph|time}` and `dry_run`.
- `GET /graph/search?query=...` and `GET /graph/entity/{id}`
- `POST /tasks/poll`, `POST /tasks/{id}/claim`, `POST /tasks/{id}/heartbeat`, `POST /tasks/{id}/result`

## 5) Data model and ranking policy

Priority score example:
```
score = α·embedding_similarity + β·recency + γ·access_frequency + δ·tier_weight + ε·confidence + ζ·task_relevance
```
- Core tier has highest `tier_weight` and is always returned first.
- Working tier limited by session window and recency.
- Long-term filtered by decay score and summary confidence.

## 6) Implementation Phases (quick execution)

### Phase 0 (Rosie / current)
- Finalize schema + policy
- Add design doc + memory log update

### Phase 1 (Mack)
- Harden `/store`, `/search`, `/semantic-search` with explicit tiers, dedup metadata, ranking policy.
- Add task poll/claim endpoints.

### Phase 2 (Winnie)
- Graph projection service: extract entities/edges from new/updated memories.
- Implement bi-temporal edge validity and conflict invalidation.

### Phase 3 (Lenny)
- Add scheduled consolidation + replay job; add metrics and smoke tests.
- Verify correctness: no data loss, deterministic dedup, task lifecycle integrity.

## 7) Risks / mitigations

- **Over-consolidation:** use confidence gates + dry-run and source references.
- **Embedding drift:** pin model and keep per-model namespace.
- **Schema drift:** strict pydantic models and migration tests.
- **Task leakage:** claim lease + heartbeat timeout + ownership guard.
- **Noisy KG relations:** confidence threshold + decay + overwrite policy.

## 8) Decision summary

Adopt a **hybrid architecture**: vector retrieval + temporal knowledge graph + consolidation scheduler + explicit memory tiers + explicit task queue. This is materially stronger than pure vector DB patterns, aligns with current memU feature direction, and matches the capabilities of Mem0/Letta/Zep-level systems.

## 9) Findings summary payload for memU

```text
- Existing memU already has semantic search, dedup, consolidate, and tasks.
- Research indicates strongest next upgrades: tiered memory lifecycle, temporal KG layer, replay-like consolidation, and task queue lease semantics.
- Recommended next step: treat tasks as first-class memory citizens with poll/claim/heartbeat semantics.
- Embeddings: use sentence-transformers locally; avoid Ollama.
- Target architecture: Core + Working + Long-term with semantic + graph retrieval union.
```