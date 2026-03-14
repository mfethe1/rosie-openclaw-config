# Daily Agentic Loop
**Version:** 1.0 | **Updated:** 2026-03-02

---

## Overview

The daily loop is fully async. Agents execute independently; humans review at defined gates.
No human needs to be online during agent execution — only during the HITL review window.

```
09:00  Context Injection      ←  Orchestrator drops approved task packets
09:05  Execution              ←  Agents run autonomously
~~     Automated Gauntlet     ←  Triggered on PR open (CI gate)
14:00  HITL Review Window     ←  Humans review gauntlet results (max 2h)
16:00  Deploy / Rollback      ←  Go/No-Go decision + execution
16:30  Daily Log Update       ←  Each agent appends 3-line status
```

---

## Phase 1: Context Injection (09:00–09:05)

**Owner:** Orchestrator (human)
**Duration:** 5 minutes

### Steps
1. Orchestrator places approved task packets in `task_packets/READY/`.
2. Each packet must pass template validation:
   ```bash
   python3 scripts/run_gauntlet_checklist.py task_packets/READY/TASK-001.md --pre-flight
   ```
3. Packets failing pre-flight are moved to `task_packets/REJECTED/` with reason appended.
4. Agent picks up any packet in `READY/` matching its role.

### Agent pickup command (example)
```bash
# Plumber picks up its task
ls task_packets/READY/ | grep plumber
# → TASK-001-plumber.md

# Agent logs intake
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) TASK-001 INTAKE plumber" >> logs/agent_run.log
```

---

## Phase 2: Execution (09:05–~14:00)

**Owner:** Agent (autonomous)
**Duration:** Up to 5 hours (SLA: task complete or BLOCKED status by 13:45)

### Agent execution rules
1. Work only on files declared in `[SECTION 1] Repo Map`.
2. Emit progress markers to stdout every 30 min:
   ```
   [PROGRESS] TASK-001 | plumber | 30min mark | status: in_progress | files_modified: 2
   ```
3. On any ambiguity: stop, write `STATUS: BLOCKED` to packet, ping Sentinel. Do NOT guess.
4. On budget overrun: emit `BUDGET_EXCEEDED`, stop immediately, report partial state.
5. On exception/crash: write traceback to `logs/errors/TASK-001.log`, set status BLOCKED.

### Dead-man switch
If no progress marker in 60 min → Sentinel receives automated alert → agent flagged for review.
(See `GUARDRAILS_CHECKLIST.md` for implementation.)

---

## Phase 3: Automated Gauntlet (CI — triggered on PR open)

**Owner:** Red Team agent + CI runner
**Trigger:** PR opened against `main`

### Gauntlet steps (run in order, fail-fast)

```bash
# 1. Task packet validation
python3 scripts/run_gauntlet_checklist.py task_packets/DONE/TASK-001.md

# 2. Linter
ruff check . --exit-zero

# 3. Security scan (secrets)
gitleaks detect --source . --exit-code 1

# 4. Unit tests
pytest -x --tb=short

# 5. Coverage gate
pytest --cov=src --cov-fail-under=70

# 6. Red Team probe (if red_team task)
python3 scripts/red_team_probe.py --task TASK-001
```

### Gauntlet outcomes

| Result | Action |
|--------|--------|
| All pass | PR marked `gauntlet:pass`, enters HITL queue |
| Any fail | PR marked `gauntlet:fail`, agent notified, humans NOT paged |
| Secrets detected | PR auto-closed, Sentinel paged immediately |
| Red Team: CRITICAL | Deploy blocked, Sentinel + Orchestrator paged |

### Retry policy
- Agent may fix and re-push up to **3 times** before human intervention required.
- After 3 failures: PR labeled `needs-human`, Sentinel assigns for review.

---

## Phase 4: HITL Review Window (14:00–16:00)

**Owner:** Domain Expert + Sentinel
**Duration:** Max 2 hours. If no decision by 16:00 → task rolls to next day.

### Review checklist (human)
- [ ] Gauntlet passed (CI badge green)
- [ ] Diff is scoped to declared repo map (no surprise files)
- [ ] Definition of Done items checked off in task packet
- [ ] Test matrix rows covered by new tests
- [ ] No logic that looks auto-generated without review comment
- [ ] Rollback plan documented

