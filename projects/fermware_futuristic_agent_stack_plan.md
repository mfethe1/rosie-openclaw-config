# Fermware Futuristic Agent Stack Plan

Last updated: 2026-03-03

## Intent
Unify existing project assets (IssuesFlow, Auth/Billing, DWG worker patterns, and multi-agent loop infrastructure) into one sustainable Fermware platform with specialized agents.

## What We Should Reuse Immediately

1. **From IssuesFlow**
- Deterministic workflow: discover → plan → execute → verify.
- Dry-run before writes.
- Claims/cursor style coordination to avoid duplicate work.
- Reliability hardening backlog (idempotency, explicit failure messages).

2. **From Auth/Billing**
- Supabase auth with protected routes.
- Credit-based usage control for expensive agent actions.
- Stripe webhook reconciliation model.

3. **From DWG Integration**
- Dedicated worker microservice pattern for heavy compute tasks.
- API contract-first design.
- Separation of web app runtime from specialized processing.

4. **From Self-Improvement/Agent System**
- Role-based lanes (Research, Build, QA/Resilience, Coordinator).
- Explicit handoffs, proof artifacts, retry budgets.
- Continuous loop with guardrails and quality gates.

---

## Target Product Architecture (Agentic Fermware)

## Layer A — Product Surface
- Web app/API for users and operators.
- Auth, org/team controls, billing/credits.
- Workspace-level project objects (flows, runs, outputs, alerts).

## Layer B — Orchestration Core
- **Workflow Engine:** deterministic state machine per run.
- **Task Router:** maps task type to specialized agent lane.
- **Run Ledger:** append-only event log for traceability.
- **Policy Gate:** validates permissions, budget, and risk before execution.

## Layer C — Specialized Agent Lanes
- **Scout Agent:** external research, alternatives, feasibility.
- **Builder Agent:** implementation/execution tasks.
- **Verifier Agent:** QA, guardrails, regression checks.
- **Operator Agent:** reliability, incident response, runbook actions.
- **Coordinator Agent:** planning, prioritization, handoff management.

## Layer D — Execution Workers
- Tool-specific workers (e.g., code worker, document parser, DWG/compute worker, messaging worker).
- Isolated queues per worker class with idempotency keys.

## Layer E — Observability & Governance
- Real-time dashboard: throughput, failures, latency, unit economics.
- Failure-only alerts and runbook links.
- Audit timeline per workflow run.

---

## Sustainability Rules (Non-Negotiable)

1. **Deterministic runs first**: no unbounded loops in production flows.
2. **Idempotent writes**: every external write uses run_id + idempotency key.
3. **Budget enforcement**: model/tool usage capped by policy and credit plan.
4. **Proof artifacts required**: each completed task stores evidence.
5. **Graceful failure UX**: every common failure has exact remediation.
6. **Feature flags for all new capabilities**: fast rollback path.

---

## 30-Day Build Roadmap

## Week 1 — Core Control Plane
- Implement run state machine (`queued/running/blocked/review/done/failed`).
- Add run ledger schema + event contracts.
- Add idempotency middleware and retry policy.

## Week 2 — Agent Lane MVP
- Implement Coordinator + Builder + Verifier lanes.
- Add task routing rules and ownership handoffs.
- Add smoke tests for one end-to-end critical path.

## Week 3 — Billing + Policy + UI
- Wire auth and org scopes.
- Add usage credits and budget guardrails.
- Build v1 ops dashboard (health, cost, success rates).

## Week 4 — Hardening + Expansion
- Failure-only alerts with on-call runbooks.
- Add Scout and Operator lanes.
- Run load/failure drills and ship v1 beta.

---

## Initial Backlog (First 8 Execution Tickets)

1. FMW-A01: Define canonical run schema + event types.
2. FMW-A02: Implement run ledger storage and query API.
3. FMW-A03: Add idempotency key middleware for external write actions.
4. FMW-A04: Implement coordinator routing table (task_type → lane).
5. FMW-A05: Build Builder lane adapter (first worker integration).
6. FMW-A06: Build Verifier lane with regression smoke gate.
7. FMW-A07: Add usage budget policy gate (credits + limits).
8. FMW-A08: Ship ops dashboard v1 + failure-only alerts.

---

## Open Gaps to Resolve
- "Sanger" project references are not yet mapped in current workspace paths.
- Need explicit inventory of generative-flow components to wire into lanes.
- Need one canonical data model to bridge all legacy project objects.

## Next Action
Create a stack inventory matrix (`project`, `capability`, `reuse now`, `needs refactor`, `owner`) and bind each item to the FMW-A tickets above.
