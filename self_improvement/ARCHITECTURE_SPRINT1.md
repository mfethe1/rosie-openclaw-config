# Multi-Gateway Architecture Sprint 1
Date: 2026-03-01 | Source: Michael's directive

## EPIC 3: Security, Consensus & Verification (Owner: ROSIE)

### F5 & UB3: Cross-Agent Self-Verification Gate & BCCS
- Actor-Critic pipeline via NATS pub/sub
- Critic sub-agents evaluate output with confidence float (0.0-1.0)
- BCCS Logic: >0.8 commits, 0.5-0.79 debate round, <0.5 rejects

### UB9: Security Hardening
- Docker: USER nonroot, --cap-drop=ALL, --security-opt=no-new-privileges
- AST static analyzer for ClawHub skill audits (block os.system, subprocess)

### UB7: MetaGPT SOP Encoding
- Convert verbose Markdown SOPs → DSPy-style XML state machines
- Reduce communication overhead, standardize rule enforcement

## Sub-Agent Dispensation Protocol
1. Decompose: JSON Schema for code needed
2. Deduce: Model tier (haiku/sonnet/opus)
3. Distribute: spawn sub-agent with context URIs
4. Reap: collect artifact, PR review

## My Sub-Agents
- Sub-Rosie-Warden (Sonnet): Docker hardening + AST skill analyzer
- Sub-Rosie-Judge (Opus): Actor-Critic + BCCS math
- Sub-Rosie-PromptEng (Sonnet): SOP → XML state machines
