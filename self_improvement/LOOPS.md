# Self-Improvement Loops

**Continuous development via 3-hour offset cron cycles + daily/weekly reviews.**

Operational coordination standards are centralized in `/agents.md` (owner roles, model policy, handoffs, quality gates).

---

## Model Rotation Protocol (All Agents) — Updated 2026-02-19

To keep utilization and quality balanced, all cycle runs must rotate across the stack:

**Primary lane (highest capability):**
1. `google-antigravity/claude-opus-4-6-thinking` — deep reasoning, complex decisions
2. `anthropic/claude-opus-4-6` (alias: `opus`) — strategic reasoning + framing
3. `anthropic/claude-sonnet-4-6` (alias: `sonnet`) — general purpose, coordination

**Breadth lane (diverse perspectives):**
4. `google-antigravity/gemini-3-pro-high` — counter-perspective + breadth
5. `google-gemini-cli/gemini-2.5-pro` — web-grounded reasoning
6. `openai-codex/gpt-5.3-codex` — deep technical synthesis

**Speed lane (fast tasks, simple checks):**
7. `openai-codex/gpt-5.3-codex-spark` — high-signal execution + concise output
8. `anthropic/claude-haiku-4-5` (alias: `haiku`) — fast/cheap routine tasks
9. `google-gemini-cli/gemini-2.5-flash` — fast Gemini lane

**Rules:**
- If any model is unavailable, skip it and continue with remaining.
- Keep every run on **at least 2 strong models** (Opus + one Codex/Gemini).
- Alternate model order across windows to avoid single-model domination.
- Use speed lane for simple tasks to preserve strong models for hard reasoning.
- Applies to all active team agents (Rosie, Mack, Winnie, Lenny) on regular loops and ad-hoc runbooks.

**Proactive addition (2026-02-19):** Each agent loop must now run the 60-second opportunity scan (see AGENTS.md §12) BEFORE selecting a task from TODO.md.

---

## 3-Hour Cycle (Continuous)

**Before each loop execution, load both docs:**
- `TODO.md`, `LOOPS.md`, `shared-state.json`
- **Agent-specific profile:** corresponding `agents/<agent>.md` (e.g., `agents/rosie.md`, `agents/mack.md`, `agents/winnie.md`, `agents/lenny.md`)

### Rosie Loop (6:00 PM, 9:00 PM, 12:00 AM, 3:00 AM...)
**Already scheduled by Michael** ✅

**Checklist:**
1. Read TODO.md, shared-state.json, LOOPS.md
2. Run proactive hook enforcement:
   - `python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/hooks/proactive_enforcer.py`
2. Check coordination health:
   - Are Mack/Winnie blocked?
   - Any process bottlenecks?
   - Memory structure clean?
3. Pick 1 process improvement from TODO.md
4. Execute improvement
5. Update CHANGELOG.md with what changed
6. Update TODO.md (mark done, add new discoveries)
7. Write cycle notes to `outputs/YYYY-MM-DD-HH-rosie.md`
8. Update shared-state.json for next agent
9. For large prompt/workflow edits, run PM expert prompt review:
   - `python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework/prompt_expertise_review.py --project "OpenClaw" --context "Latest workflow or prompt changes"`

**Focus areas:**
- Coordination protocols
- Cron job health
- Memory organization
- Quality enforcement
- Process documentation

---

### Winnie Loop (7:00 PM, 10:00 PM, 1:00 AM, 4:00 AM...)
**Anchor:** Feb 12 2026, 7:00 PM EST (1770940800000 ms)
**Interval:** Every 3 hours (10800000 ms)

**Checklist:**
1. Read TODO.md, shared-state.json, LOOPS.md
2. Check research priorities:
   - ClawHub new skills?
   - oh-my-opencode updates?
   - Testing backlog?
3. Pick 1 research/validation task from TODO.md
4. Execute (scout skill OR validate change OR test workflow)
5. Document findings with risk assessment
6. Update CHANGELOG.md
7. Update TODO.md
8. Write cycle notes to `outputs/YYYY-MM-DD-HH-winnie.md`
9. Update shared-state.json

