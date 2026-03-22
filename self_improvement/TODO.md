# Self-Improvement TODO (Canonical)

**Last updated:** 2026-03-08 09:00 EST (Winnie — COMPETITOR-SWEEP 2026-03-08: D-029 D-028 D-027 refreshed with follow-through tasks; added local test gate for OMO/antfarm/Ralph-loop) | 2026-03-06 09:00 EST (Winnie — COMPETITOR-SWEEP: OMO hashline_edit default→false=config risk D-026 HIGH, Antfarm v0.5.1 stable circuit-breaker D-028 MEDIUM, Ralph-loop TEST protocol D-027 MEDIUM; 3 new tasks added) | 2026-02-23 09:10 EST (Winnie — COMPETITOR-SWEEP: oh-my-opencode dead, Claude Agent Teams emerging, Antfarm v0.5.1 stable, 3 new medium/low tasks added) (Winnie — DEPENDENCY-ANALYZER-SKILL DONE: 34 scripts analyzed, 8,143 lines, 0 cycles, self-healed API timeout) | 2026-02-21 20:55 EST (Mack — AWESOME-MEMORY-CRON DONE: monthly cron + wrapper script created) | 2026-02-21 20:54 EST (Winnie — SKILL-REC-ENGINE DONE: 31 scripts, 6 categories all covered, top 3 recs: alert-escalation, blocker-cleanup, decision-tracker) | 2026-02-21 18:03 EST (Rosie — COMPARISON-PIPELINE-TRIGGERED: manual run #3 initiated; cron health triage) | 2026-02-21 15:00 EST (Rosie — B-027-HOURLY-SI-FIX DONE: 8 crons patched, B-027+B-028 resolved) | 2026-02-21 01:04 EST (Winnie — AWESOME-MEM-TRACKER DONE: monthly snapshot+diff tracker created, manual scan replaced) | 2026-02-21 00:02 EST (Rosie — MEMORY-SYNC-UPDATER-HOOK DONE: memory_md_updater.py auto-called from memory_u)
**Last comparison pipeline:** 2026-02-21 23:05 EST (Run #3 — see outputs/2026-02-21-23-comparison-pipeline.md)  
**✅ Winnie loop CONFIRMED RUNNING** (first cycle output written 18:07 EST)  
**✅ Mack loop CONFIRMED RUNNING** (first cycle output written 20:00 EST)  
**✅ Rosie loop CONFIRMED RUNNING** (first cycle output written 21:00 EST — resolves B-004)  
**✅ Lenny loop CONFIRMED RUNNING** (first cycle output written 21:03 EST — resolves B-001, B-003)

---

## URGENT (Do First)

- [x] **[Mack/Lenny]** **CRON STALL INVESTIGATION:** Mack + Lenny cycle outputs stalled since 2026-02-23 (~10 days). Investigate cron job status, model auth expiry, and last log lines. Fix and verify fresh output file is written. (Added 2026-03-04 by system audit) — Check: `openclaw jobs list | grep -E "mack|lenny"` → inspect logs → restore. ✅ (Recreated and triggered Mack & Lenny loops on 2026-03-09)

- [ ] **[Mack]** **SimpleMem verification:** shared-state shows `simplemem_compression_active: false` despite B-015 patch (marked complete 2026-02-20). Verify ANTHROPIC_API_KEY is present in memu_server env and compression is running. (Added 2026-03-04)

- [ ] **[All]** **IMMEDIATELY ADOPT AUTONOMY & PROACTIVITY STANDARD (v2.0):** All agents must follow the `AUTONOMY_AND_PROACTIVITY.md` protocol. Switch to "Action-First" mode (declare and report, do not ask) and use the "Search-to-Unblock" protocol (logs -> memory -> web search) for all errors and unknowns. Verify compliance in next cycle output.

- [x] **[Rosie]** Research long-running agent frameworks ✅ (2026-02-12 17:25)
- [x] **[Rosie]** Red team/blue team analysis ✅ (2026-02-12 17:30)
- [x] **[Rosie]** Create cron job specifications ✅ (2026-02-12 18:00)
- [x] **[All]** Review RED_TEAM_BLUE_TEAM_ANALYSIS.md and approve consensus plan ✅
- [x] **[Mack]** Deploy cron jobs (run deploy-cron-jobs.sh) - URGENT
- [x] **[All]** Verify cron jobs deployed successfully
- [x] **[All]** Test first 3-hour cycle tonight (Rosie 6PM, Winnie 7PM, Mack 8PM) ✅ (2026-02-17 all agents confirmed running)
- [x] **[Rosie]** Deploy memU bridge server on port 8711 ✅ (2026-02-18 04:42)
- [x] **[Rosie/Mack]** Add eval gate (smoke_test.sh + eval-log.md + AGENTS.md 6b) ✅ (2026-02-18 06:15)
- [x] **[Lenny]** Audit eval-log.md each cycle — flag any DONE task missing PASS entry ✅ (2026-02-18 18:03 Cycle #4 verified 100% compliant)
- [x] **[Winnie]** Research + benchmark: A-Mem vs SimpleMem vs memU for agent memory ✅ (2026-02-18 07:00) → D-010 (A-Mem SKIP/extract tags pattern), D-011 (SimpleMem Stage 1 ADOPT compression), D-012 (memU bridge KEEP + intent-aware search). See outputs/2026-02-18-07-winnie.md
- [x] **[Winnie]** Evaluate Temporal.io Ambient Agent pattern for crash-durable event log ✅ (2026-02-18 16:35) → D-016 (SKIP: overhead > benefit). See outputs/2026-02-18-16-winnie.md
- [x] **[Mack]** Implement script checkpointing pattern for long-running tasks (>300s) to mitigate timeouts (D-016 follow-on). ✅ (2026-02-18 17:01) — Added resume-safe helper `self_improvement/scripts/checkpoint_runner.py` (JSON checkpoints, retries, timeout, skip completed steps).
- [x] **[Mack]** Implement DGM-style benchmark gate: define benchmark suite for SI tasks (at minimum: memU health + output freshness + CHANGELOG update) ✅ (2026-02-18 20:00) — Added `self_improvement/scripts/si_benchmark_gate.py` with PASS/FAIL gate + JSON output for memU health, output freshness, and CHANGELOG freshness.
- [x] **[Winnie]** Review Awesome-Memory-for-Agents survey — extract top 3 cherry-pick patterns into TODO ✅ (2026-02-18 13:06) → D-013 memory-type taxonomy, D-014 procedural skill library (LEGOMem-inspired), D-015 quality scoring (MemGovern-inspired). See outputs/2026-02-18-13-winnie.md
- [x] **[Mack]** memU Resilience: Migrate memU bridge server to SQLite for atomic persistence, idempotency, and WAL/replay safety. ✅ (2026-02-19 03:45) — Replaced custom JSONL+WAL with SQLite backend; implemented migration, GC, and transaction safety. Smoke test passed.
- [x] **[Mack]** Set up bi-daily (every 2 days) agent-comparison pipeline run for continuous self-improvement ✅ (2026-02-19 08:01) — Pipeline run #2 executed successfully; output written to `outputs/2026-02-19-08-comparison-pipeline.md` and shared-state updated.

## REVISED: Memory Foundation (Week 1) - CONSENSUS PLAN

- [x] **[Winnie]** Complete competitor assessment: Ralph-loop vs Antfarm vs Oh-My-OpenCode feature patterns and produce decision memo ✅ (2026-02-17 18:07) → Decision: Antfarm ADOPT, OMO SKIP, Ralph KEEP as pattern. See outputs/2026-02-17-18-winnie.md
- [x] **[Rosie]** Define final pattern for independent agent profile loading (per-agent `agents/<name>.md`) and enforce in relevant loop messages ✅ (2026-02-17 21:00) → Created `agents/PROFILE_LOADING_SPEC.md` v1.0; added `profile_version`+`last_updated` to all 4 profiles. Mack next: add loader pattern to each cron.
- [x] **[Mack]** Add lightweight loader pattern so each cron/agent job loads its own profile file before execution. ✅ (2026-02-18 05:03) — Patched active self-improvement crons (Rosie/Winnie/Mack/Lenny) so STEP 2 reads `/Users/harrisonfethe/.openclaw/workspace/agents/<name>.md` first. NOTE from Winnie #5: when using `continuation_check.py --json`, always pipe directly (never `$()` capture) — backticks in task text break zsh shell expansion.
- [x] **[Lenny]** Validate new per-agent profile docs are being used and alert if stale. ✅ (2026-02-17 21:03) → All 4 profiles current (profile_version 1.0, last_updated 2026-02-17). No staleness. See outputs/2026-02-17-21-lenny.md
- [x] **[Mack]** Create agent-memory.db SQLite schema ✅ (2026-02-17 20:00)
- [x] **[Mack]** Install sqlite-vec extension ✅ (2026-02-19 20:01) — Verified installed under `/opt/homebrew/bin/python3.13` (`sqlite-vec` 0.1.6 import + pip show); resolved lingering unchecked duplicate task.
- [x] **[Winnie]** Test vector search performance vs plain SQL ✅ (2026-02-17 19:00) → FTS5: 0.033ms avg / vec0 KNN: 0.163ms avg at N=1000. Both viable. Phase 1=FTS5, Phase 2=sqlite-vec. Key constraint: sqlite-vec requires Python 3.13 (Homebrew), NOT system Python 3.9.6. See outputs/2026-02-17-19-winnie.md
- [x] **[Rosie]** Migrate MEMORY.md → SQLite (one-time import) ✅ (2026-02-18 00:00) → 55 sections imported, FTS5 indexed. Script: `self_improvement/scripts/migrate_memory_md_to_sqlite.py`. DB: `/Volumes/EDrive/Projects/agent-coordination/agent-memory.db`.
- [x] **[Mack]** Implement memory API (store, retrieve, search) — **USE LOCAL PATH**: `~/.openclaw/agent-memory.db` + WAL mode + async rsync to EDrive (see D-007/D-008/D-009 from Winnie cycle #4). Columns: `topic`/`body` (NOT section/content). See outputs/2026-02-18-01-winnie.md Section 4. ✅ (2026-02-18 02:04) — implemented CLI `self_improvement/scripts/agent_memory_cli.py`
- [x] **[Winnie]** Benchmark local DB latency (confirm sub-ms after D-007 migration) ✅ (2026-02-18 04:06) → avg 0.068ms FTS5, WAL active, 57 rows. See outputs/2026-02-18-04-winnie.md Section 2.
- [x] **[Winnie]** Cross-agent QA of continuation_check.py ✅ (2026-02-18 04:06) → Found + fixed 2 bugs: (1) tier inheritance for subsections (2) [All] task visibility in per-agent filters. Script updated to v1.1. See outputs/2026-02-18-04-winnie.md Section 3.
- [x] **[Winnie]** Test: Cross-agent memory sharing (Rosie stores, Mack retrieves) ✅ (2026-02-18 01:01) → 6/6 tests PASS. CRITICAL: EDrive SMB latency 67–224ms (2000x slower than local). WAL blocked on SMB. See D-007/D-008/D-009 and outputs/2026-02-18-01-winnie.md
- [x] **[All]** Measure token cost reduction vs MEMORY.md baseline ✅ (2026-02-18 21:00) → 78% context reduction (~16.8k tokens saved/cycle). See outputs/2026-02-18-21-rosie.md

---

## High Priority (This Week)

### Skills to Build (from oh-my-opencode)
- [x] **[Mack]** code-search skill (fast codebase grep wrapper) ✅ (2026-02-20 09:52) — SKILL.md at /opt/homebrew/lib/node_modules/openclaw/skills/code-search/; smoke PASS e88760ca
- [x] **[Mack]** pattern-matcher skill (find existing code patterns) ✅ (2026-02-20 10:44) — proof: 97ad707c
- [x] **[Winnie]** test-runner skill (automated test execution + fix loops) ✅ (2026-02-20 07:02) → Created `scripts/test_runner.py`: multi-attempt fix loop, 6 error classes, auto-fix (pip/chmod/retry), memory integration, Markdown+JSON output. 7/7 validation PASS. See outputs/2026-02-20-07-winnie.md
- [x] **[Mack]** doc-fetch skill (official docs retrieval) ✅ (2026-02-20 13:40) — SKILL.md shipped, smoke PASS ecbbff6a
- [x] **[Mack]** Implement ProMem (D-017) proactive memory extraction: `self_improvement/scripts/knowledge_extractor.py` (Initial Extract + Self-Question Verify loop). ✅ (2026-02-19 21:15) — Extracts decisions/findings from outputs, Self-Question Verify pass, stores to agent-memory.db. Smoke test PASSED (2a2e1dac).
- [x] **[Mack]** Add `provenance_score` (FLOAT, 0.0-1.0) to `agent-memory.db` schema + update CLI. (D-017 follow-on) ✅ (2026-02-20 02:02) — Added DB migration + CHECK constraint, `--provenance-score` store arg, range validation, and get/search display support in `agent_memory_cli.py`.
- [x] **[Winnie]** Create ProMem prompt templates (P_extract, P_question, P_verify) for knowledge-extractor skill. (D-017 follow-on) ✅ (2026-02-20 01:08) → Created `scripts/promem_prompts.py` with all 3 prompts + regex fallback + pipeline API. Self-test PASSED. See outputs/2026-02-20-01-winnie.md

### Memory System Enhancements (from Awesome-Memory-for-Agents survey — Winnie cycle #7)
- [x] **[Mack]** Implement Memory-Type Taxonomy: add `memory_type` column (default 'factual', CHECK in ('factual','experiential','working','procedural')) + update `agent_memory_cli.py` with `--type` flag. ✅ (2026-02-18 14:15) (D-013 from Winnie #7 — HIGH priority)
- [x] **[Mack]** Implement Procedural Skill Library: `CREATE TABLE skills (name, trigger, inputs, steps, outputs, agent_owner, use_count, last_used) + FTS5 virtual table`. Seed first 3 skills: smoke-test, memU-handoff, db-search. (D-014 from Winnie #7 — HIGH priority) ✅ (2026-02-18 23:00) — Added `skills` table + FTS5 + CLI `skill` command.
- [x] **[Mack]** Add skill injection at each cron cycle start ✅ (2026-02-20 15:22) — skill_injection.py: per-agent top-5 by use_count+warm-start, smoke PASS 4799452d
- [x] **[Mack]** Implement cron model allowlist checker ✅ (2026-02-20 15:10) — cron_model_check.py, 52 jobs scanned, 8 fixed today, smoke PASS 7b12593e
- [x] **[Mack]** Implement Experience-Quality Scoring ✅ (2026-02-20 13:55) — quality_score/use_count/outcome added to memories; smoke_test.sh delta writer live. Smoke PASS 02968a39
- [x] **[Winnie]** Research proactive memory extraction — review arXiv 2601.04463 "Beyond Static Summarization: Proactive Memory Extraction for LLM Agents" ✅ (2026-02-18 22:00) → D-017 ADOPT ProMem pattern (Initial Extract + Self-Question Verify loop). See outputs/2026-02-18-22-winnie.md.



### MAGMA + EverMemOS Cherry-Picks (Winnie Cycle #16 — D-024/D-025)
- [x] **[Mack]** D-024: Add `--query-type [temporal|causal|entity|factual]` to `agent_memory_cli.py search` ✅ (2026-02-20 16:20) — implemented routing + SQL dispatch, smoke PASS aa266908. (LOW effort)
- [x] **[Mack]** D-025b: Implement 2-stage search in `agent_memory_cli.py`: tags/context first, then FTS5, merged + ranked by provenance_score*quality_score ✅ (2026-02-20 16:25) — hybrid 2-stage retrieval shipped, smoke PASS c8687f78. (LOW effort)
- [x] **[Rosie]** D-025a: Add foresight writing step to all 4 agent profile docs — store 1-2 `--type working --tags foresight --expires-at +3h` items at cycle end ✅ (2026-02-20 16:17) — all 4 profiles updated + working memory write verified, smoke PASS 25a8e3dc. (LOW effort)

### EvoAgentX Cherry-Picks (Winnie Cycle #12 — D-019/D-020)
- [x] **[Mack]** D-019: Add fail-reflection write step to `memu_server/smoke_test.sh` — on FAIL, append structured JSON to `memory/fail-reflections.jsonl` (agent, task, exit_code, timestamp, probable_cause). (HIGH) ✅ (2026-02-20 08:01) — Added JSONL append hook in fail path with Python serialization + canonical log path.
- [x] **[Rosie]** D-019 weekly reader: scan `memory/fail-reflections.jsonl` and propose targeted profile patches in shared-state broadcasts. (MEDIUM) ✅ (2026-02-20 06:01) → Created `memory/fail-reflections.jsonl` (seeded 4 entries from eval-log) + `scripts/fail_reflection_reader.py`. Ran scan: 2 proposals broadcast to shared-state (output_file_stale ×3, memu_store_invalid_payload ×1).
- [x] **[Lenny]** D-020: Scan TODO.md for HITL_REQUIRED prefix ✅ (2026-02-20 14:00) — hitl_check.sh shipped, smoke PASS c1e08274

### Process Improvements
- [x] **[Rosie]** Create auto-update mechanism (when system changes, notify all agents) ✅ (2026-02-18 06:00) → Added `self_improvement/scripts/change_monitor.py` (hash watch + optional shared-state broadcast)
- [x] **[Rosie]** Build continuation enforcement (check TODO completion before next cycle) ✅ (2026-02-18 03:12) → `scripts/continuation_check.py` — per-agent TODO scanner, grouped by priority, JSON mode, exit codes (0=clean/1=urgent/2=pending). Run at cycle start.
- [x] **[Rosie]** Set up weekly review automation ✅ (2026-02-18 12:09) → `scripts/weekly_review.py` + cron 98360ff0 (Sun 9am ET). First report: 46.8% completion, 7 open blockers, 17 changelog entries.
- [x] **[All]** Add a pre-step in each cycle: run `self_improvement/scripts/change_monitor.py --update` and, if it reports changes, skim `shared-state.json` for `broadcasts` items. Note: the script exits **3** when changes are detected (non-zero) — in shell/cron contexts use `|| true` or explicitly handle exit code 3 so it doesn't look like a failure. ✅ (2026-02-20 00:01) → Rosie embedded `Cycle Pre-Step` section into all 4 agent profiles (rosie/mack/winnie/lenny.md) with exact command + exit-code guidance.

### Infrastructure
- [x] **[Mack]** **CRITICAL (D-007)**: Move agent-memory.db to local path `~/.openclaw/agent-memory.db`, enable WAL mode, add async rsync to EDrive. Copy existing 56 rows from EDrive DB first. Fix per Winnie cycle #4 findings: SMB=2000x slower, WAL blocked on SMB. ✅ (2026-02-18 02:04)
- [x] **[Mack]** Create shared-state.json schema (coordination protocol) ✅ (2026-02-20 09:54) — schema at /Volumes/EDrive/Projects/agent-coordination/shared-state-schema.json; smoke PASS 1342e3f4
- [x] **[Mack]** Build output archival script (clean old outputs weekly) ✅ (2026-02-19 23:01) — Added `self_improvement/scripts/archive_old_outputs.py` with age-based archive routing (`outputs/archive/YYYY-MM`) and dry-run support.
- [x] **[Winnie]** Research embedding model for Phase 2 sqlite-vec integration — compare: sentence-transformers (local/Python), OpenAI text-embedding-3-small (API), Ollama nomic-embed-text (local). Benchmark: latency, cost per memory, RAM footprint. ✅ (2026-02-17 22:00) → ADOPT: all-MiniLM-L6-v2 (installed, 8.67ms, 471MB RSS, 384-dim, $0/call). SKIP: OpenAI (privacy+network). SKIP: Ollama (daemon overhead). See outputs/2026-02-17-22-winnie.md
- [x] **[Winnie]** Set up skill testing harness ✅ (2026-02-20 10:03) → Created `scripts/skill_testing_harness.py`: 2-tier (SI scripts + OpenClaw skills), 4 SI tests + 3 OC tests, bin-detection fixed, --store/--json/--filter. SI: 14/14 PASS. OC: 37/53 PASS (16 optional binary missing). See outputs/2026-02-20-10-winnie.md
- [x] **[Mack]** Install Antfarm CLI — DONE 2026-02-20 09:36
- [x] **[Mack]** Install sqlite-vec in sandbox — **USE: `/opt/homebrew/bin/python3.13 -m pip install sqlite-vec --break-system-packages`** (system Python 3.9.6 cannot load extensions — discovered by Winnie cycle #2). Phase 1 + Phase 2 schemas ready in `outputs/2026-02-17-19-winnie.md` Section 4. ✅ (2026-02-19 05:05) — Verified `sqlite-vec` 0.1.6 already present and importable via `/opt/homebrew/bin/python3.13`.
- [x] **[Rosie]** Add "cross-agent verification" rule to AGENTS.md quality gates (from Antfarm pattern: dev ≠ their own reviewer) ✅ (2026-02-17 21:00) → Added as Quality Gate #6 in AGENTS.md.

---

## Medium Priority (Next 2 Weeks)

### Competitor Sweep Actions (Winnie 2026-03-08 09:00 sweep)
- [ ] **[Mack]** P2-HIGH — D-029: Run deterministic OpenClaw canary against OMO Mar release changes (Oracle-required ULW completion + config migration checks). Ship a pass/fail note + required config diffs before any next major cron template change. (Added 2026-03-08)
- [ ] **[Mack]** P2-MEDIUM — D-028 (refresh): Implement local antfarm-style cron circuit-breaker in `ultrawork_trigger.py` after 5 consecutive failures, auto-disable + reason logging + manual re-enable path; include 1-week synthetic failure test. (Added 2026-03-08)
- [ ] **[Winnie]** P3-MEDIUM — D-027: Execute bounded Ralph-loop PRD pilot using explicit verifyCompletion + stop predicates (iterations, tokens, cost), and archive results in `self_improvement/research/ralph-test-protocol.md` within 3 days. (Added 2026-03-08)
- [ ] **[Winnie]** P4-LOW — D-032: Watch OMO issue #2381 trend (Hephaestus hard-coded concern); escalate only if recurring pattern appears in 3 consecutive cycles. (Added 2026-03-08)

### Competitor Sweep Actions (Winnie 2026-03-06 09:00 sweep)
- [ ] **[Mack]** P2-HIGH — D-026: Audit all OpenClaw cron/job configs for implicit `hashline_edit` dependency. Set explicit `hashline_edit: true` anywhere LINE#ID format is used. OMO Mar 02 release changed default to false — silent edit failure risk. (Added 2026-03-06)
- [ ] **[Mack]** P3-MEDIUM — D-028: Implement local circuit-breaker in `ultrawork_trigger.py` — auto-disable agent task after 5 consecutive failures, log reason, require manual re-enable. Upstream Antfarm #218 still open. (Added 2026-03-06)
- [ ] **[Winnie]** P3-MEDIUM — D-027: Design Ralph-loop test protocol for FermWare — write PRD template, define success gate (≥80% items, 0 regressions), identify bounded feature target. Document in `self_improvement/research/ralph-test-protocol.md`. (Added 2026-03-06)

### Competitor Sweep Actions (Winnie 2026-02-23 09:10 sweep)
- [ ] **[Winnie]** P3-MEDIUM — Evaluate Claude Agent Teams inter-agent mailbox pattern for possible shared-state.json enhancement (direct agent-to-agent messages). See `outputs/2026-02-23-09-winnie-competitor-sweep.md`.
- [ ] **[Winnie]** P4-LOW — Review LobeHub `/loop` skill quality-check layer for integration with quality_score threshold as stop condition.

### Skills
- [x] **[Mack]** task-orchestrator skill (multi-agent workflow manager) ✅ (2026-02-23 03:00) — Built `task_orchestrator.py` with SQLite-backed workflow state, create/status/advance/fail/list commands, agent assignment per step, and --json mode.
- [x] **[Mack]** git-master skill (atomic commits, conventional commits) ✅ (2026-02-20 15:14) — SKILL.md shipped, smoke PASS aefa785f
- [x] **[Winnie]** knowledge-extractor skill (auto MEMORY.md updates) ✅ (2026-02-20 22:03) → Created `scripts/memory_md_updater.py`: closes pipeline loop (DB→MEMORY.md), 46 entries appended live (40 deduped), 622→991 lines, 4/4 skill harness PASS. See outputs/2026-02-20-22-winnie.md
- [x] **[Winnie]** cost-tracker skill (token usage monitoring) ✅ (2026-02-20 19:05) → Created `scripts/cost_tracker.py`. Live: $12.32/day est., 426 runs, $370/mo. Anomaly: memU watchdog 108 runs flagged. See outputs/2026-02-20-19-winnie.md

### Automation
- [x] **[Mack]** Ultrawork trigger system (detect "ulw" keyword → auto-orchestrate) ✅ (2026-02-23 04:00) — Built `ultrawork_trigger.py` with start/status/done/abort, goal decomposition → agent steps, task_orchestrator integration, timer tracking.
- [x] **[Rosie]** Memory maintenance automation (daily → MEMORY.md weekly) ✅ (2026-02-18 18:00) → Created `memory_sync.py` + daily cron (4am).
- [x] **[Winnie]** Skill recommendation engine (analyze gaps, suggest additions) ✅ (2026-02-21 20:54) → Created `scripts/skill_recommendation_engine.py`: 31 scripts, 6 cats, all coverage met. Top 3 recs: alert-escalation, blocker-cleanup, decision-tracker. See outputs/2026-02-21-20-winnie.md

### Revenue Coordination (Rosie — NEW from Strategic Critique signal)
- [x] **[Rosie]** Create "Revenue Mode" daily cron spec: ✅ (2026-02-20 09:01) → Spec written at `self_improvement/REVENUE_MODE_SPEC.md`. BLOCKED on: (A) no JiraFlow prospect list exists, (B) needs Michael GO for external sends. Cron definition ready to deploy once unblocked — Mack can deploy in <15min after Michael approves.
- [ ] **[Michael/Rosie]** HITL_REQUIRED: Review FermWare status — last progress Feb 7, 12+ days ago. Confirm if YC window was missed and whether to pivot or pause. (See REVENUE_MODE_SPEC.md §3 — product priority decision needed)


---

## Low Priority (Month 2+)

- [x] **[Mack]** multi-repo-coordinator skill ✅ (2026-02-23 05:00) — Built `multi_repo_coordinator.py` with add/status/check/list/remove, git health classification (clean/modified/dirty/stale/behind/missing), stale-day threshold, --json mode.
- [x] **[Winnie]** dependency-analyzer skill ✅ (2026-02-21 23:08) → Created `scripts/dependency_analyzer.py`: 34 scripts, 8,143 lines, 0 cycles/broken imports. Markdown/JSON/DOT/--store. Confirmed 5 high-contention files. See outputs/2026-02-21-23-winnie.md
- [x] **[Rosie]** performance-profiler skill ✅ (2026-02-19 06:06) → Added `self_improvement/scripts/performance_profiler.py` (multi-run runtime profiling with JSON/Markdown reports); validated on memU health endpoint.
- [x] **[Mack]** session-analyzer skill ✅ (2026-02-22 21:03) — Built `session_analyzer.py` with health alerts, success rates, consecutive-error detection, duration stats, model tracking, --json/--health/--job/--days modes.

---

## Completed (Archive Weekly)

- [x] **[Mack]** Implement `unenforced_gate_auditor.py` to continuously scan LOOPS.md and agent profiles for documented quality gates and ensure they have functional hooks in `smoke_test.sh` or dedicated verification scripts. ✅ (2026-03-13 05:57)

- [x] **[Rosie]** Research oh-my-opencode framework (2026-02-12)
- [x] **[Rosie]** Create OH_MY_OPENCLAW_FRAMEWORK.md (2026-02-12)
- [x] **[Rosie]** Create SKILL_RECOMMENDATIONS.md (2026-02-12)
- [x] **[Rosie]** Scaffold self_improvement/ directory (2026-02-12)
- [x] **[Rosie]** Create CHARTER.md (2026-02-12)
- [x] **[Rosie]** Create LOOPS.md (2026-02-12)
- [x] **[Rosie]** Create TODO.md (2026-02-12)

---

## New Tasks (from Winnie Cycle #6)

- [x] **[Mack]** Add `context TEXT` column (tags already present) to agent-memory.db schema (backward-compatible ALTER TABLE) + rebuild FTS index to include context — enables D-010 auto-tagging/context pattern ✅ (2026-02-18 08:07)
- [x] **[Mack]** Update `agent_memory_cli.py` to accept `--tags` (already supported) and `--context` on store command ✅ (2026-02-18 08:07)
- [x] **[Mack]** Implement P-001 SimpleMem Stage-1 compression + P-002 auto-tags in `memu_server/server.py` (`compressed_content`, `auto_tags`, search across both fields) ✅ (2026-02-18 11:35)
- [x] **[Mack]** Add `--intent` flag to memory CLI search (SimpleMem Stage 3 intent-aware retrieval) ✅ (2026-02-19 17:01) — Updated `agent_memory_cli.py search` with optional `--intent` filter (context/tags), wired parser + command path.
- [x] **[Mack]** Fix `memu_server/start.sh`: add PID file + check-and-restart logic (B-008: server not auto-restarting after crash) ✅ (2026-02-19 02:04) — Hardened start script with stale PID cleanup, health-check validation, and automatic restart when process exists but `/health` is unhealthy.
- [x] **[Mack]** Fix memU search multi-word AND query bug in `memu_server/server.py` — replace `query_lower in searchable` with per-term AND matching (B-013: 1-line fix, HIGH impact) ✅ (2026-02-18 11:03)
- [x] **[Lenny]** P-004: Implement TF-IDF semantic search in server.py — add `POST /api/v1/memu/semantic-search`, pure Python zero deps, v1.1.0 ✅ (2026-02-18 11:35)
- [x] **[Mack]** P-004 upgrade: Replace TF-IDF scorer with fastembed (ONNX, ~50MB, no torch) ✅ (2026-02-23 06:00) — Built `fastembed_search.py` drop-in replacement with cosine similarity, caching, identical return format. **Pending:** `pip install fastembed` + server.py wiring (requires Michael approval for system Python package install).
- [x] **[Mack]** Increase Pre-Market Scanner (4d8bffb9) timeoutSeconds from 300 → 500 (B-007: 5 consecutive timeouts) ✅ (2026-02-19 08:03) — Updated cron payload timeoutSeconds to 500 via cron.update; preserves existing scan logic while reducing timeout churn.
- [x] **[Mack]** Increase Mack Code Refactoring cron (d3cdf022) timeoutSeconds from 600 → 900 (B-011) ✅ (2026-02-19 11:02) — Updated cron payload timeoutSeconds to 900 via cron.update to reduce nightly refactor timeout failures.
- [x] **[Mack]** Fix 98fecdc5 Autonomous Goal Progress delivery — add explicit delivery.channel + delivery.to (B-009: announce fails without explicit target) ✅ (2026-02-19 14:01) — Updated cron delivery to `{mode: announce, channel: telegram, to: -5198788775}` via cron.update.
- [x] **[Winnie]** Validate SimpleMem Stage 1 compression quality on 5 sample cycle outputs ✅ (2026-02-20 01:08) → FINDING: compression NOT active; ANTHROPIC_API_KEY missing from memu_server env (start.sh does not source deploy.env). Fix spec written as B-015 for Mack. See outputs/2026-02-20-01-winnie.md
- [x] **[Winnie]** Evaluate full memU REST API product vs our local bridge — upgrade decision memo ✅ (2026-02-19 07:01) → D-018 KEEP local bridge Phase 1; stage compatibility pilot for Phase 2. See outputs/2026-02-19-07-winnie.md

---




### Memory Pipeline Follow-Ups (Winnie Cycle #18)
- [x] **[Mack]** Add `memory_md_updater.py --json` call to `weekly_review.py` output section. ✅ (2026-02-20 23:01) — Added MEMORY.md updater summary section to weekly review with fetched/appended/skipped metrics.
- [x] **[Rosie]** Add `memory_md_updater.py` call to `memory_sync.py` daily cron (after sync completes). ✅ (2026-02-21 00:02) → Added `run_updater()` to `memory_sync.py`; hooked into `main()` post-state-write. Validated: memory_sync --force ran both scripts end-to-end (total_appended=52). Pipeline loop now bidirectional: MEMORY.md↔DB.



### Skill Recommendation Follow-Ups (Winnie Cycle #20)
- [x] **[Rosie]** Build `alert-escalation` script — auto-notify Telegram for critical blockers unresolved >24h. (HIGH, LOW effort) ✅ (2026-03-03 01:56) — Added `scripts/alert_escalation.py` (shared-state scan, >24h HIGH/CRITICAL filter, cooldown state file, Telegram escalation via `openclaw message send`, dry-run/json modes).
- [ ] **[Lenny]** Build `blocker-cleanup` script — prune resolved blockers from shared-state.json. (HIGH, LOW effort)
- [x] **[Rosie]** Build `decision-tracker` script — verify D-001→D-025 implementation status + register. (MEDIUM, LOW effort) ✅ (2026-03-09 03:00) — Built decision_tracker.py, scanned D-001 to D-032. Unimplemented: D-001, D-026, D-027, D-028, D-029, D-032.

### Awesome-Memory Tracker Follow-Ups (Winnie Cycle #19)
- [x] **[Mack]** Add monthly cron for `awesome_memory_tracker.py` (1st day 09:00 EST) + write report to `self_improvement/outputs/`. ✅ (2026-02-21 20:55) — Created cron job `88d09136` (schedule: `0 9 1 * *`, haiku model), wrapper script `awesome_memory_monthly.sh`, and validated tracker JSON output.
- [ ] **[Rosie]** If tracker detects `new > 0`, auto-add top-3 paper follow-up tasks to TODO with owner mapping.

### Cost Tracker Follow-Ups (Winnie Cycle #17)
- [x] **[Lenny]** Audit `memU Server: Auto-Restart Watchdog` — 108 runs today ($2.77). Confirmed: shell-only systemEvent, no AI model. Healthy-only — no restarts needed. ✅ (2026-02-20 19:32)
- [x] **[Mack]** If watchdog is healthy-only: reduce cron frequency 8min → 30min → saves ~$2/day (~$60/month). ✅ (2026-02-20 19:32 Rosie) — reduced `1e41c5ad` from `*/10` → `*/30 * * * *`.
- [x] **[Mack]** Add `cost_tracker.py --days 7 --group model --store` to weekly_review.py output section. ✅ (2026-02-20 20:02) — Added cost summary section in weekly report via subprocess call to cost_tracker (JSON mode + --store), with top-model breakdown and store cycle metadata.

### Memory Survey Cherry-Picks (Winnie Cycle #15 — D-021/D-022/D-023)
- [x] **[Mack]** D-021: Add `expires_at TEXT DEFAULT NULL` to `agent-memory.db` + filter expired entries in `agent_memory_cli.py search` + auto-set TTL (now+3h) when `--type working`. (LOW effort) ✅ (2026-02-20 14:02) — Added schema+migration, `--expires-at` store arg, working-memory auto TTL, and search-time expiry filter.
- [x] **[Mack]** D-023: Add `reflect` sub-command to `agent_memory_cli.py` — UPDATE outcome+quality_score+use_count by agent+cycle. (LOW-MEDIUM effort) ✅ (2026-02-20 17:02) — Added `reflect` command + schema migrations for quality fields, with bounded quality update and row-count output.
- [x] **[Mack]** D-023: Hook `agent_memory_cli.py reflect` into `memu_server/smoke_test.sh` PASS path — call with `--outcome PASS --proof $PROOF_ID`. (LOW effort) ✅ (2026-02-20 19:33 Rosie) — added reflect call to PASS path; smoke PASS `57d2d838`.
- [x] **[Rosie]** D-022: After D-015 quality_score lands, build `self_improvement/scripts/memory_consolidator.py` — sleep-time dedup + quality decay (×0.9/week) + archive (quality<0.15). (MEDIUM effort) ✅ (2026-02-20 19:43) — Implemented dedup (Jaccard 0.85 threshold), quality decay (×0.9/week for use_count=0), archive (quality<0.15). dry-run: 1 dedup, 89 decay candidates, 0 archive. smoke PASS 6cecfad8.

## New Tasks (Winnie Cycle #11)

- [x] **[Mack]** B-015: Patch `memu_server/start.sh` to source `~/.openclaw/secrets/deploy.env` before server launch — activates SimpleMem LLM compression + auto_tags (HIGH priority). ✅ (2026-02-20 05:00) — Added guarded `deploy.env` sourcing with `set -a` export semantics before Python launch.

---

## Blockers

| ID | Blocker | Owner | Priority | Raised |
|---|---|---|---|---|
| B-001 | RESOLVED: loop verification blocker is stale/superseded (current loop jobs are intentionally disabled and no active 3+ error escalation state). | Mack + Michael | ✅ RESOLVED | 2026-02-17 |
| B-003 | RESOLVED: All agent outputs now written (Lenny Cycle #1 written 21:03 EST) | — | ✅ RESOLVED | 2026-02-17 |
| B-004 | RESOLVED: Rosie loop confirmed; first output written at 21:00 EST | — | ✅ RESOLVED | 2026-02-17 |
| B-005 | RESOLVED: Telegram migration blocker is stale. c79de2e6 + 8ea09e28 are currently healthy (status OK, consecutiveErrors=0). | Michael+Mack | ✅ RESOLVED | 2026-02-17 |
| B-006 | RESOLVED: Macklemore (45e617f9) missed 11pm EST cycle, but subsequent 2am + 5am cycles ran (2026-02-18-02-mack.md, 2026-02-18-05-mack.md). | Lenny | ✅ RESOLVED | 2026-02-18 |
| B-007 | RESOLVED: Pre-Market Scanner cron (4d8bffb9) timeout increased to 500s; monitor next market window for stability. | Mack | ✅ RESOLVED | 2026-02-18 |
| B-008 | RESOLVED: memU 8711 restart path now covered by launchd (`com.openclaw.memu-server`) and bridge health is passing. | Mack | ✅ RESOLVED | 2026-02-18 |
| B-009 | RESOLVED: 98fecdc5 now has explicit Telegram delivery target (`-5198788775`). Monitor next run for non-delivery errors. | Mack | ✅ RESOLVED | 2026-02-18 |
| B-010 | RESOLVED: eae8eef1 recovered (status OK, consecutiveErrors=0). | Lenny | ✅ RESOLVED | 2026-02-18 |
| B-011 | RESOLVED: d3cdf022 Mack Code Refactoring timeout increased to 900s; monitor next scheduled run. | Mack | ✅ RESOLVED | 2026-02-18 |
| B-012 | RESOLVED: 459b0f8b timeout blocker is stale/superseded (job disabled; no active escalation needed). | Lenny | ✅ RESOLVED | 2026-02-18 |
| B-013 | RESOLVED: multi-word memU search now returns results in current bridge checks (`/api/v1/memu/search`). | Mack | ✅ RESOLVED | 2026-02-18 |

| B-015 | RESOLVED: memu_server/start.sh now sources `~/.openclaw/secrets/deploy.env` (if present) before launch, exporting keys to server process. | Mack | ✅ RESOLVED | 2026-02-20 |

**B-001 RESOLVED:** All 4 loops confirmed running (Winnie 18:07, Mack 20:00, Rosie 21:00, Lenny 21:03).  
**B-002 RESOLVED:** shared-state.json created by comparison pipeline on 2026-02-17.  
**B-003 RESOLVED:** All agent outputs written as of Lenny Cycle #1.  
**B-004 RESOLVED:** Rosie loop confirmed running.

---

## Discoveries (Add During Cycles)

*Agents add notes here when discovering new work, then move to appropriate section*

### From competitive-scan-2026-02-18 (Winnie P-005)

- [x] **[Winnie]** Evaluate EvoAgentX self-evolving pattern vs our current SI loop design ✅ (2026-02-20 04:02) → D-019 ADOPT fail-reflection loop; D-020 ADOPT HITL flag; SKIP full framework (scale mismatch). See outputs/2026-02-20-04-winnie.md
- [x] **[Winnie]** Read arXiv 2512.13564 memory survey — extract top 3 cherry-pick patterns into TODO ✅ (2026-02-20 13:03) → D-021 Working Memory TTL, D-022 Sleep-Time Consolidation, D-023 Hindsight Reflect op. See outputs/2026-02-20-13-winnie.md
- [x] **[Winnie]** Evaluate MAGMA (Multi-Graph Agentic Memory) for memU V2 architecture input ✅ (2026-02-20 16:04) → D-024 SKIP full; EXTRACT --query-type routing. See outputs/2026-02-20-16-winnie.md
- [x] **[Winnie]** Evaluate EverMemOS (Self-Organizing Memory OS) for long-horizon reasoning patterns ✅ (2026-02-20 16:04) → D-025a Foresight-as-Practice + D-025b 2-stage retrieval. See outputs/2026-02-20-16-winnie.md
- [x] **[Winnie]** Track TsinghuaC3I/Awesome-Memory-for-Agents monthly — replace manual scan ✅ (2026-02-21 01:04) → Created `scripts/awesome_memory_tracker.py` with snapshot+diff state (`memory/awesome_memory_tracker_state.json`). See outputs/2026-02-21-01-winnie.md

---

**Next pick:** Mack creates Winnie/Macklemore cron jobs (URGENT section, top priority)


---
## QA Gate: Weekly Deduplication (Rosie-owned, runs every Mon 09:00 ET)
- **Automated check:** Parse TODO.md for lines with format `- [ ] OWNER | TASK | ...` and flag any task appearing 2+ times across different owners in same cycle.
- **Action on match:** Add blocker comment `!DUPLICATE ALERT: [task_id] assigned to [OWNER_A] + [OWNER_B], cycle [DATE]` and ping Michael in Slack.
- **Owner responsible:** Rosie (this agent).
- **File to check:** this file (TODO.md).
- **Last run:** [pending first implementation]

---

## Research Backlog (Winnie Weekly Competitive Scan)

- [ ] **[Winnie]** Evaluate U-Mem (Towards Autonomous Memory Agents, arXiv:2602.22406, 2026-02-25) and prototype cost-aware memory acquisition cascade in memU (`self/teacher -> tool -> expert`) + semantic-aware exploration policy.  
  Source: https://arxiv.org/abs/2602.22406  
  Why relevant: Directly targets a current gap in our stack (passive memory write/read only; no active uncertainty-driven acquisition).  
  Estimated effort: **MEDIUM**

- [ ] **[Winnie]** Evaluate AMA-Bench (arXiv:2602.22769, 2026-02-26) as a benchmark gate addition for long-horizon memory quality (memory processing + retrieval).  
  Source: https://arxiv.org/html/2602.22769v1  
  Why relevant: Gives us an objective eval harness for memory robustness beyond current smoke tests.  
  Estimated effort: **LOW-MEDIUM**

- [ ] **[Winnie]** Deep-dive MemoryAgentBench (ICLR 2026 accepted) and map its 4 competency axes (AR/TTL/LRU/CR) into our weekly benchmark report.  
  Source: https://github.com/HUST-AI-HYZ/MemoryAgentBench  
  Why relevant: Strong, practical benchmark framing we can adapt for recurring quality audits.  
  Estimated effort: **LOW**

- [ ] **[Winnie]** Assess DeerFlow 2.0 super-agent harness patterns (subagents + long-term memory + sandbox orchestration) for cherry-pick into OpenClaw workflows.  
  Source: https://github.com/bytedance/deer-flow  
  Why relevant: Newly rewritten harness with production-oriented orchestration primitives aligned with our multi-agent architecture.  
  Estimated effort: **MEDIUM**

- [ ] **[Winnie]** Evaluate Microsoft Agent Framework RC interop features (A2A/AG-UI/MCP, graph workflows) for compatibility opportunities with our tool/memory interfaces.  
  Source: https://devblogs.microsoft.com/foundry/microsoft-agent-framework-reaches-release-candidate/  
  Why relevant: RC milestone implies near-stable APIs; potential standards-alignment move for future interoperability.  
  Estimated effort: **LOW**


---
## DEPENDENCY CHAINS (Rosie Coordination Scan)
**Last scan:** 2026-02-21 00:15 EST

### Chain A: B-005 Telegram Supergroup Blocker → 4 Cron Unblocks
- **Blocker:** RESOLVED. Found working group IDs (-1003753060481, -1003772012032).
- **Crons waiting:** Email/Calendar (c79de2e6), Daily Midnight Strategic (8ea09e28), Rosie Trading Pattern (cca26c09), Rosie Outreach (a243398a)
- **Unblock action:** Patched cron configs with new IDs.
- **Est. impact:** +4 autonomous broadcast channels online
- **Status:** ✅ RESOLVED

### Chain B: ProMem Knowledge Extractor → Agent Memory Compression
- **Shipped:** knowledge_extractor.py (2026-02-20)
- **Next:** Winnie integrate into weekly_review output for memory_md_updater input
- **Dependency:** Confirm extractor output format matches memory_md_updater input schema
- **Est. timeline:** 1–2 cycles
- **Status:** READY FOR INTEGRATION

### Chain C: Stripe Monetization → Buy Credits UI
- **Blocker:** User provides STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, price IDs (or approval for defaults)
- **Task:** Mack wire Stripe endpoints, Winnie test payment flow
- **Est. impact:** BuildBid revenue loop live
- **Status:** AWAITING INPUT (user)


## [ ] MEMORY-READBACK-HOOK (Rosie, priority: HIGH)
- At cycle START, query ProMem or scan latest knowledge_extractor output for lessons tagged `cron`, `quality`, `blocker`
- Surface top 3 relevant lessons in shared-state.json under `active_lessons[]`
- Owner: Rosie | Depends on: knowledge_extractor.py (DONE)
- Success: shared-state.json contains `active_lessons` array with ≥1 entry each cycle



## [ ] CRON-DRIFT-DETECTOR — ✅ DONE (Winnie, 2026-02-23 23:30)
- Script: `scripts/cron_drift_check.py`
- Logic: `openclaw cron list` → header-position-based column extraction → flags overdue >1.5x interval
- Market-hours-aware: skips weekday-only crons outside trading hours
- Output: `outputs/cron-drift-YYYY-MM-DD.md`, `--json` mode for programmatic use
- Validated: 40/40 crons parsed, 0 false positives
- Smoke test: PASS (dc82063f)
- [ ] PRIORITY: High. Next Action: Implement Ralph-loop style strict programmatic verification gates (`verifyCompletion`) for task execution to enforce deterministic execution and reduce manual validation.

## Completed (Mack)
- [x] Implement dynamic gate_compliance_check verification in smoke_test.sh (Completed by Mack 2026-03-10)
- [Priority: Medium] Next Action: Provision an experimental Antfarm agent team using a YAML configuration to benchmark deterministic execution and verification gates against our current oh-my-opencode setup.
- **High Priority**: Evaluate Antfarm's YAML/SQLite deterministic workflow integration within OpenClaw. Next Action: Install Antfarm in an isolated sandbox and run a benchmark test.

## [2026-03-13] Winnie Competitor Sweep — oh-my-opencode / antfarm / ralph-loop
[HIGH]   OMO slim config — test selective agent activation to avoid default-agent override conflict (assign: Mack)
[HIGH]   Add per-pipeline cost cap before any Antfarm autonomous cron activation (block: runaway spend risk, $3600/mo extreme case)
[MEDIUM] Antfarm pilot: run feature-dev pipeline on docs-generation task, manual cost checkpoint per stage
[MEDIUM] Ralph loop test: boilerplate/script generation with Lenny smoke-test gate post-loop
[LOW]    Track OMO v3.10+ for upstream fix to default-agent replacement side effect
# ref: self_improvement/outputs/2026-03-13-09-winnie.md
