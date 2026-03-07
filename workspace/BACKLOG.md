# BACKLOG.md - Team Action Items

## Active Tasks

### Strategic Priorities (Michael directive)
- [ ] **P0 Revenue**: Trading remains top operational priority (Rosie-led).
- [ ] **P1 Product**: Swift iOS app remains top build priority.
- [ ] **P2 Infra R&D**: Browser Relay/Auth rework initiative (high value, but must not distract from P0/P1).

### Browser Relay/Auth Rework Initiative (P2)
- [ ] **research**: Map current Browser Relay bottlenecks (attach-tab friction, session persistence, remote control constraints, auth handoff pain points).
- [ ] **design**: Propose secure auth architecture for Google/web login flows (session vault + delegated approvals + 2FA assist path).
- [ ] **prototype**: Evaluate “operatorless” modes for away-from-keyboard use (persistent browser workers + approval queue + fallback).
- [ ] **safety**: Define threat model + controls (least privilege, encrypted session tokens, no raw secret logging, explicit consent boundaries).
- [ ] **delivery**: Produce RFC + implementation backlog with effort/impact scoring and revenue tie-in.

### Unassigned
- [ ] **setup**: Establish Lenny's heartbeat schedule at :15/:45 intervals (define Lenny's focus area first)

### Lenny (@LennyFetheBot)
- [ ] **architect**: memU/Postgres memory roadmap “better-than-SuperMemory” with safety and open-source packaging plan
- [ ] **guardrail**: GitHub publish checklist to prevent secret leakage (.env scanners, allow/deny file policy, pre-push checks)

### Rosie (@RosieFetheBot)
- [ ] **lead**: Browser Relay/Auth rework triage doc (current-state issues + proposed architecture options A/B/C)
- [ ] **define**: Revenue-linked prioritization rubric so Browser Relay work does not cannibalize trading/Swift output
- [ ] **setup**: Establish heartbeat schedule at :00/:30 intervals (coordination role)
- [ ] **implement**: memU integration with Mack and Winnie coordination (PRIORITY - per Michael 23:29)
- [ ] **fix**: Implement conflict detection system for HEARTBEAT.md hash validation (CRITICAL)
- **08:00-12:00**: Execute JiraFlow outreach (10 personalized emails minimum)
- **09:30**: Trading validation (token refresh, routing, monitors, stops)
- **17:00**: Numeric review (outbound sent, response rate, demos, P&L)

### Mack (@MacklemoreFetheBot)
- [ ] **investigate**: Gateway-level Browser Relay reliability + cross-gateway orchestration feasibility (federated dispatch design)
- [ ] **spec**: Secure remote-control pattern for unattended runs (approval queue, audit logs, timeout/cancel semantics)
- [ ] **debug**: Fix Winnie's "messages.1.content.0.thinking.signature: Field required" error (SSH into Winnie and resolve)
- [ ] **setup**: Establish heartbeat schedule at :08/:38 intervals
- [ ] **setup**: Check Schwab token scripts for output location and verify token is accessible (PRIORITY - token ready per Michael 23:27)
- [ ] **implement**: memU integration with Rosie and Winnie coordination (PRIORITY - per Michael 23:29)
- [ ] **fix**: Define default autonomous behavior for split-brain/non-response scenarios
- [ ] **create**: Implementation of escalation ladder (15min → 30min → 1hr thresholds)
- Support JiraFlow backend monitoring
- Real-time trading system v3 deployment at 09:20 AM

### Winnie (@WinnieFetheBot)
- [ ] **research**: Google auth flow options for agent-operated browser sessions (session persistence vs delegated login)
- [ ] **document**: UX flow for 2FA assist via iMessage signal + one-time approval handoff without secret leakage
- [ ] **setup**: Establish heartbeat schedule at :22/:52 intervals
- [ ] **implement**: memU integration with Mack and Rosie coordination (PRIORITY - per Michael 23:29)
- [ ] **test**: Verification of cross-machine config consistency after sync
- Monitor JiraFlow frontend performance
- Test trading automation guardrails

## Completed (Last 24h)
- ✅ WhatsApp rate limit fix (10-min debounce)
- ✅ 24/7 overnight automation enabled
- ✅ JiraFlow outreach messages prepared (9 queued)
- ✅ Lane-Lock Protocol formalized (`self_improvement/GOVERNANCE.md`) - 05:10
- ✅ JiraFlow CRM tool (`crm.py`) built for prospect tracking - 05:13
- ✅ Default-approve policy implemented (auto-execute revenue tasks if blocked >2 hours)

---

*Auto-updated hourly by task extraction cron*
*Last update: 2026-02-14 23:40 EST*
