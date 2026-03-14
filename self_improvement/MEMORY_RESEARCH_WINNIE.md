# Memory Research Findings (Winnie) — 2026-02-18

## Scope
- Task: benchmark/compare memory patterns for AI agents and find non-obvious upgrades to beat Supermemory.
- Sources used: web_search + web_fetch only (no Ollama usage).
- Focus areas:
  1) Supermemory vs Mem0
  2) Non-consensus memory methods (forgetting/consolidation/temporal)
  3) Fast retrieval/indexing methods
  4) Task delegation through shared-memory architectures (blackboard/tuple spaces)

---

## 1) Supermemory research (what they do, what seems stealable)

### Supermemory stated architecture (from official docs)
- **Knowledge-graph-first memory model**, not plain doc storage.
- Distinguishes **documents** (raw input) from **memories** (atomic semantic chunks). 
- Core pipeline: **queued -> extract -> chunk -> embed -> index -> searchable memory graph**.
- Uses explicit relation types: **update / extends / derives** (knowledge evolution and inference).
- Adds **forgetful/decaying** behavior and layered memory tiers in their public writeup.
- Claims sub-400ms latency and scaling focus, with memory routing/integration products layered above base store.

### Supermemory research page claims
- Introduces temporal metadata and dual timestamps (`documentDate`, `eventDate`) in relation to multi-session temporal reasoning.
- Mentions benchmarked gains on LongMemEval
a suite and describes their method as **chunked semantic memories + atomic relation+versioning** to improve recall over raw chunk retrieval.

### What “stealable” implies
- Supermemory’s differentiators are mostly **pipeline maturity and productization** (graph relations + graph updates + query rewrite + metadata routing).
- To beat them, need a combination of: **better temporal semantics + adaptive decay + task-coupled consolidation + deterministic task orchestration**.

---

## 2) Supermemory vs Mem0 (competition surface)

### Supermemory narrative
- “Memory engine” framing (ingest -> relate/infer -> retrieve -> route) vs “CRUD-like store” framing.
- Public comparison claims emphasize:
  - lower latency under load,
  - better connector/import behavior,
  - stronger versioning/relationship logic,
  - stronger recall in some anecdotal comparisons.

### Mem0 from paper + product page
- `arXiv:2504.19413` and `mem0` materials indicate: **extract -> consolidation/update -> retrieval** with graph-memory option.
- Mem0 reports good benchmark gains (e.g., large relative uplift on Locomo and much lower latency/cost than full-context approaches).
- Their own framing is still **operationally explicit memory records + graph augmentations**, i.e., strong control but still mainly retrieval-focused.

### Synthesis
- **Common ground:** both are converging on triad: extraction, consolidation, retrieval.
- **Differentiator today:** architecture depth around temporal reasoning, conflict handling, and task-level memory orchestration.
- **Beating target:** add mechanisms not yet standard in either stack:
  1) temporal-hierarchical memory trees,
  2) adaptive decay by relevance/usage + replay budgets,
  3) graph-aware task provenance and delegation cues in memory items,
  4) strict atomic task claiming/consumption to avoid coordination races.

---

## 3) Non-consensus / unconventional approaches (high upside for us)

### 3.1. Memory dynamics over static retention
- Survey literature framing `forms/functions/dynamics` shows memory as a **lifecycle** (formation, evolution, retrieval), not a static store.
- Most teams still over-invest in “better indexing” and under-invest in **dynamic pruning/refresh/rewrite loops**.

### 3.2. Biologically inspired forgetting (important edge)
- `FadeMem` (arXiv 2601.18642) introduces:
  - dual-layer memory hierarchy with **adaptive exponential decay**,
  - importance-weighted decay rates,
  - **memory consolidation/fusion** + conflict resolution,
  - measured storage reduction with improved multi-hop retrieval.
- This is explicitly “forget by design,” a strong edge over simple TTL or global relevance ranking.

### 3.3. Temporal-hierarchical memory trees
- `TiMem` (Temporal-Hierarchical) adds explicit tree over time:
  - lower nodes keep episodic detail,
  - higher nodes store consolidated abstractions/profiles,
  - recall planner chooses level by query complexity.
- Huge opportunity: **query-aware granularity retrieval** (cheap coarse memory first, then drill-down) reduces context load and latency.

### 3.4. Temporal knowledge-graph engines (Zep Graphiti)
- `Zep` paper-style approach introduces **bi-temporal graph memory**:
  - separate episodic + semantic structures,
  - explicit event and transactional timelines,
  - relationship edges with validity windows.
- This solves “stale facts vs latest facts” better than generic semantic graphs.

