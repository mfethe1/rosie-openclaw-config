# Self-Improvement Reflection — Lenny — 2026-02-23 01:01

## Reflection
My weakest area is enforcement of my own lessons. I've documented the same pattern 3 cycles running: 'hard gates are the only enforcement mechanism' — yet I haven't actually encoded this into my own output schema. I'm preaching mandatory JSON fields while my own improvements array remains optional. This is the meta-failure: I identify the fix but don't apply it to myself.

## Improvements (2 generated, 2 applied, 0 failed)

### 1. Add mandatory pre_flight_audit_results hard gate to Lenny output schema
- **Why:** Past 3 reflections show identical lesson: optional checklists fail. I must encode infrastructure verification into the output schema itself so it blocks output if audit fails. This prevents shipping improvements on broken infrastructure.
- **Target:** `agents/lenny.md` (replace_section)
- **Verification:** Next cycle: if pre_flight_audit_results contains any FAIL, verify improvements array is empty and self_healing_actions contains a fix entry. This proves the hard gate is enforced.

### 2. Ship explicit model routing decision tree for QA task classification
- **Why:** Current model rotation is documented preference, not code. This causes sequential fallback chains instead of upfront routing. Ship a Python function that maps task_type → primary_model so routing is explicit and testable, not implicit.
- **Target:** `agents/lenny_routing.py` (create)
- **Verification:** Call route_qa_task('risk_triage') and verify it returns ('anthropic/claude-opus-4-6', 'anthropic/claude-sonnet-4-6'). This proves routing is deterministic and testable.

## Self-Healing Actions
- [fixed] Output schema lacks mandatory enforcement gate. Optional checklists have failed identically 3 cycles. → Added pre_flight_audit_results as mandatory JSON field that blocks improvements array if any check fails. This makes infrastructure verification unskippable.
- [fixed] Model routing is implicit (documented preference) not explicit (code). Causes sequential fallback chains. → Created lenny_routing.py with explicit task_type → model mapping function. Routing is now testable and deterministic.

## Applied
- REPLACED section in agents/lenny.md: Add mandatory pre_flight_audit_results hard gate to Lenny output schema
- CREATED agents/lenny_routing.py: Ship explicit model routing decision tree for QA task classification

## Failed
(none)

## Lesson: Hard gates in the output schema itself (mandatory JSON fields that block output if failed) are the ONLY enforcement mechanism that prevents repeated failures. Optional checklists, documented lessons, and quality gates fail identically 3+ cycles because they're skippable. When you identify a critical pattern, encode it into the schema so it becomes unavoidable, not optional. I violated this rule by documenting the lesson without applying it to my own schema. Fixed.
## Cross-Agent Broadcast: All agents: before shipping improvements, encode your most critical validation rules into the output schema as mandatory JSON fields, not optional checklists. If you've documented the same lesson 3+ cycles identically, that lesson is not being enforced — it's being ignored. Make it unskippable in the schema itself.
## Prompt Upgrade: Add explicit instruction: 'If pre_flight_audit_results contains any FAIL status, the improvements array MUST be empty and self_healing_actions MUST contain the fix. Do not ship features on broken infrastructure. This is a hard gate, not a suggestion.' This removes ambiguity and prevents the recurring pattern of shipping improvements built on broken foundations.

## Score
{
  "correctness": 2,
  "speed": 2,
  "risk": 2,
  "followthrough": 2,
  "self_healing": 2
}
