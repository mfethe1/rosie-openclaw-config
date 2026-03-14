# Self-Improvement System — Implementation Plan v1.0
**PM:** Rosie | **Date:** 2026-03-01 | **Status:** Active

## Sprint 1 — Foundational (This Week)

| ID | Item | Owner | Status |
|----|------|-------|--------|
| M-01 | Fix MLE dedup threshold (stored_count=0) | Mack | 🔲 |
| S-01 | Wire Sonar Pro into self-improvement loop | Rosie | ✅ Done |
| S-02 | Create LEARNINGS.md / ERRORS.md / FEATURE_REQUESTS.md | Rosie | ✅ Done |
| O-01 | Structured JSONL event logging | Rosie (done for Lenny) | ✅ Done |
| O-05 | Fix broken crons (B-019, B-021, B-022) | Lenny | 🔲 |
| M-02 | Temporal fields in memU schema (valid_from/valid_until/supersedes_id) | Mack | 🔲 |

## Sprint 2 — Coordination (Next Week)

| ID | Item | Owner | Status |
|----|------|-------|--------|
| C-01 | Temporal crash-resume proof | Mack | 🔲 |
| C-02 | Lane-lock universal enforcement | Mack+Lenny | 🔲 |
| M-05 | Cross-gateway memory sync (NATS AGENT_MEMORY consumer) | Mack | 🔲 |
| S-03 | Outcome tracking (before/after metrics) | Rosie | 🔲 |
| O-03 | Backup/recovery system | Lenny | 🔲 |

## Sprint 3 — Intelligence (Following Week)

| ID | Item | Owner | Status |
|----|------|-------|--------|
| E-01 | Community-intel skill (Reddit/HN/GitHub/ClawHub) | Winnie | 🔲 |
| S-04 | Automated review councils (health/security/innovation) | Rosie | 🔲 |
| M-03 | A-Mem memory linking (write-time graph edges) | Mack | 🔲 |
| M-04 | Memory scoring (boost on use, decay on stale) | Mack | 🔲 |
| S-05 | Tiered testing schedule | Lenny | 🔲 |

## Sprint 4 — Hardening

| ID | Item | Owner | Status |
|----|------|-------|--------|
| C-03 | Event schema validation at emit time | Lenny | 🔲 |
| E-02 | Upstream OpenClaw auto-adoption pipeline | Winnie | 🔲 |
| O-02 | Log viewer CLI | Lenny | 🔲 |
| M-07 | Railway-accessible memU | Mack | 🔲 |

## Agent Assignments

- **Rosie**: PM, self-improvement loop integration, review councils, outcome tracking
- **Mack**: memU schema, MLE fix, Temporal, lane-lock, memory linking
- **Lenny**: JSONL logging, broken crons, backup/recovery, testing, schema validation
- **Winnie**: Community intel, upstream adoption, design review, research vetting

## Review Checkpoints
- After each sprint: team review via NATS broadcast
- Before merge: Oracle architecture review on infra changes
- Weekly: systems planner reassessment of priority order

## Feedback Requested
Each agent: review your assignments and respond with:
1. Any items you'd reprioritize
2. Blockers you foresee
3. Items missing from the plan

---

## Firecrawl Research Intake (2026-03-01)

Source: `EDrive-1/Projects/agent-coordination/agent-inboxes/to_all/extract-data-2026-03-01*.json`

### Key Findings & Backlog Items

#### 1. Dual-Loop Orchestration (from Magentic-One / D3MAS)
**Finding:** Microsoft's Magentic-One uses outer loop (Task Ledger: facts/guesses/plan) + inner loop (Progress Ledger: current progress/assignments). D3MAS uses hierarchical graph decomposition.
**Action:** Implement Task Ledger + Progress Ledger pattern in our self-improvement orchestrator. Currently we have a flat cycle with no structured fact/guess/plan tracking.
| ID | Item | Owner | Sprint |
|----|------|-------|--------|
| F-01 | Add Task Ledger (structured facts/guesses/plan) to self-improvement cycle | Rosie | 3 |
| F-02 | Add Progress Ledger (per-agent task tracking with assignments) | Rosie | 3 |

#### 2. Skill-as-Code Memory (from Voyager / CASCADE / SAGE)
**Finding:** Voyager saves solutions as Python functions in a skill library. CASCADE accumulates executable skills. SAGE preserves skills across tasks for reuse.
**Action:** Our self-improvement loop generates improvements but doesn't save reusable skill functions. We should extract successful patterns into a skill library that agents can call.
| ID | Item | Owner | Sprint |
|----|------|-------|--------|
| F-03 | Build skill library from successful self-improvement patterns (Python functions saved + indexed) | Mack | 3 |
| F-04 | Add skill retrieval step to self-improvement prompt (check library before generating new) | Rosie | 3 |

#### 3. Conflict Resolution Protocols (from BCCS / voting research)
**Finding:** Cumulative voting (25 points across options) beats simple majority. Consensus excels in knowledge tasks, voting in reasoning. BCCS outperforms both.
**Action:** When agents disagree on approach (e.g., memory architecture), use structured voting instead of whoever-runs-first-wins.
| ID | Item | Owner | Sprint |
|----|------|-------|--------|
| F-05 | Implement agent voting protocol for architectural decisions (cumulative voting via NATS) | Lenny | 4 |

#### 4. SOP Encoding (from MetaGPT)
**Finding:** MetaGPT encodes SOPs into agents — PM outputs PRD, Architect subscribes to produce UML, Engineer subscribes to produce code. Shared message pool.
**Action:** Our agents don't have formal subscription chains. Encode our WORKFLOW_AUTO.md as subscription triggers — when Rosie outputs a plan, Mack auto-subscribes to implement.
| ID | Item | Owner | Sprint |
|----|------|-------|--------|
| F-06 | Encode agent SOPs as NATS subscription chains (plan→implement→verify→deploy) | Rosie | 4 |

#### 5. OpenClaw-Specific Optimizations (from research citations)
**Finding:** Session resets reduce costs 40-60%. Smart model switching saves money. Selective skill injection keeps context lean.
**Action:** Implement regular /compact scheduling, model-cost tracking per agent, and audit our skill injection for bloat.
| ID | Item | Owner | Sprint |
|----|------|-------|--------|
| F-07 | Add cost-per-agent tracking (model tokens × cost per cycle) | Winnie | 2 |
| F-08 | Schedule periodic session compaction for long-running agents | Lenny | 2 |

#### 6. Hierarchical Security (from cyberSPADE)
**Finding:** Three-layer architecture: Coordination (monitor), Execution (swarms), Communication (message server). Strategic control loop at supervisor level.
**Action:** Our stack orchestrator is flat. Add a strategic monitor layer that evaluates system-level health beyond individual service checks.
| ID | Item | Owner | Sprint |
|----|------|-------|--------|
| F-09 | Add strategic health monitor (system-level patterns, not just service pings) | Lenny | 4 |
