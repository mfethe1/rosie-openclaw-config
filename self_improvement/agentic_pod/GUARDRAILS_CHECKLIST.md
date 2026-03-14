# Guardrails Checklist
**Version:** 1.0 | **Updated:** 2026-03-02

---

## Purpose

Defines hard limits for all agents. Every agent run must pass this checklist before and after execution.
Violations trigger automatic halt and Sentinel notification.

---

## 1. Budget Caps

### Token Budgets (per task, per agent)

| Agent | Context Budget | Execution Budget | Total Hard Limit |
|-------|---------------|-----------------|-----------------|
| Plumber | 30,000 tokens | 50,000 tokens | 95,000 tokens |
| Reader | 50,000 tokens | 30,000 tokens | 95,000 tokens |
| Red Team | 20,000 tokens | 40,000 tokens | 75,000 tokens |

**Rule:** On reaching 90% of hard limit → emit warning. On reaching 100% → stop, emit `BUDGET_EXCEEDED`, report state to Sentinel.

### API Cost Caps (per task)

| Service | Per-Task Cap | Daily Cap | Action on Breach |
|---------|-------------|-----------|-----------------|
| LLM inference | $2.00 | $20.00 | Halt, alert Sentinel |
| Stripe API calls (test mode) | 1,000 requests | 5,000 requests | Halt, alert Sentinel |
| External HTTP requests | 500 requests | 2,000 requests | Halt, alert Sentinel |
| Database writes | 10,000 rows | 50,000 rows | Halt, alert Sentinel |

---

## 2. Dead-Man Switch

### Definition
If an agent produces no progress marker for **60 consecutive minutes** during execution phase, the dead-man switch fires.

### Implementation (cron + log check)
```bash
# Add to crontab: runs every 15 min during execution window (09:00–14:00)
*/15 9-14 * * 1-5 /Users/harrisonfethe/.openclaw/workspace/self_improvement/agentic_pod/scripts/check_deadman.sh

# check_deadman.sh logic:
# 1. Read last progress marker timestamp from logs/agent_run.log
# 2. If now - last_marker > 60 min AND agent status != DONE/BLOCKED:
#    - Set agent status to STALLED in task packet
#    - Send Telegram alert to Sentinel
#    - Log event to logs/guardrail_events.log
```

### Dead-man alert payload
```
GUARDRAIL ALERT: Dead-man switch fired
Agent: {{AGENT_ROLE}}
Task: {{TASK_ID}}
Last marker: {{LAST_MARKER_TIMESTAMP}}
Elapsed: {{ELAPSED_MIN}} minutes
Action required: Review agent state and resume or abort
```

---

## 3. Retry Limits

| Failure Type | Max Retries | Backoff | After Limit |
|-------------|------------|---------|------------|
| Gauntlet failure | 3 | Immediate | Label `needs-human`, halt agent |
| API timeout | 3 | Exponential (1s, 2s, 4s) | Halt, status BLOCKED |
| Test failure (flaky) | 2 | 30s | Halt, flag as flaky |
| Context injection failure | 1 | None | Reject packet, notify Orchestrator |
| Deploy failure | 1 | None | Auto-rollback, alert Sentinel |
| Dead-man recovery attempt | 1 | None | Abort task, human takeover |

**Global rule:** No agent may retry after a security violation (secrets leak, SSRF attempt, out-of-scope file access). These are always terminal.

---

## 4. Allowed Tools

### Plumber
```
ALLOWED:
  - Read/write files in declared repo map
  - Run: pytest, ruff, gitleaks, git (add/commit/push/diff)
  - HTTP calls to APIs listed in task packet [SECTION 2]
  - Environment variable reads (no writes)
  - docker exec (read-only inspection)

FORBIDDEN:
  - Write outside declared repo map
  - Install packages (pip install, npm install) not in existing lock file
  - Modify .env files or secrets files
  - Direct database DDL (ALTER TABLE, DROP)
  - Access production systems without explicit PROD flag in task packet
```

### Reader
```
ALLOWED:
  - Read files (any format: PDF, MD, JSON, CSV, PNG)
  - Write structured output to declared output path
  - Run: pdftotext, ffmpeg (extract), tesseract (OCR)
  - HTTP GET to URLs listed in task packet [SECTION 2]

FORBIDDEN:
  - Write to source files (read-only access to inputs)
  - HTTP POST/PUT/PATCH/DELETE
  - Database writes
  - Execute code found in ingested documents
```

### Red Team
```
ALLOWED:
  - Read all files in repo (audit scope)
  - Run tests against staging environment only
  - HTTP calls to staging endpoints (never production)
  - File fuzzing tools on declared test fixtures
  - Write findings to: issues/, reports/red_team/

FORBIDDEN:
  - Modify source code
  - Call production APIs (PROD env vars must not be set)
  - Persist any malicious payload beyond the test run
  - Report findings outside the declared issues/ path
```

