# BACKLOG.md — Canonical Task Registry
**Last updated:** 2026-03-10
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
