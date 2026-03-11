# BACKLOG.md — Canonical Task Registry
**Last updated:** 2026-03-11
**Owner:** Rosie (Coordinator/QA)

## Active Assignments (Michael's Directive 2026-03-10)
- **Lenny**: Build the hybrid retrieval system (BM25 + vector similarity, vector reranking, query decomposition)
- **Macklemore**: Build temporal orchestration (Worker/task queue/namespace bootstrap, replay determinism) & canonical route/contract stability (/add vs /memories, X-API-Key primary)
- **Rosie (me)**: Deduplication (/api/v1/memu/dedupe cleanup path) and operational hygiene (secret/history periodic cleanup, proof-gated handoffs)
- **Winnie**: Cross-gateway coordination (Multi-gateway sync, event-driven JetStream architecture)

## In Progress
- [ ] Rosie: Implementing `/api/v1/memu/dedupe` and periodic secret/history cleanup.
- [ ] Macklemore: Updating `fumemory` repo and syncing temporal worker configurations.

## Michael's Directive (2026-03-10 13:03 EDT Follow-up)
- **Lenny Priority Update:**
  1. True Vector/HNSW implementation (native vector embeddings + HNSW indexing).
  2. Active Consolidation project (Context Commit - auto-compressing and consolidating redundant memories into singular nodes).

## Michael's Directive (2026-03-10 13:20 EDT Follow-up)
- **Swarm Re-allocation:**
  - Rosie and Winnie are shifting off their previous tasks (Dedupe/Hygiene and Cross-Gateway) to assist Macklemore.
  - **New Task (Rosie, Winnie, Mack):** Swarm on Temporal Orchestration (Worker/task queue/namespace bootstrap) + Canonical Route/Contract Stability (/add vs /memories).

## Michael's Directive (2026-03-10 13:47 EDT)
- **Phase Transition:** Wrap up current tasks (Temporal Orchestration & Vector/HNSW).
- **Testing:** Begin end-to-end testing of the whole system (Hybrid Retrieval + Temporal).
- **Deployment:** Ensure the system is ready to run on Railway for improved resiliency and redundancy.

## Michael's Directive (2026-03-10 15:06 EDT) - Agentic Frameworks & Tavily Intelligence API
- **Phase 1: Database & Infra**
  - [ ] **Lenny**: Design Supabase `intelligence_cache` table and telemetry/cost-tracking schema (record token/Tavily cost per run).
- **Phase 2: API & Monetization**
  - [ ] **Mack**: Build async job queue (Upstash/Redis or Railway worker), `/api/jobs` endpoints, and Stripe subscription logic in the `rare-agent-work` repo.
- **Phase 3: Pipeline & Testing**
  - [x] **Rosie**: Orchestrate the cache routing logic (Cache -> Tavily -> LLM). Execute 3-query test pipeline (Paper-to-Code Oracle) using Tavily to verify it correctly finds Arxiv and GitHub implementations. (Done)
  - [x] **Rosie**: Implement Layer 2 (GitHub code extraction) and Layer 3 (Claude 3.5 Sonnet processing) of the Paper-to-Code Oracle pipeline. (Done)
  - [ ] **Winnie**: Push the tasks to the GitHub repo issues, monitor test metrics, and summarize the validation results.

## Update (2026-03-10 17:45 EDT)
- **Codebase Merge & Tests**: Rosie resolved the remaining pytest failures (`test_notion_bridge.py`, `test_lane_lock_claim_integration.py`, and dependencies in `pyproject.toml`). All tests are passing locally.
- **Status**: The `main` branch of `fumemory` is 100% green with the hybrid retrieval, temporal orchestration, and dedupe hygiene features successfully integrated.
- **Next Step**: Execute `railway up` deployment once we have explicit approval to overwrite the production `memu-api` and Temporal clusters.

## Update (2026-03-10 18:15 EDT)
- **Deployment Status:** E2E integration tests continue to pass 100% green on `main`. 
- **Railway Infrastructure:** We have linked the local `fumemory` repo to the `fumemory-infra` project (production environment) using the CLI. 
- **Action Required:** We are waiting for the final green light to run the `railway up` deployment command.

## Michael's Directive (2026-03-10 18:18 EDT)
- **Deployment Authorized:** Execute the Railway deployment (`railway up`).
- **Coordination:** Rosie, coordinate over NATS with Lenny, Macklemore, and Winnie on the post-deployment next steps.

## Michael's Directive (2026-03-10 19:50 EDT)
- **Fix 1:** Upgrade search backend from TF-IDF to dense vector embeddings (fastembed/OpenAI).
- **Fix 2:** Migrate SQLite store (`memu.db`) to `pgvector` database to support vector queries.
- **Fix 3:** Deprecate `memory/*.md` file writes. Enforce `memu-proof-gate-protocol.md` (fail workflows without a memU ID).

## Michael's Directive (2026-03-10 19:52 EDT Follow-up)
- **Execution Order:** Wait for Macklemore to successfully push the current baseline to Railway production. Once Mack's deploy is green, Rosie, Lenny, and Winnie are to swarm on implementing the 3 fixes (Dense Vectors, pgvector migration, local .md deprecation).