**Focus areas:**
- Skill scouting (ClawHub)
- oh-my-opencode monitoring (daily)
- Test validation
- Workflow templates
- Risk assessment

---

### Macklemore Loop (8:00 PM, 11:00 PM, 2:00 AM, 5:00 AM...)
**Anchor:** Feb 12 2026, 8:00 PM EST (1770944400000 ms)
**Interval:** Every 3 hours (10800000 ms)

**Checklist:**
1. Read TODO.md, shared-state.json, LOOPS.md
2. Check technical priorities:
   - Skills to implement?
   - Scripts to build?
   - Integrations needed?
   - Repos to maintain?
3. Pick 1 technical task from TODO.md
4. Build it (code, test, document)
5. Update CHANGELOG.md
6. Update TODO.md
7. Write cycle notes to `outputs/YYYY-MM-DD-HH-mack.md`
8. Update shared-state.json

**Focus areas:**
- Skill implementation
- Automation scripts
- API integrations
- Code optimization
- Infrastructure maintenance

---

## Daily Summary (08:00 EST)

**Automated job (runs daily):**

1. Compile overnight work:
   - Read all `outputs/YYYY-MM-DD-*` from last 24h
   - Read CHANGELOG.md entries from yesterday
   - Read shared-state.json
2. Generate summary:
   - Completed improvements
   - New skills added
   - Blockers identified
   - Next priorities
3. Post to Telegram Self Improvement group
4. Archive outputs older than 7 days

---

## Weekly Review (Sunday 8:00 PM)

**Coordinated job (all agents participate):**

**Agenda:**
1. Review CHANGELOG.md (last 7 days)
2. Assess metrics:
   - Skills added this week?
   - Autonomy rate improving?
   - Repeat mistakes eliminated?
   - Deploy time trending down?
3. Update CHARTER.md if needed
4. Identify next week's priorities
5. Update TODO.md with weekly goals
6. Post weekly summary to Telegram

---

## oh-my-opencode Monitoring (Daily, 9:00 AM)

**Winnie's responsibility:**

1. Check oh-my-opencode GitHub for updates:
   ```bash
   cd /tmp && git clone https://github.com/code-yeongyu/oh-my-opencode.git oh-my-opencode-latest
   diff -r /tmp/oh-my-opencode /tmp/oh-my-opencode-latest
   ```
2. Identify new features/improvements
3. Assess: Should we adopt?
4. Add to TODO.md with priority
5. Document in `outputs/oh-my-opencode-monitoring-YYYY-MM-DD.md`

**What to look for:**
- New agents (Oracle, Librarian patterns)
- New hooks (quality enforcement)
- New MCPs (tool integrations)
- Architecture changes (orchestration patterns)
- Bug fixes (avoid same issues)

---

## Emergency Loop (On-Demand)

**Trigger:** Critical blocker, system failure, security issue

**Any agent can invoke:**
1. Post to Telegram immediately
2. Document in TODO.md as URGENT
3. Update shared-state.json with blocker flag
4. Work until resolved (don't wait for next cycle)
5. Post resolution to Telegram
6. Update CHANGELOG.md with incident + fix

---

## Anti-Patterns (What NOT to Do)

❌ **Don't:** Skip TODO.md read (you'll duplicate work or miss context)
❌ **Don't:** Work outside your lane without coordination
❌ **Don't:** Stop work halfway (continuation enforcement)
❌ **Don't:** Skip CHANGELOG.md updates (we lose audit trail)
❌ **Don't:** Spam Telegram with routine updates (workspace-first)
❌ **Don't:** Deploy without testing (Winnie validates first)
❌ **Don't:** Ignore shared-state.json (coordination breaks)

---

**These loops ensure 24/7 continuous improvement with perfect coordination.**


