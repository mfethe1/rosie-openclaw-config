# Unified Memory System Implementation Track

This track consolidates the core memory system improvement proposals into a unified execution path.

## 1. Graph-Lite Entity/Relationship Tagging
- Implement `relationships` arrays on all memU objects.
- Ensure the memu-proof-gate-protocol requires the `relationships` arrays when storing execution context, decisions, and outcomes.
- Enable semantic traversal of entity connections via the graph structure.

## 2. Temporal Tracking
- Standardize timeline and timestamp fields for memories to enable time-based querying.
- Support expiring tactical memories vs long-term durable knowledge.

## 3. Eval Harness
- Build an automated evaluation suite to benchmark recall accuracy, response time, and relationship retrieval completeness.
- Gate production changes based on eval harness pass rates.

## 4. pgvector Tuning
- Optimize database indices for cosine similarity search over embeddings.
- Implement HNSW (Hierarchical Navigable Small World) indexes on the embedding column for scalable performance.
- Tune memory allocation and parallel worker counts in PostgreSQL for vector operations.