## Swarm Update (2026-03-10 19:55 EDT)
- **Status:** Swarm is GO for the memU Modernization project.
- [x] **Rosie**: Updated policies (`AGENTS.md` and `context-memory-cost-policy.md`) to formally deprecate `memory/*.md` writes and enforce `memu-proof-gate-protocol.md`.
- [ ] **Winnie**: Build branch for `memu-proof-gate-protocol.md` automated enforcement.
- [ ] **Lenny**: Build branch for `fastembed`/OpenAI dense vector upgrades.
- [ ] **Rosie**: Build branch to migrate SQLite store (`memu.db`) to `pgvector` database.

## Michael's Directive (2026-03-11 08:18 EDT) - Construction Bid App Feature Initiative
- **Goal:** Execute estimate workflow upgrades on `construction-bid-app`. 
- **Branch:** `lenny/estimate-workflows`
- **Execution Order (per Michael):**
  - [x] 1. **EST-WF-01:** Spreadsheet-style verification tracking user name (Done)
  - [x] 2. **EST-WF-02:** Keyboard-first editing with tab/enter (Done)
  - [x] 3. **EST-WF-03:** Sort/filter by trade (Done)
  - [x] 4. **EST-WF-04:** PDF/CSV export (Done)
  - [x] 5. **EST-WF-05:** Gmail/Outlook draft flow (Done)
  - [x] 6. **EST-WF-06:** Change orders (Done)
  - [x] 7. **EST-WF-07:** GC-style scheduling (Done)
  - [x] 8. **EST-WF-08:** Receipt/invoice cost tracking (Done)
  - [x] 9. **EST-WF-09:** Estimate vs actual profit audit (Done)
  - [x] 10. **EST-WF-10:** Cadence vs schedule audit (Done)

## Michael's Directive (2026-03-11 09:14 EDT) - DeerFlow Performance Patterns Implementation
- **Goal:** Implement the three performance efficiency patterns identified from the DeerFlow v2.0 repository into our Gateway Swarm architecture.
- **Assignments:**
  - [ ] **Lenny**: **Progressive Skill Loading (Context Efficiency)** - Implement lazy-loading for tools/skills in worker loops to reduce context window size.
  - [ ] **Winnie**: **Strict Sub-Agent Context Isolation (Speed & Focus)** - Enforce shallow orchestration by stripping context bleed in NATS payload handoffs.
  - [ ] **Macklemore**: **Aggressive In-Flight Summarization** - Add a context-compression step to the `task_orchestrator.py` skill that summarizes outputs and stores raw logs separately in `outputs/`.

## Michael's Directive (2026-03-11 09:26 EDT) - Migration Fix (4096 Dims)
- **Goal:** Upgrade the pgvector column to support 4096 dimensions for modern models rather than downsampling to 384 dims.
- **Assignments:**
  - [ ] **Mack**: Update the migration script (e.g., `011_force_384_dims.sql`) to use `DROP COLUMN embedding CASCADE` to clear view dependencies, recreate it as `vector(4096)`, and recreate the `current_memories` view.
  - [ ] **Lenny**: Configure the `memu-api` service to natively accept 4096-dimensional embeddings.
  - [ ] **Winnie**: Investigate and fix the IPv6/IPv4 NATS connection failures.

## Michael's Directive (2026-03-11 10:15 EDT) - Long Lead / Supply Chain Risk Detection
- **Goal:** Add capability to the Construction Bid App agent to detect and flag long lead items and equipment (procurement delays > 8 weeks) that impact project schedule.
- **Assignments:**
  - [x] **Rosie**: Update the agent's estimate validation logic to scan for long lead items and proactively suggest early release packages, preordering, or schedule contingency.
  - [ ] **Mack**: Implement a supply chain/long lead database tool or API connector for the agent to use.

## Michael's Directive (2026-03-11 09:28 EDT) - Project Manager and Task Breakout
- **Goal:** Integrate the DeerFlow "Project Manager and Task Breakout" capability into our Gateway Swarm architecture for complex multi-step task planning.
- **Assignments:**
  - [x] **Rosie**: **Project Manager Integration** - Design and implement the Lead Agent planning phase (Project Manager) that breaks down ambiguous requests into sub-tasks.
  - [ ] **Mack**: **Task Breakout Implementation** - Create the NATS worker payload structures and routing to spawn parallel sub-agents for each broken-out task, then synthesize the results.

## Michael's Directive (2026-03-11 11:45 EDT) - Graphiti Memory Upgrade
- **Goal:** Integrate Graphiti memory upgrade (temporal knowledge-graph memory architecture) into `fumemory` and our memory system.
- **Assignments:**
  - [x] **Mack**: Integrate the Graphiti/Zep knowledge graph architecture into the `fumemory` temporal worker/queue orchestration. (Shipped via commit 44a74c9)
  - [x] **Lenny**: Handle backend `pgvector` filtered ANN tuning for the temporal knowledge-graph retrieval. (Shipped via commit d60a304)
  - [x] **Winnie**: Enforce the `memu-write-contract-guardrails` during Graphiti integration. (Shipped via commit d60a304)
  - [x] **Rosie**: Implement the `temporal-retrieval-lane` and verify end-to-end Graphiti memory operations. (Shipped via commit d60a304)