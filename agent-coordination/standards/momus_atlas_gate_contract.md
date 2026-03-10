# Momus → Atlas Inter-Agent Verification Gate Contract

## Overview
This document sketches the proposed verification gate contract between the Momus (Plan Reviewer) and Atlas (Executor) agents, based on the Antfarm verified pipeline architecture. This gate ensures that Atlas only executes plans that have been fully validated by Momus, eliminating a class of hallucination and incomplete-plan failures.

## 1. Handoff Payload Schema (JSON)
When Momus completes a plan review and hands off to Atlas, the payload must conform to the following JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Momus to Atlas Handoff",
  "type": "object",
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "Unique identifier for the execution plan."
    },
    "status": {
      "type": "string",
      "enum": ["APPROVED", "REJECTED", "NEEDS_REVISION"],
      "description": "Momus' final decision on the plan."
    },
    "plan_hash": {
      "type": "string",
      "description": "SHA-256 hash of the final plan content to ensure immutability."
    },
    "required_skills": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of required tools/skills for Atlas to use."
    },
    "acceptance_criteria": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Explicit criteria that Atlas must satisfy to mark the task complete."
    },
    "momus_signature": {
      "type": "string",
      "description": "Cryptographic or verified signature from Momus."
    }
  },
  "required": ["plan_id", "status", "plan_hash", "acceptance_criteria"]
}
```

## 2. Gate Protocol (Atlas Pre-Execution Check)
Before Atlas begins execution, it must run the `momus_gate_check` routine:
1. **Schema Validation**: Verify the handoff payload against the JSON schema.
2. **Status Check**: Execution is ONLY permitted if `status == "APPROVED"`.
3. **Immutability Check**: Atlas re-hashes the provided plan document and compares it to `plan_hash`. If there is a mismatch, the execution is aborted.
4. **Skill Availability Check**: Verify all `required_skills` are active in Atlas' current tool profile.

## 3. Post-Execution Gate (Atlas to Momus/QA)
Once Atlas finishes, it returns an execution report mapping back to the `acceptance_criteria` provided in the original contract.
```json
{
  "plan_id": "<plan_id>",
  "status": "COMPLETED",
  "criteria_met": [
    {"criterion": "...", "proof": "filepath or log reference"}
  ]
}
```

## Next Steps
- **Winnie**: Validate this contract against the upstream Antfarm YAML pattern.
- Incorporate this gate into `hourly_self_reflect.py` as a distinct module for Swarm tasks.
