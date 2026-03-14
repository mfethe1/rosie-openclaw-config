# Context Injection Template
**Version:** 1.0 | **Updated:** 2026-03-02

---

## Usage

Copy this template into a task packet. Fill every section before handing off to an agent.
Incomplete sections → task packet rejected at gauntlet.

```
python3 scripts/create_task_packet.py \
  --task-id TASK-001 \
  --agent plumber \
  --title "Wire Stripe webhook to Issuesflow billing" \
  --repo https://github.com/mfethe/issuesflow \
  --output task_packets/TASK-001.md
```

---

## Template

```markdown
# Task Packet: {{TASK_ID}}
**Agent:** {{AGENT_ROLE}}          <!-- plumber | reader | red_team -->
**Title:** {{TASK_TITLE}}
**Created:** {{CREATED_AT}}
**Status:** DRAFT | READY | IN_PROGRESS | REVIEW | DONE | BLOCKED

---

## [SECTION 1] Repo Map

<!-- Required. List relevant files/dirs the agent needs to read/modify. -->
<!-- Format: path :: purpose -->

- `src/webhooks/stripe.py` :: Stripe event handler (primary edit target)
- `src/billing/models.py`  :: Subscription model
- `tests/test_stripe.py`   :: Existing test suite
- `infra/terraform/`       :: Do NOT touch (read-only reference)
- `docs/api/stripe.md`     :: Reference for event shape

**Branch:** `{{BRANCH_NAME}}`
**Base commit:** `{{BASE_COMMIT_SHA}}`

---

## [SECTION 2] API Docs & External References

<!-- Required. Link every external API the agent may call or reference. -->

| API / Resource | URL | Auth Method | Rate Limit |
|---------------|-----|-------------|-----------|
| Stripe Webhooks | https://stripe.com/docs/webhooks | Webhook secret (env: STRIPE_WEBHOOK_SECRET) | 100 rps |
| Issuesflow Internal API | https://api.issuesflow.com/v2/docs | Bearer (env: ISSUESFLOW_API_KEY) | 50 rps |
| <!-- Add more rows --> | | | |

**Env vars required:** (list all, never hardcode values)
```
STRIPE_WEBHOOK_SECRET=
ISSUESFLOW_API_KEY=
DATABASE_URL=
```

---

## [SECTION 3] Constraints

<!-- Required. Hard rules the agent MUST NOT violate. -->

### Must NOT
- [ ] Modify files outside declared repo map without Sentinel approval
- [ ] Commit secrets or API keys to any file
- [ ] Delete existing tests
- [ ] Call external endpoints not listed in Section 2
- [ ] Exceed token budget (see Section 6)

### Must
- [ ] Run linter (`ruff check .`) before submitting
- [ ] Pass existing test suite without regressions
- [ ] Leave audit comment in code: `# AGENT: {{AGENT_ROLE}} {{TASK_ID}}`
- [ ] Use stdlib only for scripts (no pip installs in CI)

### Scope boundary
> {{SCOPE_BOUNDARY_DESCRIPTION}}
> Example: "Only touch stripe webhook ingestion. Do not modify subscription upgrade logic."

---

## [SECTION 4] Definition of Done

<!-- Required. Gauntlet will reject if this section is missing or has unchecked items at merge. -->

- [ ] Feature works end-to-end in staging environment
- [ ] All existing tests pass (`pytest -x`)
- [ ] New tests cover the happy path and at least 2 failure modes
- [ ] No linter errors (`ruff check . --exit-zero` returns 0)
- [ ] PR description references this task packet ID
- [ ] Domain Expert has reviewed and signed off
- [ ] No secrets committed (gitleaks scan clean)
- [ ] {{CUSTOM_DOD_1}}
- [ ] {{CUSTOM_DOD_2}}

---

## [SECTION 5] Test Matrix

<!-- Required. Gauntlet checks this section exists and has ≥ 3 rows. -->

| Test Case | Input | Expected Output | Pass Criteria |
|-----------|-------|----------------|---------------|
| Happy path: valid Stripe event | `{"type": "invoice.paid", ...}` | Subscription updated, 200 OK | DB record updated |
| Invalid signature | Tampered payload | 400 Bad Request | No DB write |
| Duplicate event (idempotency) | Same event ID twice | 200 OK, no duplicate record | Single DB row |
| Unknown event type | `{"type": "foo.bar"}` | 200 OK, logged and ignored | Log entry present |
| Missing env var | STRIPE_WEBHOOK_SECRET="" | Startup error, clear message | Process exits non-zero |
| {{CUSTOM_TEST_1}} | | | |

---

## [SECTION 6] Token Budget

<!-- Required. Agent must stay within budget. Overruns → pause and report. -->

| Phase | Allotted Tokens | Hard Limit |
|-------|----------------|-----------|
| Context ingestion (reading files) | 20,000 | 30,000 |
| Execution (writes/edits) | 30,000 | 50,000 |
| Review / self-check | 10,000 | 15,000 |
| **Total** | **60,000** | **95,000** |

**On budget overrun:** Stop, emit `BUDGET_EXCEEDED` marker, report current state to Sentinel.
Do not truncate work silently to fit budget.

---

## [SECTION 7] Rollback Plan

<!-- Recommended. Required for any deploy touching production data. -->

**Rollback command:**
```bash
git revert {{MERGE_COMMIT_SHA}} && git push origin main
# or
kubectl rollout undo deployment/{{SERVICE_NAME}}
```

**Data rollback:** {{DATA_ROLLBACK_INSTRUCTIONS or "N/A — no data migration"}}

**Verification after rollback:**
```bash
curl -s https://{{HEALTH_ENDPOINT}} | jq '.status'
# Expected: "ok"
```

---

## [SECTION 8] Sign-offs

| Role | Name | Timestamp | Status |
|------|------|-----------|--------|
| Domain Expert | | | ☐ Approved / ☐ Rejected |
| Sentinel | | | ☐ Approved / ☐ Rejected |
| Orchestrator | | | ☐ Go / ☐ No-Go |

**Rejection reason (if any):** {{REJECTION_REASON}}
```

---

## Minimal Required Sections

For gauntlet to pass, these sections must be present and non-empty:
1. `[SECTION 1] Repo Map` — ≥ 1 file entry
2. `[SECTION 2] API Docs` — ≥ 1 row OR explicit "No external APIs"
3. `[SECTION 3] Constraints` — Must and Must NOT lists present
4. `[SECTION 4] Definition of Done` — ≥ 3 checklist items
5. `[SECTION 5] Test Matrix` — ≥ 3 test case rows
6. `[SECTION 6] Token Budget` — Total allotted tokens declared
