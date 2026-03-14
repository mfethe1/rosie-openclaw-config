# Security Release Criteria

**Version:** 1.0  
**Last Updated:** 2026-03-01  
**Owner:** Rosie (self-improvement security pipeline)

---

## Overview

All code, skills, and agent configurations that reach production must pass the **Production Release Gate** (`release_gate.py`). This document defines what must pass, who is responsible, how to run the checks, and the escalation path when a check fails.

---

## Mandatory Checks

All checks below must have status `pass` or `skip` (skips only allowed when the check type does not apply to the release). Any `fail` blocks release.

---

### 1. AST Security Scan

| Field | Value |
|-------|-------|
| **Script** | `skill_auditor.py <target_dir> --json` |
| **Tool** | `release_gate.py` check step 1 |
| **Owner** | Hephaestus (automated), Rosie (sign-off) |
| **Responsible human** | Michael Fethe |
| **Pass criteria** | Zero HIGH-severity findings in the AST scan output |
| **Fail criteria** | Any finding with `severity == "HIGH"` |
| **Skip allowed** | Only if target directory contains no Python files |

**What it checks:**  
Static analysis of Python source code for dangerous patterns: unguarded `eval()`, `exec()`, unsafe deserialization, hardcoded credentials, and other HIGH-severity code risks.

---

### 2. Docker Security Audit

| Field | Value |
|-------|-------|
| **Script** | `docker_security.py audit <Dockerfile>` |
| **Tool** | `release_gate.py` check step 2 |
| **Owner** | Hephaestus (automated), Rosie (sign-off) |
| **Responsible human** | Michael Fethe |
| **Pass criteria** | All Dockerfiles include `USER nonroot` and `--cap-drop=ALL` |
| **Fail criteria** | Any Dockerfile missing `USER nonroot` or missing cap-drop |
| **Skip allowed** | If no Dockerfiles exist in the target directory |

**What it checks:**  
Container hardening — ensures no containers run as root and Linux capabilities are dropped.

---

### 3. State Machine Validation

| Field | Value |
|-------|-------|
| **Script** | `state_machine_validator.py <file.xml>` |
| **Tool** | `release_gate.py` check step 3 |
| **Owner** | Oracle (architecture review), Rosie (sign-off) |
| **Responsible human** | Michael Fethe |
| **Pass criteria** | All XML state machine files have valid transitions, no orphaned states |
| **Fail criteria** | Any invalid transition or structural error in XML files |
| **Skip allowed** | If no `.xml` files exist in the target directory |

**What it checks:**  
Agent state machine correctness — verifies that all declared state transitions are reachable and valid before deploying agent workflow changes.

---

### 4. BCCS Consensus Verification

| Field | Value |
|-------|-------|
| **Result file** | `bccs_result.json` in target dir, or `verification_result.json`, or `logs/bccs_last_result.json` |
| **Tool** | `release_gate.py` check step 4 |
| **Owner** | Critic weight trainer / BCCS subsystem |
| **Responsible human** | Michael Fethe |
| **Pass criteria** | `decision == "commit"` AND `μ ≥ 0.82` |
| **Fail criteria** | `decision == "reject"`, `μ < 0.82`, or no result file found |
| **Skip allowed** | **Never** — all releases require BCCS sign-off |

**What it checks:**  
Byzantine Consensus Check System (BCCS) multi-agent agreement. A quorum of internal verification agents must have agreed this release is safe (`μ ≥ 0.82`). This prevents any single compromised agent from approving a bad release.

**To generate a BCCS result:**
```bash
python3 critic_weight_trainer.py verify <target_dir>
# Result written to: logs/bccs_last_result.json
```

---

### 5. Test Suite

| Field | Value |
|-------|-------|
| **Command** | `python3 -m pytest <target_dir> -q --tb=short` |
| **Fallback** | `python3 <script>.py --test` for each script |
| **Tool** | `release_gate.py` check step 5 |
| **Owner** | Hephaestus (writes tests), Rosie (gates) |
| **Responsible human** | Michael Fethe |
| **Pass criteria** | Zero test failures |
| **Fail criteria** | Any test failure or unhandled exception during `--test` |
| **Skip allowed** | If no `.py` files in target dir (not expected) |

