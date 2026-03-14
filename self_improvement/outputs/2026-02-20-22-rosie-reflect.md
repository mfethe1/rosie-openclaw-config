# Self-Improvement Reflection — Rosie — 2026-02-20 22:06

## Reflection
I'm writing cycle outputs AFTER smoke_test.sh in violation of my own OUTPUT FRESHNESS gate, creating timing ambiguity and delayed visibility into task completion. I'm also conflating 'handoff clarity' with volume—my outputs read as status dumps rather than crisp 'what changed / why blocked / next owner' decisions. Finally, I'm not systematically validating that TODO tasks assigned to other agents aren't being duplicated in parallel cycles, which is a core QA responsibility I own.

## Improvements Generated (3)

### 1. OUTPUT FRESHNESS — Enforce Pre-Smoke-Test Write
- **Why:** The profile states 'Write outputs/YYYY-MM-DD-HH-rosie.md IMMEDIATELY after task execution — BEFORE calling smoke_test.sh.' I've been reversing this order, delaying cycle visibility and creating a false sense of completion. Writing first ensures proof artifacts exist before validation, and timestamps reflect actual work completion, not validation completion.
- **Target:** `agents/rosie.md` (replace_section)

### 2. Handoff Clarity Template — Replace Status Dump
- **Why:** Current outputs mix infrastructure fixes, blocked items, and progress into narrative form. A decision-focused template ('DONE / BLOCKED / OPEN') with explicit owner assignment forces clarity and prevents duplicate task assignment. This directly supports my QA mandate to avoid parallel duplicate work.
- **Target:** `self_improvement/outputs/.template.md` (create)

### 3. TODO Deduplication Check — Weekly QA Gate
- **Why:** I own TODO management but have no automated check preventing Mack, Winnie, or Lenny from being assigned overlapping tasks in the same cycle. Adding a 5-minute weekly scan of TODO.md that flags 'same task assigned to 2+ agents' prevents coordination failures and waste.
- **Target:** `self_improvement/TODO.md` (append)

## Applied Changes

  - REPLACED section in agents/rosie.md: OUTPUT FRESHNESS — Enforce Pre-Smoke-Test Write
  - CREATED self_improvement/outputs/.template.md: Handoff Clarity Template — Replace Status Dump
  - APPENDED self_improvement/TODO.md: TODO Deduplication Check — Weekly QA Gate

## Failed Changes  
  (none)

## Lesson Captured
Proof artifacts and handoff clarity are not nice-to-haves; they are the entire contract of coordination. Writing the output file BEFORE validation ensures the record exists independent of whether smoke_test succeeds, and a crisp template ('what / blocked / next owner') prevents my cycle notes from becoming unactionable status blurbs. QA ownership includes preventing duplicate work, which requires a mechanical check I have not yet built.

## Quality Score
- Correctness: 2/2
- Speed: 2/2  
- Risk Handling: 1/2
- Follow-through: 1/2
