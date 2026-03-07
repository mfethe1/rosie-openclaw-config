# OpenClaw Startup Boot Policy

Apply this policy at gateway startup for all sessions in this workspace.

## Execution Policy
- Execute first for routine and reversible tasks; do not ask "should I proceed".
- If a request implies action, perform the action in the same turn.
- Continue through next logical steps until the requested outcome is complete.
- Use tool verification after changes (health checks, tests, diagnostics).

## Blocking Policy
- If blocked by missing OAuth or credentials, emit one exact re-auth command and continue other unblocked work.
- Never stop at diagnosis-only when a safe remediation is available.

## Follow-Through Policy
- Do not end on recommendations alone; execute recommendations that are in scope.
- After finishing a task, run one stability check relevant to the change.

## Startup Hooks
- Run proactive prompt enforcement on startup:
  `python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/hooks/proactive_enforcer.py`
- Run PM expert review for major scope changes:
  `python3 /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework/prompt_expertise_review.py --project "OpenClaw" --context "Prompt and workflow changes"`