**What it checks:**  
Functional correctness — all unit/integration tests and self-tests must pass before release.

---

## How to Run the Full Gate

```bash
# Full gate check on a target directory
python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/security/release_gate.py check <target_dir>

# Show last gate result
python3 release_gate.py report

# Self-test the release gate itself
python3 release_gate.py --test
```

**Exit codes:**
- `0` — Gate PASSED (all checks pass or skip)
- `1` — Gate FAILED (one or more checks failed)

**Report format** (JSON):
```json
{
  "gate": "pass|fail",
  "target_dir": "/path/to/target",
  "timestamp": "2026-03-01T20:00:00Z",
  "checks": [
    {"name": "ast_scan", "status": "pass|fail|skip", "details": "..."},
    {"name": "docker_audit", "status": "pass|fail|skip", "details": "..."},
    {"name": "state_machine", "status": "pass|fail|skip", "details": "..."},
    {"name": "bccs_consensus", "status": "pass|fail", "details": "..."},
    {"name": "test_suite", "status": "pass|fail|skip", "details": "..."}
  ]
}
```

Last report saved to: `logs/last_gate_report.json`

---

## Guardrail Integration

The C9 Guardrail (`guardrail.py`) must be active during all agent execution:

```python
from guardrail import Guardrail
g = Guardrail()

# Before any agent file write:
result = g.check(action="write_file", target=path, content=content)
if not result["allowed"]:
    raise SecurityError(result["reason"])

# Before any agent command execution:
result = g.check(action="run_command", target=command)
if not result["allowed"]:
    raise SecurityError(result["reason"])
```

Blocked actions are logged to: `logs/guardrail-YYYY-MM-DD.jsonl`

---

## Escalation Path

When a gate check fails, follow this escalation path in order:

| Step | Action | Owner |
|------|--------|-------|
| **1. Investigate** | Read the `details` field in the gate report. Understand the root cause. | Rosie / Hephaestus |
| **2. Fix and re-run** | Fix the issue in the target directory. Re-run `release_gate.py check`. | Hephaestus |
| **3. Consult Oracle** | If fix is unclear after 2 attempts, escalate to Oracle for architecture review. | Rosie |
| **4. Human review** | If Oracle cannot resolve, halt release and notify Michael via Telegram. | Rosie → Michael |
| **5. Manual override** | Only Michael can explicitly approve a failing gate. Requires written sign-off below. | Michael Fethe |

**Critical rule:** No automated system may bypass the gate. Manual overrides require human sign-off.

---

## Pre-Release Checklist

Before running the gate, confirm:

- [ ] All new code has been committed to the target directory
- [ ] BCCS verification has been run and result file is present
- [ ] All `--test` flags have been manually verified on new scripts
- [ ] No hardcoded secrets or credentials in new files
- [ ] Docker changes (if any) include `USER nonroot` and `--cap-drop=ALL`

---

## Sign-Off Template

Copy and complete this template when releasing to production:

```
PRODUCTION RELEASE SIGN-OFF
============================
Date:          ___________
Target dir:    ___________
Gate result:   PASS / FAIL (circle one)
Gate report:   logs/last_gate_report.json @ <timestamp>

Checks:
  [ ] AST Scan           PASS / SKIP
  [ ] Docker Audit       PASS / SKIP
  [ ] State Machine      PASS / SKIP
  [ ] BCCS Consensus     PASS (μ = ___)
  [ ] Test Suite         PASS

Override (if any check failed):
  Reason: ___________
  Approver: Michael Fethe
  Signature: ___________

Released by: ___________
```

---

## Appendix: File Locations

| File | Purpose |
|------|---------|
| `release_gate.py` | Main gate script |
| `guardrail.py` | C9 guardrail for runtime action blocking |
| `skill_auditor.py` | AST security scanner |
| `docker_security.py` | Dockerfile auditor |
| `state_machine_validator.py` | XML state machine validator |
| `critic_weight_trainer.py` | BCCS consensus engine |
| `logs/last_gate_report.json` | Last gate result |
| `logs/guardrail-YYYY-MM-DD.jsonl` | Daily blocked-action log |
| `logs/bccs_last_result.json` | Last BCCS verification result |