### 3.5. Task-specific memory types in practice
- Many systems still mix facts, preferences, procedures, and events in one score.
- Stronger pattern: explicit memory type + provenance tags (`semantic / episodic / procedural / task-state / conflict-state`) used by planners and judges, not just retrieval ranking.

**Novel/low-adoption insight:** Most systems still treat memory update as ingestion + similarity search. A better frontier: **memory as a control-plane artifact** (feeds scheduling, delegation, and planning) in addition to retrieval.

---

## 4) Fastest memory retrieval / indexing insights

### ANN indexing patterns to prioritize
- **Faiss** remains the standard baseline for ANN + vector compression:
  - options across `IVF`, `PQ`, `HNSW`, and `IMI`; strong Python ecosystem.
  - official benchmarks repeatedly show classic tradeoff: `HNSW` can win precision/latency at higher memory cost.
- `cagra/ivf` GPU acceleration (cuVS) reports substantial gains at equal recall (published benchmark style): up to **~8x lower latency**, **~12x faster build** in their examples, better throughput.
- For 1M-scale benchmark excerpts, Faiss shows:
  - brute-force exact indices dominate only at lower load/short-circuit contexts,
  - approximate methods dominate practical ANN when latency is king,
  - quantized variants (`PQ`, `PQfs`) materially cut memory with accuracy tradeoffs.

### Hybrid search (BM25 + vector)
- Weaviate-style hybrid search guidance:
  - BM25 is strong for exact tokens/IDs/
    lexical constraints;
  - dense vectors are strong for intent/semantic matching;
  - combine via **parallel retrieval + rank fusion** (e.g., RRF).
- Practical edge for agent memory: retrieval quality on mixed query styles improves dramatically vs vector-only.

### Hybrid strategy recommendations
- For our memory query path, use **two-tier retrieval**:
  1) lexical sparse recall for deterministic constraints,
  2) semantic ANN for semantic expansion,
  3) late fusion re-ranker using freshness/conflict/state signals.

---

## 5) Task delegation through memory systems (shared-memory coordination)

### Blackboard pattern (practical for agent teams)
- Classic blackboard design: shared workspace, specialist modules, control shell. Modern papers on `bMAS` indicate:
  - agents post to public board + select based on current board state,
  - iterative rounds until consensus/reasoned completion,
  - better for ill-structured tasks where fixed workflows fail.
- Key benefit: low coupling and runtime role re-selection.

### Tuple-space / Linda style as a coordination substrate
- Tuple-space model still highly relevant for AI agent coordination:
  - producer/consumer decoupling by content pattern,
  - associative read/write semantics,
  - atomic consume semantics (in Linda-style systems `in`/`rd`/`out`/`eval`).
- This maps directly to modern AI orchestration pain points (task claiming, race avoidance, durable delegation logs).

### Strongly novel insight for Winnie tasks (for Michael)
- Most teams run task queues as plain queues + polls.
- Better: **atomic task claiming + typed tuple patterns + scoped memory spaces**:
  - `in()`-style atomic claim for single-consumer pickup,
  - private/public board separation for sensitive/competitive paths,
  - event subscriptions instead of polling loops where possible.
- This gives concurrency safety + reproducibility in multi-agent systems.

---

## 6) Actionable upgrade ideas to compete with Supermemory

1. Implement **temporal-hierarchical recall**:
   - maintain memory at multiple abstraction levels,
   - query planner chooses recall granularity by complexity.

2. Implement **decay+fusion memory**:
   - adaptive forgetting function by importance, frequency, recency,
   - periodic memory consolidation into canonical/merged facts,
   - conflict-aware merge/update with explicit staleness semantics.

3. Add **bi-temporal validity**:
   - capture both event-time and ingest-time,
   - prioritize “newest valid” facts while preserving historical trail.

4. Add **task-aware memory schema**:
   - every memory record includes `task_id`, `agent_role`, `confidence`, `state`, `ttl_policy`.
   - retrieval scoring incorporates planning relevance.

5. Add **atomic delegation tuple-space layer**:
   - tasks are claims not just queue entries,
   - `claim/read/update` operations are atomic/logged,
   - board partitions (shared, team, private) + event notifications.

6. Use **hybrid retrieval for every memory read**:
   - vector + BM25 in parallel,
   - late fusion with freshness/conflict penalties and task context boosts.

7. Evaluate with **LongMemEval / LoCoMo / LongMemEval-S** and custom planner benchmarks, including update-correctness + concurrency correctness.

---

## 7) Notes on uncertainty / source quality
- Some vendor pages are marketing-forward (Supermemory/Scira/LogRocket).
- Higher-confidence technical claims were cross-checked with arXiv/faiss/wiki and independent ANN references.
- No local Ollama dependency was used or introduced.
