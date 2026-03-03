# Fermware Stack Inventory Matrix

Last updated: 2026-03-03
Status: Execution kickoff

## Legend
- **Reuse now**: can integrate with minimal changes
- **Refactor**: useful but needs redesign or hardening
- **Archive**: keep for reference only

| Project/Asset | Current Capability | Decision | Target Lane | Owner | Mapped Ticket |
|---|---|---|---|---|---|
| `projects/issuesflow/README-draft.md` | Deterministic issue workflow pattern (discover→execute→verify) | Reuse now | Coordinator | Rosie | FMW-A04 |
| `projects/issuesflow/AUDIT.md` | Reliability findings (idempotency, duplicate risks, UX failures) | Reuse now | Verifier | Lenny | FMW-A03, FMW-A06 |
| `projects/issuesflow/BACKLOG.md` | Adoption hardening backlog and rollout concerns | Refactor | Operator | Rosie | FMW-A08 |
| `projects/auth-billing/PLAN.md` | Supabase auth + Stripe credit system concept | Reuse now | Policy Gate | Mack | FMW-A07 |
| `projects/dwg-integration/round2_arch.md` | Dedicated heavy compute worker pattern | Reuse now | Builder | Mack | FMW-A05 |
| `projects/dwg-integration/round3_qa.md` | QA considerations for worker safety/perf | Refactor | Verifier | Lenny | FMW-A06 |
| `self_improvement/AGENT_FINALIZED_ARCHITECTURE.md` | Canonical multi-lane agent model | Reuse now | Coordinator | Rosie | FMW-A04 |
| `self_improvement/LOOPS.md` | Continuous cycle checklists and handoff discipline | Refactor | Operator | Rosie | FMW-A08 |
| `agents/rosie.md` | Coordination profile and quality gates | Reuse now | Coordinator | Rosie | FMW-A04 |
| `agents/mack.md` | Build execution profile | Reuse now | Builder | Mack | FMW-A05 |
| `agents/winnie.md` | Research/scout profile | Reuse now | Scout | Winnie | FMW-A04 (routing extension) |
| `agents/lenny.md` | Resilience/QA profile | Reuse now | Verifier | Lenny | FMW-A06 |
| `agent-coordination/README.md` | Basic inbox model for asynchronous coordination | Refactor | Operator | Rosie | FMW-A01 |
| `self_improvement/CHANGELOG.md` | Audit trail pattern | Reuse now | Run Ledger | Mack | FMW-A02 |

---

## Phase 1 Build Queue (Activated)

1. **FMW-A01** — Canonical run schema + event types
   - Draft states: `queued`, `running`, `blocked`, `review`, `done`, `failed`
   - Required keys: `run_id`, `workflow_id`, `task_type`, `lane`, `owner`, `status`, `idempotency_key`, `created_at`, `updated_at`

2. **FMW-A02** — Run ledger API/storage
   - Append-only events
   - Query by `run_id`, `workflow_id`, `status`, `owner`

3. **FMW-A03** — Idempotency middleware
   - Protect all external writes
   - Reject duplicate `idempotency_key` within configurable TTL

4. **FMW-A04** — Routing table and coordinator rules
   - `research` → Scout
   - `implementation` → Builder
   - `qa/security/reliability` → Verifier
   - `ops/incident` → Operator

5. **FMW-A05** — Builder lane adapter
   - First worker integration with deterministic request/response contract

6. **FMW-A06** — Verifier lane gate
   - Smoke + regression checks must pass before `done`

7. **FMW-A07** — Policy + budget guardrail
   - Credits and per-run budget caps
   - Hard-stop on budget exhaustion

8. **FMW-A08** — Ops dashboard + failure alerts
   - Throughput, failures, latency, spend
   - Alert only on SLO breaches/failures

---

## Immediate Execution Notes
- `Sanger` path still not discovered in current workspace scan; pending explicit directory reference.
- Generative-flow components should be mapped once exact folders/repos are provided.
- No blockers for starting A01→A04 now.
