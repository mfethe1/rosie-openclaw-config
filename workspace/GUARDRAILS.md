# GUARDRAILS.md

Updated: 2026-02-23

Use this file as an always-on constraint layer before execution.

## Sign 1: Cron patches require verification
- Trigger: any cron edit (model, schedule, delivery, timeout)
- Instruction: run `openclaw cron list --json` and verify the patched fields immediately
- Reason: prevents silent mispatch and unknown cron ID loops

## Sign 2: Delivery failures must not loop forever
- Trigger: any announce delivery error repeats 3 times
- Instruction: stop retry loop, mark blocker with root cause, patch destination or set best-effort delivery
- Reason: avoids infinite delivery retries with invalid destinations

## Sign 3: Model failures require lane switching
- Trigger: model_not_found, auth cooldown, provider unavailable
- Instruction: switch job model to an allowed alternate lane (`openai-codex/gpt-5.3-codex` first), then retest
- Reason: restores execution continuity instead of waiting on one provider

## Sign 4: Context drift prevention
- Trigger: repetitive errors or no-progress cycle
- Instruction: reload `SOUL.md`, `HEARTBEAT.md`, and top TODO section; execute one concrete fix before summarizing
- Reason: prevents analysis loops and keeps cycles outcome-oriented

## Sign 5: Completion needs verification evidence
- Trigger: claiming task completion
- Instruction: include health/status checks and artifact paths proving success
- Reason: keeps operations trustworthy and auditable
