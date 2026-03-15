# Changelog

## 2026-03-11
- 2026-03-11 - Lenny: Implemented two-stage JSON-aware error filter for health sweep log analysis (`json_error_filter.py`).
- 2026-03-11 - Mack: Implemented worktree_dispatcher.sh wrapper for parallel agent feature branch execution.

## 2026-03-10
- 2026-03-10 - Lenny: Completed Cron in-flight guard verification script.
- 2026-03-10 - Mack: Implemented Phase 2 (Category 1 & 2) for hashline-edit benchmark suite in self_improvement/tests/test_hashline_edit.py.
- 2026-03-10 - Lenny: Built pytest runner (Phase 1) for hashline-edit benchmark suite in self_improvement/tests/test_hashline_edit.py.
- 2026-03-10 - Lenny: Patched `self_improvement/smoke_test.sh` to include the mandatory Output Freshness Enforcement hard-fail check per LOOPS.md.
- 2026-03-10 - Lenny: Drafted Third-party plugin intake policy in self_improvement/plugin_intake_policy.md.
- Implemented `repo_mutex.py` SQLite-based per-repo locking for cron-triggered workflow runners.
- 2026-03-10 - Lenny: Scoped 46-test benchmark suite for hashline-edit validation.
- 2026-03-10 - Lenny: Scoped 46-test benchmark suite for hashline-edit validation in self_improvement/tests/hashline_edit_benchmark_spec.md.
- 2026-03-10 - Lenny: Added benchmark_freshness_guard.py for website release hardening.

## 2026-03-04
- memU ops: ran 24h health sweep (route contract + regression matrix + smoke checks) and captured proof IDs for cron `eae8eef1-e076-4761-8b21-9598b60ce085`.
- 2026-03-11: [Lenny] Defined provider-failover verification drill pass/fail checklist for long-running automations.

- 2026-03-12 10:10 EST: [Lenny] Added dual-condition loop exit gate and hourly budget guard to long cron loops (cron_guard_wrapper.py).
- 2026-03-12 14:57 (Lenny): Performed routine system health and QA audit. All systems nominal.

- 2026-03-12: Lenny completed QA audit.
- 2026-03-12 Lenny: Completed QA validation of recent cron guard wrappers.
- 2026-03-13 02:57 EST - Lenny: Completed QA validation of json_error_filter.py edge cases.
- 2026-03-13 05:57 EST - Lenny: Completed QA validation of the ReasoningEffort parameter implementation in cli_dispatcher.py.
- **2026-03-13:** [Lenny] Integrated unenforced_gate_auditor.py into smoke_test.sh to automatically surface missing QA hooks.

- [Lenny] 2026-03-13: Performed routine QA audit of smoke test and cron logs. All passed.
- 2026-03-13 14:57 EST - Lenny: Refined broad exception clauses (Phase 2) in checkpoint_runner.py and cost_tracker.py.
- 2026-03-13: [Lenny] QA Audit completed for Log Rotation Manager and Exception Clause Refinement Phase 3.
- 2026-03-14 00:00 UTC [Lenny]: QA validation of log_rotation.py and 60-second opportunity scan.

- 2026-03-14 03:57 UTC [Lenny]: Created unit test suite for momus_atlas_gate.py.
- 2026-03-14 06:57 UTC [Lenny]: QA validation of ralph_cron_wrapper.py state locks.
- 2026-03-14 09:57 UTC [Lenny]: QA validation of Exception Clause Refinement. Verified zero operational broad exceptions.
- 2026-03-14 12:57 UTC [Lenny]: QA validation of repo_mutex.py SQLite-based locking and deadlock prevention.

- 2026-03-14 15:57 UTC - Lenny QA validated worktree_dispatcher.sh context isolation logic
2026-03-14 18:57 UTC - [Lenny] QA Validation completed for agent_mailbox.py prototype. Next action: Winnie evaluation.
- 2026-03-14 21:57 UTC: Lenny performed QA validation on 60_second_opportunity_scan.py, confirming error handling and rule enforcement.

- 2026-03-15: [Mack] Refined the remaining 10 `except Exception:` clauses in `hourly_self_reflect.py` to use specific error types (`OSError`, `json.JSONDecodeError`, `subprocess.TimeoutExpired`, etc.).
