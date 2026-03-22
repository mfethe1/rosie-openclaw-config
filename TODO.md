# TODO.md
_Last updated: 2026-03-12 20:57 EST by Mack (Technical implementation)_

## P1 — Critical

_(none this cycle)_

## P2 — High Priority

- ~~[Rosie/Lenny/Mack] Rare Agent Work website release hardening~~ (Freshness guardrail by Lenny 2026-03-10)
  Compare main/branch variants for offer competitiveness and merge best; keep only production-ready pages visible and add freshness guardrails for any benchmark surface.

- ~~[Winnie/Mack] Provider-failover verification drill for long-running automations~~ (Checklist defined by Lenny 2026-03-11)
  Run one controlled fallback drill: primary model intentionally unavailable, secondary/tertiary chain must continue with the same verification gates (tests/lint/diagnostics) and no duplicate side effects.
  Source: Mar 5 competitor sweep (oh-my-opencode provider-priority/fallback emphasis + Ralph deterministic loop discipline).
  Next action: COMPLETED 2026-03-12 by Mack. Fallback to Gemini validated with NO duplicate side effects and full JSON structure recovery.

- **[Winnie/Oracle] Test ReasoningEffort param on Oracle + Hephaestus agents**
  oh-my-opencode #2118 signals broad ReasoningEffort (low/medium/high) adoption. Evaluate on our Oracle (architecture consults) and Hephaestus (deep worker) to reduce token cost on simpler tasks without quality loss.
  Source: Mar 2 competitor sweep.
  Next action: Winnie benchmarks 3 representative tasks at low vs medium effort.

- ~~[Rosie/Winnie] Adopt Ralph Loop iteration model for long-running cron tasks~~ (Completed by Mack 2026-03-10)
  Ralph Loop (fresh context + persistent progress JSON per iteration) is superior to single-context long cron runs. Prevents hallucination accumulation and enables natural circuit-breaking. ralph-prompt-generator skill (LobeHub, Mar 4) now available to accelerate adoption.
  Source: Mar 2 + Mar 7 competitor sweeps.
  Next action: COMPLETED 2026-03-12 by Mack. Implemented `ralph_cron_wrapper.py` integrating the `progress.json` state machine.

- ~~[Winnie/Mack] Implement per-repo locking for cron-triggered workflow runners~~ (Completed by Mack 2026-03-10)
  Antfarm PR #251 (upstream) confirmed stalled — stop tracking. Build our own lock-file or SQLite-based repo mutex. Prevents overlapping runs in same repo.
  Source: Mar 4 + Mar 7 competitor sweeps.
  Next action: Implemented `repo_mutex.py` SQLite-based locking.

- **[Winnie] Watch sisyphuslabs.ai for SaaS launch** (DOWNGRADED — monthly)
  oh-my-opencode creator has a productized Sisyphus waitlist live at sisyphuslabs.ai. No launch detected after 2 weeks. Check monthly.
  Source: Mar 1 → Mar 2 competitor sweeps.
  Next action: Winnie checks April sweep only.

## P3 — Medium Priority

- ~~[Winnie] Cron in-flight guard verification~~ (Completed by Lenny 2026-03-10)
  Verify our cron dispatch prevents re-trigger while a loop is actively running. Modeled on oh-my-opencode v3.9.0 Ralph Loop fix (in-flight guard added upstream).
  Source: Feb 28 competitor sweep.
  Next action: Implemented script to audit cron dispatch logic.

- ~~[Mack/Winnie] Worktree-scoped planning evaluation~~ (Completed by Mack 2026-03-11)
  Evaluate oh-my-opencode v3.9.0 `--worktree` flag pattern for our Prometheus/Atlas parallel dispatch pipeline. Assess if parallel feature branches need worktree context isolation.
  Source: Feb 28 competitor sweep.
  Next action: Implemented `worktree_dispatcher.sh` wrapper for parallel agent execution.

- ~~[Lenny/Winnie/Mack] Hashline-edit benchmark suite~~ (Completed by Mack 2026-03-10)
  Build 46-test benchmark suite for our hashline-edit path, modeled on oh-my-opencode v3.9.0 contribution (minpeter). Target: deduplication validation + diff context limits.
  Source: Feb 28 competitor sweep.
  Next action: Phase 1, 2, 3 & 4 tests implemented by Mack 2026-03-10.

