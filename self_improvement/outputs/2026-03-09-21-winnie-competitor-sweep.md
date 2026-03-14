# Winnie Competitor Sweep (March 9, 2026 - 21:00 EST)

## 1. Executive Summary
Scanned latest 2026 updates in agent memory frameworks including Mem0, Letta (MemGPT), and Zep. The core trend is a move toward explicit architectural tiering and temporal awareness, prioritizing efficient context over raw vector search.

## 2. Top 3 Architectural Improvements
1. **Tiered/Hierarchical Memory (Letta, Mem0):** Separating 'core' (always-available), 'recall' (conversation history), and 'archival' (long-term) storage. This prevents critical facts from being lost in semantic search chunks and improves accuracy by bounding context.
2. **Temporal Knowledge Graphs (Zep):** Building evolving entity graphs that automatically invalidate outdated facts over time. 
3. **Hybrid Vector + Graph Stores with Compression:** Adaptive compression prior to storage combined with graph traversal, yielding 80-90% token savings while maintaining high recall.

## 3. Low-Risk Deploy Proposal for memU
**Proposal: Adopt Letta-style Tiered Memory (Core vs Recall)**
*Why:* We currently treat all stored memories equally via FTS5/Vector search. Critical operational facts can be lost if they don't semantically match the current query.
*Implementation:* 
1. Add a `tier` column (`core`, `recall`, `archival`) to `agent-memory.db` (default `recall`).
2. Update `agent_memory_cli.py search` to ALWAYS append non-expired `tier='core'` memories as a separate top-level context block, regardless of semantic match.
*Proof ID:* `122` (Stored via agent_memory_cli.py)

## 4. Next Actions for TODO.md
- **[Mack]** P2-HIGH — D-036: Implement Tiered Memory (Core vs Recall) in `agent-memory.db`. Add `tier` column and update `agent_memory_cli.py search` to always return `core` memories unconditionally.