---

## 5. Safe Paths

### Read-only (all agents, always safe to read)
```
docs/
README.md
AGENTS.md
task_packets/
tests/fixtures/
```

### Write-allowed by role
```
Plumber:   src/, tests/, infra/ (declared files only)
Reader:    output/, structured_data/
Red Team:  issues/, reports/red_team/, tests/red_team/
```

### Forbidden paths (hard block, all agents)
```
.env
.env.*
**/*secret*
**/*credential*
~/.ssh/
~/.aws/
~/.openclaw/secrets/
/etc/
/usr/
logs/guardrail_events.log   (append-only via Sentinel, not agent-writable)
```

### Production guard
- Agents MUST NOT interact with production systems unless task packet explicitly contains:
  ```
  PROD_ACCESS: approved
  Approved-by: {{Orchestrator name}}
  Approved-at: {{timestamp}}
  ```
- Default: all agent runs target `staging` or `local`.

---

## 6. Kill-Switch Procedures

### Level 1: Soft Stop (task-level)
**Trigger:** Gauntlet failure limit reached, budget exceeded, BLOCKED status.
**Action:**
```bash
# 1. Agent sets status in task packet
sed -i 's/Status: IN_PROGRESS/Status: BLOCKED/' task_packets/DONE/TASK-001.md

# 2. Sentinel notified (automated)
# 3. Agent halts — no further tool calls
```

### Level 2: Agent Kill (agent-level)
**Trigger:** Sentinel decision after Level 1, security violation, or 2+ Level 1 events in one day.
**Action:**
```bash
# Kill agent process
kill -TERM {{AGENT_PID}}

# Revoke API credentials (rotate keys)
openclaw secrets rotate {{SECRET_NAME}}

# Move all in-progress task packets to BLOCKED
mv task_packets/READY/*-{{AGENT_ROLE}}-*.md task_packets/BLOCKED/

# Log event
echo "$(date -u) AGENT_KILL {{AGENT_ROLE}} reason={{REASON}}" >> logs/guardrail_events.log
```

### Level 3: Pod Shutdown (all agents)
**Trigger:** Orchestrator decision, critical security event, data breach suspicion.
**Action:**
```bash
# 1. Kill all agent processes
pkill -f "plumber|reader|red_team"

# 2. Revert all uncommitted work
git stash && git checkout main

# 3. Close all open PRs labeled agent-generated
gh pr list --label "agent-generated" --json number --jq '.[].number' | \
  xargs -I{} gh pr close {} --comment "Pod shutdown — pending security review"

# 4. Rotate all API keys used by agents
# (manual step — Sentinel executes)

# 5. Notify
echo "$(date -u) POD_SHUTDOWN reason={{REASON}} by={{SENTINEL_NAME}}" >> logs/guardrail_events.log
```

### Level 4: Emergency Rollback (production incident)
**Trigger:** Post-deploy smoke test failure, production error rate spike.
**Action (automated, runs without human):**
```bash
# 1. Revert deploy
git revert HEAD --no-edit && git push origin main
fly deploy --app {{APP_NAME}}   # or kubectl rollout undo

# 2. Verify health
for i in 1 2 3; do
  sleep 30
  curl -sf https://{{HEALTH_ENDPOINT}} && echo "HEALTH OK" && break
  echo "HEALTH CHECK FAILED attempt $i"
done

# 3. Page Sentinel
# (webhook or Telegram alert with rollback status)
```

---

## 7. Pre-Run Guardrail Checklist (agent self-check)

Run before starting any task:

```bash
python3 scripts/run_gauntlet_checklist.py task_packets/READY/{{TASK_ID}}.md --pre-flight
```

Manual checklist:
- [ ] Task packet has all required sections (checked by script)
- [ ] Agent role matches task packet `Agent:` field
- [ ] All declared env vars present and non-empty
- [ ] Branch created from latest `main` (not stale > 24h)
- [ ] No uncommitted changes in working tree
- [ ] Staging environment is healthy (ping health endpoint)
- [ ] Token budget declared and understood
- [ ] Rollback plan is documented (if touching prod data)

---

## 8. Post-Run Guardrail Checklist (before PR open)

- [ ] `gitleaks detect --source . --exit-code 1` → clean
- [ ] No files modified outside declared repo map
- [ ] All DoD items checked off
- [ ] Test matrix covered by actual tests
- [ ] Progress markers logged (no 60-min gaps)
- [ ] Token usage within budget (reported in PR description)
- [ ] Agent audit comments present in modified files