## CRON PATCH VERIFICATION LOOP (Rosie — 2026-02-21)
After ANY cron model/payload/delivery patch:
1. Apply patch via `openclaw cron edit <id>`
2. Wait 2 minutes
3. Run `openclaw cron logs <id> --limit 3` — confirm no error in latest entry
4. If error persists: escalate to B-board with cron ID + error text
5. Write proof line in output file: `CRON-VERIFY: <id> OK|FAIL <timestamp>`
Never mark a cron patch DONE without step 3 logged.


## Rosie Quality Gates (Run Every Cycle)

1. **Output Freshness**
   - [ ] Main task execution complete
   - [ ] `outputs/YYYY-MM-DD-HH-MM-rosie.md` written with timestamp, changes, blockers, next owner
   - [ ] Output file committed to git
   - [ ] `smoke_test.sh` run AFTER output committed

2. **Cron Patch Verification** (if any cron edited this cycle)
   - [ ] Wait 2 minutes after patch deployment
   - [ ] Run `openclaw cron logs <id> --limit 3` for EACH patched cron
   - [ ] Verify successful execution OR delivery confirmation
   - [ ] If model error or delivery failure: add to blockers board with proof artifacts
   - [ ] Record verification results in output file under "Cron Patch Verification" section

3. **State Change Verification**
   - [ ] At least one of: TODO updated, output file written, shared-state changed
   - [ ] "What changed / why blocked / next owner" explicitly recorded
   - [ ] No duplicate task assignments in same cycle

4. **Broadcast Ingestion** (run before picking task)
   - [ ] `change_monitor.py --broadcast --update` executed
   - [ ] Exit code checked (0=no changes, 3=changes detected)
   - [ ] Broadcasts acknowledged if present

## Rosie Quality Gates (run every cycle)

- [ ] At least one proof artifact exists: TODO.md update OR output file OR shared-state.json change
- [ ] Output file written to `outputs/YYYY-MM-DD-HH-MM-rosie.md` BEFORE smoke_test.sh
- [ ] Output file committed to git BEFORE smoke_test.sh
- [ ] "what changed / why blocked / next owner" explicitly recorded in output
- [ ] No task duplication: tasks assigned to others are not also claimed by Rosie in same cycle
- [ ] **CRON PATCH VERIFICATION:** If any cron was edited this cycle, run `self_improvement/scripts/cron_patch_verifier.sh <cron_id...>` and attach proof artifacts to output file. Missing verification = incomplete cycle.
- [ ] Change monitor run and broadcasts acknowledged before task selection

## Per-Cycle Checklist

Every agent must complete ALL items before marking a cycle done:

### Rosie (Coordinator/QA)
- [ ] Change monitor run and broadcasts ingested
- [ ] Task selected from TODO.md (not duplicated from another agent this cycle)
- [ ] Task executed with proof artifact
- [ ] `outputs/YYYY-MM-DD-HH-MM-rosie.md` written IMMEDIATELY after execution (before smoke_test.sh)
- [ ] Output file committed to git
- [ ] TODO.md updated (status, timestamp, owner)
- [ ] shared-state.json updated with handoff
- [ ] CHANGELOG.md line appended
- [ ] smoke_test.sh run — must PASS (output freshness hard blocker enforced)
- [ ] **gate_compliance_check:** List which profile quality gates were followed this cycle with proof artifact references:
  - OUTPUT FRESHNESS: [output file path or FAILED]
  - CRON PATCH VERIFICATION: [cron log proof or N/A]
  - Verify TODO/output/shared-state: [which of the three were updated]
- [ ] **unenforced_gates_audit:** List any quality gates in rosie.md that still lack enforcement (no checklist entry, no verification script, no smoke_test hook). For each: proposed enforcement tier (checklist/script/smoke_test).

### All Agents
- [ ] No task duplication with other agents this cycle
- [ ] cross_agent_broadcast filed if lesson applies to others
- [ ] Blockers escalated to blockers board with proof artifacts (not just noted in output)
- [ ] gate_compliance_check completed in reflection JSON output

## Winnie Cycle Checklist

