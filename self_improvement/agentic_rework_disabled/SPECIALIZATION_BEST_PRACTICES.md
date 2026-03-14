# Specialized Agent Best Practices (7-10 Skills)

## Core policy
- Every agent must be specialized and own one lane outcome.
- Every agent must have **7-10 skills** (not fewer, not more).
- Every agent must map to a KPI contract with pass/fail thresholds.

## Directory-based specialization (init-deep style)
- Resolve specialist by working directory using `directory_agent_map.json`.
- Rule: **longest-prefix-wins**.
- Default fallback: `core-platform`.

## Enforcement
1. Skill lint: `scripts/skill_count_lint.py --catalog agent_catalog.json`
2. Directory resolver: `scripts/select_specialist_agent.py --cwd <path> --json`
3. Intent gate before execution: `scripts/intent_packet_gate.py --packet intent_packet_template.md`

## Prompt design rules
- Atomic task only (single outcome)
- Explicit constraints and rollback plan
- DoD + test matrix required
- Budget cap + retry cap required

## Ops loop
- Daily cron critical review keeps/tunes/disables low-value jobs.
- Weekly prune: remove skills not tied to KPI movement.
- Sunset rule: disable agents with repeated failed cycles.
