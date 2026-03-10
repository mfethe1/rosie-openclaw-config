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