### Pre-Task (run before ANY research task)
- [ ] Run change_monitor.py --broadcast --update; ack any Exit 3 broadcasts
- [ ] Run model_health_check.py; if Exit 3 → escalate to Mack, use fallback rotation
- [ ] **gate_compliance_check**: List which quality gates from winnie.md were followed THIS cycle with proof artifact refs
  - Evidence-first (≥2 sources per recommendation): _____________
  - Competitor assessment format (pros/cons/cost/risk/decision): _____________
  - Adopt-now/sandbox/skip classification: _____________
  - Output file written to outputs/YYYY-MM-DD-HH-winnie.md: _____________
- [ ] **unenforced_gates_audit**: List any quality gates lacking enforcement mechanisms
  - Gate: _____________ | Missing: checklist/script/smoke_test | Proposed fix: _____________

### Post-Task
- [ ] Output file written and timestamped (smoke_test.sh freshness gate will hard-fail if >75min old)
- [ ] call_llm() retry+fallback confirmed active (check hourly_self_reflect.py has FALLBACK_CHAIN)
- [ ] Any new tool/API validated against ≥2 independent sources before recommendation
- [ ] cross_agent_broadcast filed if lesson applies to Mack/Rosie/Lenny

## Cycle Checklist
<!-- Patched 2026-02-22 by Rosie: added gate_compliance_check + infrastructure_audit as mandatory items -->

### Pre-cycle (run before picking task)
- [ ] Run change_monitor.py and ingest broadcasts
- [ ] Read shared-state.json for blockers and handoffs
- [ ] Confirm no duplicate task assignments from prior cycle

### Execution
- [ ] Complete main task with proof artifact (file written or command output captured)
- [ ] Write `outputs/YYYY-MM-DD-HH-MM-rosie.md` IMMEDIATELY after task — BEFORE smoke_test.sh
- [ ] Commit output file to git

### Quality gates (MANDATORY — not optional)
- [ ] **gate_compliance_check:** List which quality gates from rosie.md profile were followed this cycle, with proof artifact references. Surface any gate that was skipped.
- [ ] **infrastructure_audit:** Verify (1) call_llm() in hourly_self_reflect.py has retry+fallback (check for 'fallback_model' in function body), (2) smoke_test.sh has OUTPUT FRESHNESS hard-fail block (check for 'HARD FAIL' string), (3) LOOPS.md has gate_compliance_check checklist item (this entry). Record pass/fail for each.
- [ ] **infrastructure_patch_proof:** If any infrastructure file was patched this cycle, paste first 5 lines of patched function as proof in output file.

### Post-cycle
- [ ] Run smoke_test.sh — must PASS (OUTPUT FRESHNESS hard-fail will catch missing output)
- [ ] Update TODO.md: mark done, add next task, update timestamp
- [ ] Write changelog line to CHANGELOG.md
- [ ] Update shared-state.json with next owner and handoff note
- [ ] Verify at least one of: TODO updated, output file written, shared-state changed

## Pre-Flight Checks

**MANDATORY—cycle cannot proceed without passing all three:**

- [ ] **Infrastructure Audit:** Verify `call_llm()` in `scripts/hourly_self_reflect.py` has: (1) explicit timeout 30-45s, (2) retry loop with exponential backoff (3+ attempts), (3) fallback to different provider on final attempt. If ANY missing, STOP and patch before generating improvements. Report pass/fail in output JSON `pre_flight_audit_results` field.
- [ ] **Output Freshness Enforcement:** Verify `smoke_test.sh` line 42+ contains hard-fail check: `if [ ! -f outputs/YYYY-MM-DD-HH-MM-rosie.md ] || [ $(date +%H) != $(grep -o '[0-9]\{2\}-[0-9]\{2\}$' outputs/YYYY-MM-DD-HH-MM-rosie.md | tail -1 | cut -d- -f2) ]; then exit 1; fi`. If missing, patch it. Report status in `pre_flight_audit_results`.
- [ ] **Gate Compliance Checklist:** This LOOPS.md section must contain at least 3 enforceable checklist items (not prose). If any item lacks a corresponding smoke_test.sh hook or verification script, add the hook. Report count in `pre_flight_audit_results`.