### Sign-off options
1. **Approve:** Update task packet `[SECTION 8]` with name + timestamp, label PR `hitl:approved`.
2. **Reject:** Write rejection reason in task packet, label PR `hitl:rejected`, notify agent.
3. **Request Changes:** Label `hitl:changes-requested`, add inline comments. Agent gets 1 retry same day.

---

## Phase 5: Deploy / Rollback (16:00–16:30)

**Owner:** Orchestrator (go/no-go), Plumber (execution)

### Deploy (go)
```bash
# Merge PR
gh pr merge {{PR_NUMBER}} --squash --delete-branch

# Deploy (example: fly.io)
fly deploy --app issuesflow-prod

# Smoke test
curl -sf https://issuesflow.com/health | jq '.status'
# → "ok"

# Tag release
git tag -a v{{VERSION}} -m "Task {{TASK_ID}}: {{TASK_TITLE}}" && git push --tags
```

### Rollback (no-go or post-deploy failure)
```bash
# Immediate rollback
git revert HEAD --no-edit && git push origin main
fly deploy --app issuesflow-prod   # redeploy previous

# OR for infra
kubectl rollout undo deployment/{{SERVICE_NAME}}

# Notify
echo "ROLLBACK executed for TASK-{{TASK_ID}} at $(date -u)" >> logs/deploy.log
```

### Post-deploy verification (automated, 5 min window)
```bash
# Run smoke tests
pytest tests/smoke/ -x --timeout=30

# Check error rate (if metrics available)
# Expected: error_rate < 1% over 5 min
```

If smoke tests fail → auto-rollback triggers, Sentinel paged.

---

## Phase 6: Daily Log Update (16:30)

Each agent appends to `logs/DAILY_LOG.md`:
```
## {{DATE}} — {{AGENT_ROLE}}
- Task: {{TASK_ID}} | Status: {{DONE|BLOCKED|ROLLED_BACK}}
- Outcome: {{one line summary}}
- Next: {{next action or "waiting for new packet"}}
```

---

## SLA Table

| Phase | SLA | Breach Action |
|-------|-----|--------------|
| Context Injection | Complete by 09:05 | Orchestrator escalates |
| Execution | Status update by 13:45 | Dead-man alert → Sentinel |
| Gauntlet | Complete within 20 min of PR open | CI alert to Sentinel |
| HITL Review | Decision by 16:00 | Task rolls to next day, Orchestrator notified |
| Deploy | Complete by 16:30 | Orchestrator escalates to next business hour |
| Progress marker | Every 30 min during execution | Sentinel alert after 60 min silence |

---

## Escalation Rules

| Trigger | Escalate To | Channel | Response SLA |
|---------|------------|---------|-------------|
| Guardrail breach | Sentinel | Telegram page | 15 min |
| Secrets detected in PR | Sentinel + Orchestrator | Telegram page | Immediate |
| 3x gauntlet failure | Sentinel | Telegram message | 30 min |
| No progress marker 60 min | Sentinel | Telegram message | 15 min |
| Red Team CRITICAL finding | Orchestrator + Sentinel | Telegram page | Immediate |
| HITL no decision by 16:00 | Orchestrator | Telegram reminder | N/A (task rolls) |
| Post-deploy smoke fail | Sentinel (auto-rollback first) | Telegram page | 15 min |

---

## Sample Full-Day Command Sequence

```bash
# 09:00 — Orchestrator drops packet
cp templates/task_template.md task_packets/READY/TASK-007-plumber.md
# (fill in sections)
python3 scripts/run_gauntlet_checklist.py task_packets/READY/TASK-007-plumber.md --pre-flight

# Agent picks up and runs (autonomous from here)

# ~14:00 — PR opened by agent, CI gauntlet runs automatically

# 14:30 — Sentinel reviews CI output
gh pr view {{PR_NUMBER}} --json statusCheckRollup

# 15:00 — Domain Expert reviews diff
gh pr diff {{PR_NUMBER}}
# Signs off in task packet

# 16:00 — Orchestrator deploys
gh pr merge {{PR_NUMBER}} --squash && fly deploy --app issuesflow-prod

# 16:30 — Daily log
echo "## $(date +%Y-%m-%d) — plumber\n- Task: TASK-007 | Status: DONE\n- Outcome: Stripe webhook live\n- Next: waiting for new packet" >> logs/DAILY_LOG.md
```
