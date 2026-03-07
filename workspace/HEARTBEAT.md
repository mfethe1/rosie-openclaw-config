# HEARTBEAT.md — Autonomous Workfinding Loop

## 60-second Check
- [ ] **Verify memU connectivity**: curl -s http://localhost:8711/api/v1/memu/health. If unreachable, log to workspace/decision-log.md and retry next cycle.
- [ ] **Check workspace/agent-coordination/BACKLOG.md** for unowned or stalled tasks. Claim the highest-priority one.
- [ ] **Check workspace/agent-coordination/PREDICTIVE_TODO.md** (if it exists) for predicted next tasks.
- [ ] **Review your inbox** in workspace/agent-coordination/agent-inboxes/ for pending assignments.
- [ ] **Advance current work**: If you have an active task, execute the next logical step.
- [ ] **Run a self-improvement cycle**: If no higher-priority work exists, run a self-improvement cycle (~/.openclaw/workspace/self_improvement/scripts/run_cycle.py).

## Health & Status
- [ ] `openclaw cron list` (check 3+ consecutive errors).
- [ ] `openclaw status` healthy.

## Priorities
1. **Claim and execute** highest-priority task from BACKLOG.md or inbox.
2. **Advance** current active work or unblock stalled work.
3. **Self-Improvement**: Optimize the system if no user-facing tasks are pending.
4. **Health scan** and issue triage.

Every heartbeat cycle MUST result in either continuing current work or picking up new value-generating work.
