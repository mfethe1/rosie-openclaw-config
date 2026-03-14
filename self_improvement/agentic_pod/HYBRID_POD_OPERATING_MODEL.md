# Hybrid Pod Operating Model
**Version:** 1.0 | **Updated:** 2026-03-02

---

## 1. Purpose

A lean hybrid pod that pairs human judgment with agent execution. Humans own intent, approval, and escalation. Agents own throughput, pattern-matching, and adversarial stress.

---

## 2. Roles

### Human Roles

| Role | Responsibilities |
|------|-----------------|
| **Orchestrator** | Sets sprint OKRs, approves task packets, makes go/no-go deploy decisions, owns escalation path. Single point of accountability per sprint. |
| **Sentinel** | Monitors agent outputs for safety/compliance. Reviews guardrail alerts. Holds kill-switch authority. On-call during automated gauntlet runs. |
| **Domain Expert** | Provides business context, validates output quality (not just format), signs off on definition-of-done criteria for their domain. |

### Agent Roles

| Role | Responsibilities |
|------|-----------------|
| **Plumber** | Executes integration tasks: API wiring, webhook plumbing, schema migrations, CI/CD pipeline changes. Tool-heavy, low-ambiguity work. |
| **Reader** | Ingests and structures unstructured data: PDFs, blueprints, transcripts, changelogs. Produces structured markdown or JSON. |
| **Red Team** | Adversarially probes systems: test guardrails, fuzz inputs, simulate edge cases, generate negative test cases. Reports exploits as issues. |

---

## 3. RACI Matrix

> **R** = Responsible (does the work) | **A** = Accountable (final sign-off) | **C** = Consulted | **I** = Informed

| Activity | Orchestrator | Sentinel | Domain Expert | Plumber | Reader | Red Team |
|----------|-------------|---------|---------------|---------|--------|---------|
| Define sprint OKRs | **A** | I | C | I | I | I |
| Author task packet | **A** | C | **R** | I | I | I |
| Context injection | C | I | **R** | **R** | **R** | **R** |
| Execute task | I | I | C | **R** | **R** | **R** |
| Automated gauntlet | I | **A** | C | I | I | **R** |
| HITL review | **A** | C | **R** | I | I | I |
| Deploy approval | **A** | C | I | I | I | I |
| Rollback decision | **A** | **R** | I | I | I | I |
| Guardrail breach alert | C | **A** | I | I | I | I |
| Kill-switch activation | I | **A** | I | I | I | I |
| Post-mortem | **R** | **R** | C | I | I | I |

---

## 4. Month 1 OKRs

### Objective: Validate hybrid pod model across 3 pilot workflows

| Key Result | Owner | Target | Measurement |
|-----------|-------|--------|-------------|
| KR1: All 3 pilots complete at least one end-to-end loop | Orchestrator | 100% | Loop completion log |
| KR2: Gauntlet pass rate ≥ 80% on first submission | Plumber/Reader | ≥80% | `run_gauntlet_checklist.py` output |
| KR3: Zero unreviewed deploys (HITL gate enforced) | Sentinel | 0 bypasses | Deploy audit log |
| KR4: Red Team identifies ≥ 3 guardrail gaps | Red Team | ≥3 | Issues filed in tracker |
| KR5: Mean HITL review time < 30 min per task | Domain Expert | <30 min | Timestamp delta in task packets |
| KR6: Task packet generation time < 2 min (CLI tool) | Orchestrator | <2 min | `create_task_packet.py --test` benchmark |

### Anti-goals (Month 1)
- Do NOT optimize for speed over safety
- Do NOT expand to more than 3 pilots before all 3 pass gauntlet
- Do NOT automate the deploy gate — HITL required all of Month 1

---

## 5. Communication Protocol

- **Async-first:** All task state lives in task packets (markdown files), not in DMs.
- **Escalation path:** Agent alert → Sentinel → Orchestrator → Domain Expert (if domain knowledge needed).
- **Daily standup artifact:** Each agent produces a 3-line status update appended to `DAILY_LOG.md`.
- **Blocking issues:** Sentinel pages Orchestrator within 15 min of guardrail breach.

---

## 6. Pod Norms

1. No agent executes outside its declared tool allowlist (see `GUARDRAILS_CHECKLIST.md`).
2. Every deploy has a linked task packet with approved DoD.
3. Rollback procedures are tested before a pilot goes live.
4. Red Team findings block deploy if severity ≥ HIGH until patched.
