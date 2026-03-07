# memU Research Update: Agent-Memory Approaches (2026-02-18)

## 1. Top 3 Improvements for memU
Based on a scan of recent OSS (Mem0, Letta/MemGPT, Zep/Graphiti):

1.  **Smart Context Filtering (Mem0-style):**
    *   *Concept:* Instead of dumping raw logs into context, use a lightweight vector store to retrieve only the top-k relevant memories for the current task.
    *   *Benefit:* Reduces token costs by ~90% and improves agent focus by removing noise.
    *   *Relevance:* High. Our current file-based `memU` is growing; we need retrieval, not just storage.

2.  **Git-Backed State (Letta's "Context Repositories"):**
    *   *Concept:* Treat memory updates as commits. Branch memory for experimental runs, revert on failure.
    *   *Benefit:* Safety and auditability.
    *   *Relevance:* Medium-High. We already use git, but could formalize "memory commits" to prevent bad data from polluting the main branch.

3.  **Temporal Knowledge Graphs (Zep's Graphiti):**
    *   *Concept:* Store memories as a graph (nodes/edges) with time awareness, allowing queries like "What happened *before* the API broke?"
    *   *Benefit:* Deep reasoning about causality.
    *   *Relevance:* High for debugging, but high complexity to implement.

## 2. Proposed Low-Risk Deploy: "Mem0-Lite" Retrieval Layer
**Goal:** Add a simple retrieval script to `memU` that finds relevant past logs without changing the underlying file storage.
**Why Low Risk:** It's a read-only addition (a new script) that indexes existing Markdown files. No data migration required.
**Measurable Proof:** Can we find specific past decisions (e.g., "token cost") without reading all files?

## 3. Proof of Concept Execution
I created and ran `memory/mem0_proof_of_concept.py` to demonstrate this retrieval capability.

**Proof Key:** `MEM0_LITE_POC_202602182131`
**Status:** SUCCESS
**Query:** "token cost reduction"
**Result:** Successfully retrieved Winnie's research note about Mem0 cost savings while ignoring unrelated trading logs.

**Next Step:** I recommend fully implementing a local embedding index (using `chromadb` or similar lightweight lib) over `memory/*.md` to power this permanently.
