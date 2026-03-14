# PREDICTIVE_TODO.md
# Auto-generated: 2026-03-04 | System: Augment Agent + OpenClaw v2026.3.2
# Purpose: Predictive task queue derived from request patterns, agent memory, TODO.md history, and system health signals.
# Format: CONFIDENCE [OWNER] Priority — Task (Rationale)
# Outcomes are logged below each task after execution.

---

## 🔴 HIGH CONFIDENCE — Execute Immediately

- [ ] **[Mack]** P1-CRITICAL — Investigate why Mack + Lenny cron outputs stalled at 2026-02-23 (10+ days ago). Check cron job status, last log lines, and shared-state for failure signals. Likely related to model allowlist or auth expiry.
  - _Basis: shared-state shows `last_mack_output: 2026-02-23`, `last_lenny_output: 2026-02-23`. All loops "confirmed running" but no recent output._
  - _Next: `openclaw jobs list | grep -E "mack|lenny"` → check cron logs → fix + verify output file written._

- [ ] **[Mack]** P1-HIGH — Verify SimpleMem LLM compression is now active after B-015 deploy.env patch. shared-state still shows `simplemem_compression_active: false`.
  - _Basis: B-015 marked complete 2026-02-20 but state not updated. Pattern: fixes often need follow-up validation._
  - _Next: Check memu_server logs for ANTHROPIC_API_KEY presence → run smoke test → update shared-state._

- [ ] **[Mack]** P1-HIGH — Implement circuit-breaker for agent cron jobs (explicit TODO, P3-MEDIUM assigned, now overdue given stalled Mack/Lenny cycles).
  - _Basis: Explicit open TODO. Stalled cycles confirm the risk is real. Pattern: infrastructure failures persist until hardened._
  - _Next: Add 5-consecutive-failure auto-disable + Telegram alert + manual re-enable command._

- [ ] **[Lenny]** P2-HIGH — Build `blocker-cleanup` script (explicit open TODO). Prune resolved blockers from shared-state.json.
  - _Basis: Explicit open TODO, LOW effort. 13/15 blockers resolved but still in state file._
  - _Next: Script reads shared-state.json, removes `resolved: true` blockers older than 7 days, atomic-writes result._

- [x] **[Rosie]** P2-HIGH — Build `decision-tracker` script (explicit open TODO). Verify D-001→D-025 implementation status.
  - _Basis: Explicit open TODO, LOW effort. 25 decisions logged, status unknown after bulk completions._
  - _Next: Cross-reference decisions/ folder vs TODO.md `[x]` items. Report unimplemented decisions._

---

## 🟡 MEDIUM CONFIDENCE — Queue for Next Cycle

- [ ] **[Mack]** P2-MEDIUM — Audit the 16 missing optional-binary skills (skill health: 37/53 PASS).
  - _Basis: shared-state `openclaw_skill_health: "37/53 PASS (16 optional-binary missing)"`. Pattern: missing binaries cause silent failures._
  - _Next: `openclaw skills list --status fail` → identify which binaries → install or document as intentionally absent._

- [ ] **[All]** P2-MEDIUM — Adopt AUTONOMY & PROACTIVITY STANDARD v2.0 (top URGENT item in TODO.md).
  - _Basis: Marked URGENT, assigned to all agents, still unchecked. Today's AGENTS.md update is partial fulfillment._
  - _Next: Each agent reads AUTONOMY_AND_PROACTIVITY.md → confirms compliance in next cycle output._

- [ ] **[Mack]** P2-MEDIUM — Validate OpenCode 1.2.16 and oh-my-opencode 3.10.0 upgrade compatibility.
  - _Basis: Both upgraded today. Pattern: minor upgrades can change prompt behavior or config schema._
  - _Next: Run `opencode run "hello"` → verify agents load → check 3.10.0 changelog for breaking changes._

- [ ] **[Winnie]** P2-MEDIUM — Evaluate U-Mem (arXiv:2602.22406) and prototype cost-aware memory cascade (explicit open TODO).
  - _Basis: Explicit Winnie TODO. Pattern: After 3+ back-to-back memory framework evals, Mack typically implements 1-2 cherry-picks._
  - _Predicted follow-on: Mack adds query-type routing to agent_memory_cli.py within 2 cycles of Winnie's report._

- [ ] **[Winnie]** P2-MEDIUM — Assess DeerFlow 2.0 super-agent harness patterns (explicit open TODO).
  - _Basis: Explicit Winnie TODO. Aligns with OpenClaw workflow enhancement pattern._

---

## 🟢 LOW CONFIDENCE — Monitor & Conditionally Trigger

- [ ] **[Mack]** P3-LOW — After Winnie completes D-025a/D-025b cherry-pick evaluation, implement foresight-writing in agent cycle prompts.
  - _Basis: D-025a/b adopted but not implemented. Triggered IF Winnie produces implementation spec._

- [ ] **[Rosie]** P3-LOW — After `decision-tracker` script ships: auto-add top-3 unimplemented decisions to TODO with owner mapping (explicit chained TODO).
  - _Basis: Explicit dependency chain in TODO.md. Triggered AFTER decision-tracker script is complete._

- [ ] **[Michael/Rosie]** P3-LOW — FermWare pivot decision (HITL required). Flagged >14 days ago.
  - _Basis: HITL_REQUIRED item. No autonomous action possible. Surfacing for human review._
  - _Trigger: Human confirms go/pause/pivot decision._

- [ ] **[Winnie]** P3-LOW — Evaluate Microsoft Agent Framework RC interop for A2A/AG-UI/MCP compatibility (explicit open TODO).
  - _Basis: Explicit Winnie TODO. Triggered AFTER circuit-breaker + cron health restored._

---

## 📊 Workflow Pattern Registry (Updated 2026-03-04)

| Trigger | Predicted Next Step | Confidence | Observed Times |
|---------|-------------------|------------|----------------|
| Winnie evaluates framework | Mack implements cherry-picks | 87% | 8/9 evals led to Mack implementation within 2 cycles |
| Code change committed | Lenny runs regression scan | 91% | Standard pattern per lenny.md |
| Script added to scripts/ | Rosie adds cron job + Mack validates | 78% | Observed in alert_escalation, awesome_memory_tracker, cost_tracker |
| TODO item completed | Rosie updates CHANGELOG.md + shared-state | 95% | Standard Rosie cycle behavior |
| Shared-state shows stale agent output | Health alert escalated | 72% | Lenny pattern, but currently broken (irony noted) |
| Version upgrade | Config compatibility audit | 80% | Observed after oh-my-opencode, OpenClaw upgrades |
| New memory benchmark evaluated | Quality score threshold updated | 65% | 3/5 Winnie evals led to benchmark gate change |

---

## 📈 Prediction Outcomes Log

| Date | Task | Predicted | Actual | Accurate? |
|------|------|-----------|--------|-----------|
| 2026-03-04 | File created | — | Baseline established | — |

_Log is updated by agents after task execution. Compare predicted vs actual to refine confidence scores._

