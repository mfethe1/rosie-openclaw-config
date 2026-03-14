# Offline Prompt Review — OpenClaw

Timestamp: 2026-03-02T16:56:22.862288
Context: Review agent prompts for proactive execution and output quality; return specific improvement actions

## Review Board
pm, tech_lead, engineering_manager, security, qa, red, blue, solutions_architect

## Required Checks
- PM: backlog clarity, dependency ordering, acceptance criteria quality
- Tech Lead: architecture correctness, failure modes, complexity controls
- Engineering Manager: execution realism, handoff quality, throughput bottlenecks
- Security: auth/data handling risks and safe defaults
- QA: testability and regression coverage
- Red Team: adversarial edge cases and hidden assumptions
- Blue Team: mitigation quality and residual risk
- Solutions Architect: integration contracts and boundary definitions

## Action Template
1. List top 5 prompt failures seen in recent runs.
2. Map each failure to one role check above.
3. Patch the owning prompt file with a precise rule.
4. Re-run verification (`openclaw doctor`, `openclaw health`, targeted workflow run).
5. Keep only rules that measurably improve output quality.
