# Fermware Execution Board (Sprint 0 → Sprint 1)

Last updated: 2026-03-03
Owner: Rosie (coordination), Michael (product decisions)

## Objectives
1. Stabilize the core workflow and eliminate avoidable failures.
2. Add observability to make priorities data-driven.
3. Ship small, frequent improvements with rollback safety.

## Priority Ladder
- **P0**: Reliability / data integrity / auth / deployment blockers
- **P1**: Growth and adoption features
- **P2**: UX polish and nice-to-haves

---

## Top 10 Tickets (Ready to Execute)

### FMW-001 — Define Critical User Path (P0)
**Goal:** Identify the single workflow Fermware must never fail at.
**Acceptance Criteria:**
- One-page workflow map committed.
- Named start/end events and failure points.
- Owners for each step assigned.
**Metric:** Critical path documented and reviewed.

### FMW-002 — Add Structured Error Logging (P0)
**Goal:** Capture actionable failures across API + frontend.
**Acceptance Criteria:**
- Standard error schema (`trace_id`, `route`, `user_state`, `severity`, `error_code`).
- Logs visible in one place.
- No secrets/PII in logs.
**Metric:** 95%+ of runtime errors include structured payload.

### FMW-003 — Healthcheck + Readiness Endpoints (P0)
**Goal:** Fast detection of degraded service.
**Acceptance Criteria:**
- `/healthz` and `/readyz` implemented.
- Dependency checks included (DB/cache/external APIs as applicable).
- Status integrated into deployment checks.
**Metric:** Health endpoint available with sub-500ms response.

### FMW-004 — Idempotency + Retry Guardrails (P0)
**Goal:** Prevent duplicate/partial operations on retries.
**Acceptance Criteria:**
- Idempotency keys on critical write operations.
- Safe retry policy with bounded backoff.
- Duplicate operation test cases passing.
**Metric:** Duplicate write incidents reduced to zero on tested paths.

### FMW-005 — Critical Path Smoke Tests (P0)
**Goal:** Prevent regressions before/after deploy.
**Acceptance Criteria:**
- Automated smoke suite for core path.
- Runs on CI and post-deploy.
- Fails block production release.
**Metric:** 100% of deploys include smoke run record.

### FMW-006 — Product Event Taxonomy (P1)
**Goal:** Track user behavior consistently.
**Acceptance Criteria:**
- Event naming convention documented.
- Core funnel events instrumented.
- Event payload validation in place.
**Metric:** End-to-end funnel visible daily.

### FMW-007 — Live Ops Dashboard v1 (P1)
**Goal:** Single view for health + usage.
**Acceptance Criteria:**
- Dashboard includes traffic, conversion, errors, and latency.
- 24h and 7d trend views.
- Accessible to Fermware team.
**Metric:** Daily review can be done from one dashboard.

### FMW-008 — Failure-Only Alerting (P1)
**Goal:** Reduce noise and improve response speed.
**Acceptance Criteria:**
- Alerts only for critical failures and SLO breaches.
- Alert runbook linked.
- On-call routing confirmed.
**Metric:** Alert volume reduced; mean-time-to-detect improved.

### FMW-009 — Feature Flags for New Work (P1)
**Goal:** Ship incrementally with safe rollback.
**Acceptance Criteria:**
- Flag framework selected/implemented.
- New features gated by default.
- Kill switch documented.
**Metric:** Rollback from flag can complete in <5 minutes.

### FMW-010 — Weekly Decision Review Loop (P1)
**Goal:** Prioritize by evidence, not intuition.
**Acceptance Criteria:**
- Weekly 30-min review template created.
- Decisions logged as keep/kill/add with metric reference.
- Backlog updated same day.
**Metric:** 100% of weekly decisions recorded with rationale.

---

## Suggested Sprint Sequence
- **Sprint 0 (this week):** FMW-001 → 005
- **Sprint 1 (next week):** FMW-006 → 010

## Definition of Done (all tickets)
- Change shipped or merged behind flag
- Validation evidence attached (test output/dashboard screenshot/log query)
- Rollback path documented
- Owner + follow-up date set
