# Self-Improvement Reflection — Winnie — 2026-02-23 05:58

## Reflection
My research and vetting workflow lacks a structured evidence-collection template that forces adversarial review before recommendations ship. I'm generating recommendations without a consistent framework to challenge my own conclusions, which means weaker vetting quality and slower convergence to high-confidence verdicts.

## Improvements (2 generated, 2 applied, 0 failed)

### 1. Evidence-Driven Recommendation Template with Built-In Adversarial Review
- **Why:** Ensures every recommendation includes: (1) primary evidence, (2) counter-evidence, (3) risk assessment, (4) cost/maintenance burden. This forces adversarial thinking before output and reduces recommendation reversals by enforcing structured challenge loops.
- **Target:** `agents/winnie_templates.md` (create)
- **Verification:** Before shipping any recommendation in next research task, validate it against this template. If any required section is missing or generic, reject output and re-run analysis.

### 2. Dependency Validation Checklist — Pre-Research Gate
- **Why:** My profile documents dependency validation as a core responsibility but has no executable checklist. This creates a gap where external tools are researched without validating their own upstream dependencies. Adding a pre-research gate ensures I catch hidden dependency chains before recommending adoption.
- **Target:** `agents/winnie_checklists.md` (create)
- **Verification:** Next research task: apply checklist to first 3 tools evaluated. Confirm counter-evidence section includes dependency health findings.

## Self-Healing Actions
- [fixed] Profile documents 'evidence-first' strategy but no template enforces it; recommendations ship without adversarial review → Created winnie_templates.md with required sections (Primary Evidence, Counter-Evidence, Risk, Maintenance, Confidence, Fallback). Next task will validate against this before output.

## Applied
- CREATED agents/winnie_templates.md: Evidence-Driven Recommendation Template with Built-In Adversarial Review
- CREATED agents/winnie_checklists.md: Dependency Validation Checklist — Pre-Research Gate

## Failed
(none)

## Lesson: A responsibility documented in a profile without an executable checklist or template is a responsibility that is not being performed. The fix is not better documentation—it is a concrete, blocking template or checklist that is consulted BEFORE output is generated. Documentation + template + pre-output validation = performed. Documentation alone = skipped.
## Cross-Agent Broadcast: All agents: Audit your profile for documented responsibilities or strategies (e.g., 'evidence-first', 'adversarial review', 'dependency validation'). For each, create an executable checklist or template and integrate it into your pre-output validation flow. If a responsibility is documented but has no corresponding checklist that blocks output if violated, that responsibility is being skipped. This cycle, encode each documented responsibility into a blocking template.
## Prompt Upgrade: Add a new section: 'DOCUMENTED_RESPONSIBILITIES' listing each claimed strategy/responsibility with its corresponding executable template/checklist file. Next reflection cycle, audit this section first—if any responsibility lacks a checklist file, flag it as a blocker before generating improvements.

## Score
{
  "correctness": 2,
  "speed": 2,
  "risk": 2,
  "followthrough": 2,
  "self_healing": 2
}
