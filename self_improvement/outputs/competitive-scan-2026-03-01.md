# Weekly Competitive Intelligence Scan — 2026-03-01

## Scope
Scan target: new agent frameworks and memory systems (weekly window emphasis).

Queries executed:
1. `agent memory framework site:github.com 2026`
2. `multi-agent self-improving LLM 2026`
3. `autonomous agent memory arxiv 2026`
4. `LLM agent tool new framework released`

Additional freshness check:
- `agent framework released GitHub memory multi-agent` (`freshness=pw`)

## HIGH-VALUE Findings

### 1) U-Mem: Towards Autonomous Memory Agents (NEW this week)
- Source: https://arxiv.org/abs/2602.22406
- Signal: Submitted 2026-02-25 (within week)
- Why high value:
  - Moves memory from passive logging to active acquisition + validation.
  - Introduces cost-aware escalation (cheap signals -> tool verification -> expert fallback).
  - Reports notable gains on HotpotQA/AIME25 in abstract.
- Relevance to our stack:
  - Directly addresses current gap: memU lacks uncertainty-triggered acquisition policy.
  - Aligns with our need for higher-quality long-horizon memory without full retraining.
- Estimated implementation effort: MEDIUM

### 2) AMA-Bench: Evaluating Long-Horizon Memory for Agentic Applications (NEW this week)
- Source: https://arxiv.org/html/2602.22769v1
- Signal: surfaced as 3 days old in search results
- Why high value:
  - Targets memory processing + retrieval as explicit benchmark requirements.
  - Useful for objective quality gating beyond smoke test pass/fail.
- Relevance to our stack:
  - Can become a benchmark extension for weekly memory QA.
- Estimated implementation effort: LOW-MEDIUM

### 3) MemoryAgentBench (ICLR 2026 accepted)
- Source: https://github.com/HUST-AI-HYZ/MemoryAgentBench
- Signal: Jan 26, 2026 ICLR acceptance note; active benchmark repo
- Why high value:
  - Practical 4-axis evaluation: Accurate Retrieval, Test-Time Learning, Long-Range Understanding, Conflict Resolution.
  - Designed for incremental multi-turn interactions (close to real assistant use).
- Relevance to our stack:
  - We can map these 4 axes to recurring SI benchmark outputs.
- Estimated implementation effort: LOW

### 4) DeerFlow 2.0 (major rewrite + trending momentum)
- Source: https://github.com/bytedance/deer-flow
- Signal: README cites Feb 28, 2026 milestone and 2.0 ground-up rewrite
- Why high value:
  - Production-minded super-agent harness patterns (subagents, memory, sandbox, skills).
  - Useful architecture reference for orchestrated agent runtime design.
- Relevance to our stack:
  - Pattern mining candidate for OpenClaw orchestration hardening and sandbox workflows.
- Estimated implementation effort: MEDIUM

### 5) Microsoft Agent Framework reaches RC (Feb 19, 2026)
- Source: https://devblogs.microsoft.com/foundry/microsoft-agent-framework-reaches-release-candidate/
- Why high value:
  - RC suggests API stabilization near GA.
  - Explicit support for graph workflows + standards (A2A, AG-UI, MCP).
- Relevance to our stack:
  - Interop patterns worth tracking for future cross-framework compatibility.
- Estimated implementation effort: LOW

## CRITICAL Assessment
Critical finding identified: **U-Mem pattern** is directly applicable and currently missing in our architecture (active memory acquisition under uncertainty with cost-aware escalation).

Action taken:
- Added proposal **P-006 — Active Memory Acquisition Loop (U-Mem Cherry-Pick)** to `self_improvement/PROPOSALS.md`.

## Non-selected / Lower-confidence signals
- Aggregator “awesome lists” and broad surveys were used as discovery leads only; not treated as primary evidence for implementation decisions.
- Several “framework ranking”/news pages lacked technical depth or primary-source detail.

## File updates completed
- Updated `self_improvement/TODO.md` with new entries under **Research Backlog**.
- Updated `self_improvement/PROPOSALS.md` with **P-006**.

## Notes
- This week yielded both immediate tactical ideas (U-Mem loop) and benchmark opportunities (AMA-Bench, MemoryAgentBench) that improve decision quality before deeper implementation.