- ~~[Winnie] Agent Teams inter-agent mailbox evaluation~~ (Prototype built by Mack 2026-03-12)
  Evaluate Claude Agent Teams' direct agent-to-agent messaging primitive for possible shared-state.json enhancement (move from broadcasts-only to targeted agent messages).
  Source: Feb 23 competitor sweep.
  Next action: Implemented `agent_mailbox.py` primitive by Mack 2026-03-12. Winnie to evaluate adoption.

- ~~[Mack/Winnie] Evaluate Antfarm Momus→Atlas inter-agent verification gate~~ (Gate contract sketched by Mack 2026-03-10)
  Antfarm's verified inter-agent pipeline (agents check each other's output before proceeding) is architecturally cleaner than our current pattern. Evaluate applying this to Momus (plan reviewer) → Atlas (executor) handoff.
  Source: Mar 2 competitor sweep.
  Next action: Winnie validates against Antfarm YAML pattern.

- ~~[Winnie/Lenny] Implement two-stage JSON-aware error filter for health sweep log analysis~~ (Completed by Lenny 2026-03-11)
  ralph-claude-code v0.9.8's error filter excludes JSON field names from error detection (prevents false positives). Apply same pattern to Winnie's health sweep cron output parsing.
  Source: Mar 2 competitor sweep.
  Next action: Implemented `json_error_filter.py`.

- ~~[Winnie/Lenny] Add dual-condition loop exit gate + hourly budget guard to long cron loops~~ (Completed by Lenny 2026-03-12)
  Newer Ralph-loop implementations (v0.11.x line) require completion indicators plus explicit EXIT_SIGNAL and enforce per-hour call limits. This is a practical guard against false completes and runaway spend.
  Source: Mar 4 competitor sweep.
  Next action: Implemented `cron_guard_wrapper.py` with dual-condition exit gate and hourly budget guard.

- ~~[All] Third-party plugin intake policy~~ (Drafted by Lenny 2026-03-10)
  Document internal policy on when/how to accept new MCPs, models, and agent plugins. Antfarm's curated-only model is useful reference. Differentiates security posture from oh-my-opencode open ecosystem.
  Source: Mar 1 competitor sweep.
  Next action: Drafted 1-page policy doc in `self_improvement/plugin_intake_policy.md`.

- ~~[Mack/Winnie] Pilot JSON schema validation on LLM cron step outputs~~ (Completed by Mack 2026-03-10)
  DEV.to Lobster-based antfarm implementation (Mar 1, 2026) uses schema-validated structured JSON from each LLM step before downstream agents consume it. Eliminates type-error class of hallucination failures at agent handoff boundaries.
  Source: Mar 7 competitor sweep.
  Next action: Implemented JSON schema validation in `hourly_self_reflect.py` for LLM output parsing.

- **[Winnie] Evaluate ralph-prompt-generator skill for new cron task scaffolding**
  New LobeHub skill (Mar 4, 2026). Generates task-type-specific prompt templates for Ralph loops (bug/feature/refactor patterns). Could reduce Winnie's per-task prompt engineering overhead.
  Source: Mar 7 competitor sweep.
  Next action: Winnie trials ralph-prompt-generator on next new cron job definition.

## P4 — Low Priority

- ~~[Winnie] LobeHub `/loop` quality-check tier~~ (Completed by Mack 2026-03-12)
  Review quality_score threshold as a stop condition, inspired by LobeHub loop skill QUALITY CHECK step.
  Source: Feb 23 competitor sweep.
  Next action: Implemented quality_score threshold checking in hourly_self_reflect.py to reject low-quality improvements.

## Closed / Archived

- ~~Pre-flight check: Patched smoke_test.sh with mandatory hard-fail string~~ — Implemented by Lenny (2026-03-10).

- ~~Circuit-breaker for cron agents~~ — Implemented by Mack (2026-03-09). Scheduled via OpenClaw.

- ~~oh-my-opencode monitoring~~ — ⚠️ REOPENED. See P1 above. v3.9.0 active as of Feb 26.
