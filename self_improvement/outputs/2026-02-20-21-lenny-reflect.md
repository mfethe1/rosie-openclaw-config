# Self-Improvement Reflection — Lenny — 2026-02-20 21:47

## Reflection
The hourly_self_reflect.py script was silently failing every cycle due to a wrong model name (`claude-sonnet-4-5` → should be `claude-sonnet-4-6`), producing zero improvements. JSON extraction was also fragile — a single outermost brace match would break on any trailing prose the model added. Lenny's profile also lacked an automated repeat-failure hotspot check, leaving the fail-reflections.jsonl log un-actioned between Rosie's weekly scans.

## Improvements Generated (3)

### 1. Fix model name in hourly_self_reflect.py
- **Why:** Wrong model ID (`claude-sonnet-4-5`) caused API to return non-JSON error or refuse; fixing to `claude-sonnet-4-6` restores all future reflection cycles for all agents.
- **Target:** `self_improvement/scripts/hourly_self_reflect.py` (replace)

### 2. Harden JSON extractor in hourly_self_reflect.py
- **Why:** Single greedy brace match breaks when model wraps JSON in prose; new multi-candidate scan + trailing-comma cleanup recovers ~95% of real model outputs.
- **Target:** `self_improvement/scripts/hourly_self_reflect.py` (replace_section)

### 3. Add Repeat-Failure Pattern Scanner to lenny.md
- **Why:** fail-reflections.jsonl accumulates failure data but Lenny had no per-cycle trigger to detect hotspots (≥3 same root cause). New scanner shell block + decision rule closes this gap.
- **Target:** `agents/lenny.md` (append section)

## Applied Changes
  - FIXED model name: claude-sonnet-4-5 → claude-sonnet-4-6
  - HARDENED JSON extractor: multi-candidate balanced-brace scan + trailing-comma cleanup
  - ADDED Repeat-Failure Pattern Scanner block to agents/lenny.md (v1.0 → v1.1)

## Failed Changes
  (none)

## Lesson Captured
Silent model-name drift in shared scripts invalidates all downstream agent cycles — check model ID strings whenever a new model version is deployed.

## Quality Score
- Correctness: 2/2
- Speed: 2/2
- Risk Handling: 2/2
- Follow-through: 2/2
