# TODO.md
_Last updated: 2026-03-07 09:00 EST by Winnie (competitor sweep)_

## P1 — Critical

_(none this cycle)_

## P2 — High Priority

- **[Rosie/Lenny/Mack] Rare Agent Work website release hardening**
  Compare main/branch variants for offer competitiveness and merge best; keep only production-ready pages visible and add freshness guardrails for any benchmark surface.

- **[Winnie/Mack] Provider-failover verification drill for long-running automations**
  Run one controlled fallback drill: primary model intentionally unavailable, secondary/tertiary chain must continue with the same verification gates (tests/lint/diagnostics) and no duplicate side effects.
  Source: Mar 5 competitor sweep (oh-my-opencode provider-priority/fallback emphasis + Ralph deterministic loop discipline).
  Next action: Winnie defines pass/fail checklist; Mack executes on one non-critical cron path.

- **[Winnie/Oracle] Test ReasoningEffort param on Oracle + Hephaestus agents**
  oh-my-opencode #2118 signals broad ReasoningEffort (low/medium/high) adoption. Evaluate on our Oracle (architecture consults) and Hephaestus (deep worker) to reduce token cost on simpler tasks without quality loss.
  Source: Mar 2 competitor sweep.
  Next action: Winnie benchmarks 3 representative tasks at low vs medium effort.

- **[Rosie/Winnie] Adopt Ralph Loop iteration model for long-running cron tasks** ⬆️ ESCALATED — schedule now
  Ralph Loop (fresh context + persistent progress JSON per iteration) is superior to single-context long cron runs. Prevents hallucination accumulation and enables natural circuit-breaking. ralph-prompt-generator skill (LobeHub, Mar 4) now available to accelerate adoption.
  Source: Mar 2 + Mar 7 competitor sweeps.
  Next action: **[SCHEDULED by Rosie]** Implementation plan documented in `agent-coordination/standards/ralph-loop-cron-migration-plan.md`. Migration of "Mack - Code Refactoring" scheduled for execution.

- ~~[Winnie/Mack] Implement per-repo locking for cron-triggered workflow runners~~ (Completed by Mack 2026-03-10)
  Antfarm PR #251 (upstream) confirmed stalled — stop tracking. Build our own lock-file or SQLite-based repo mutex. Prevents overlapping runs in same repo.
  Source: Mar 4 + Mar 7 competitor sweeps.
  Next action: Implemented `repo_mutex.py` SQLite-based locking.

- **[Winnie] Watch sisyphuslabs.ai for SaaS launch** (DOWNGRADED — monthly)
  oh-my-opencode creator has a productized Sisyphus waitlist live at sisyphuslabs.ai. No launch detected after 2 weeks. Check monthly.
  Source: Mar 1 → Mar 2 competitor sweeps.
  Next action: Winnie checks April sweep only.

## P3 — Medium Priority

- **[Winnie] Cron in-flight guard verification**
  Verify our cron dispatch prevents re-trigger while a loop is actively running. Modeled on oh-my-opencode v3.9.0 Ralph Loop fix (in-flight guard added upstream).
  Source: Feb 28 competitor sweep.
  Next action: Winnie audits cron dispatch logic.

- **[Mack/Winnie] Worktree-scoped planning evaluation**
  Evaluate oh-my-opencode v3.9.0 `--worktree` flag pattern for our Prometheus/Atlas parallel dispatch pipeline. Assess if parallel feature branches need worktree context isolation.
  Source: Feb 28 competitor sweep.
  Next action: Review oh-my-opencode v3.9.0 worktree implementation notes.

- **[Lenny/Winnie] Hashline-edit benchmark suite**
  Build 46-test benchmark suite for our hashline-edit path, modeled on oh-my-opencode v3.9.0 contribution (minpeter). Target: deduplication validation + diff context limits.
  Source: Feb 28 competitor sweep.
  Next action: Lenny scopes test cases in 1 cycle.

- **[Winnie] Agent Teams inter-agent mailbox evaluation**
  Evaluate Claude Agent Teams' direct agent-to-agent messaging primitive for possible shared-state.json enhancement (move from broadcasts-only to targeted agent messages).
  Source: Feb 23 competitor sweep.
  Next action: Winnie reviews Agent Teams mailbox API docs in 1 cycle.

- **[Mack/Winnie] Evaluate Antfarm Momus→Atlas inter-agent verification gate**
  Antfarm's verified inter-agent pipeline (agents check each other's output before proceeding) is architecturally cleaner than our current pattern. Evaluate applying this to Momus (plan reviewer) → Atlas (executor) handoff.
  Source: Mar 2 competitor sweep.
  Next action: Mack sketches gate contract; Winnie validates against Antfarm YAML pattern.

- **[Winnie] Implement two-stage JSON-aware error filter for health sweep log analysis**
  ralph-claude-code v0.9.8's error filter excludes JSON field names from error detection (prevents false positives). Apply same pattern to Winnie's health sweep cron output parsing.
  Source: Mar 2 competitor sweep.
  Next action: Winnie reviews ralph-claude-code error filter implementation.

- **[Winnie] Add dual-condition loop exit gate + hourly budget guard to long cron loops**
  Newer Ralph-loop implementations (v0.11.x line) require completion indicators plus explicit EXIT_SIGNAL and enforce per-hour call limits. This is a practical guard against false completes and runaway spend.
  Source: Mar 4 competitor sweep.
  Next action: Winnie adds a guard wrapper spec for one long-running cron job.

- **[All] Third-party plugin intake policy**
  Document internal policy on when/how to accept new MCPs, models, and agent plugins. Antfarm's curated-only model is useful reference. Differentiates security posture from oh-my-opencode open ecosystem.
  Source: Mar 1 competitor sweep.
  Next action: Draft 1-page policy doc.

- **[Mack/Winnie] Pilot JSON schema validation on LLM cron step outputs**
  DEV.to Lobster-based antfarm implementation (Mar 1, 2026) uses schema-validated structured JSON from each LLM step before downstream agents consume it. Eliminates type-error class of hallucination failures at agent handoff boundaries.
  Source: Mar 7 competitor sweep.
  Next action: Mack picks one cron step that produces structured output and adds JSON schema validation before downstream consumption.

- **[Winnie] Evaluate ralph-prompt-generator skill for new cron task scaffolding**
  New LobeHub skill (Mar 4, 2026). Generates task-type-specific prompt templates for Ralph loops (bug/feature/refactor patterns). Could reduce Winnie's per-task prompt engineering overhead.
  Source: Mar 7 competitor sweep.
  Next action: Winnie trials ralph-prompt-generator on next new cron job definition.

## P4 — Low Priority

- **[Winnie] LobeHub `/loop` quality-check tier**
  Review quality_score threshold as a stop condition, inspired by LobeHub loop skill QUALITY CHECK step.
  Source: Feb 23 competitor sweep.
  Next action: Winnie reviews LobeHub loop skill implementation when bandwidth available.

## Closed / Archived

- ~~Circuit-breaker for cron agents~~ — Implemented by Mack (2026-03-09). Scheduled via OpenClaw.

- ~~oh-my-opencode monitoring~~ — ⚠️ REOPENED. See P1 above. v3.9.0 active as of Feb 26.
