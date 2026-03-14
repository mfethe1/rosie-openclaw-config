# Revenue Mode — Cron Spec & Blocker Analysis

**Status:** BLOCKED — needs Michael GO + prospect list  
**Owner:** Rosie (design) → Michael (approve + unblock) → Mack (implement cron)  
**Created:** 2026-02-20 by Rosie  
**Priority:** HIGH — Autonomous Goal Progress cron has flagged revenue stall 3+ consecutive nights

---

## 1. What the Revenue Mode Cron Would Do

A daily cron (8 AM ET, weekdays) that:
1. Reads `/Volumes/Edrive/Projects/agent-coordination/outreach-queue.md` — picks top 3 messages by confidence score that have NOT yet been sent.
2. For each message: resolves the `[Name]`/`[Company]` placeholder from a JiraFlow prospect list.
3. Sends via `gog gmail send` from `protelynx@gmail.com` (already functional).
4. Marks sent messages in a `outreach-sent-log.jsonl` to avoid re-sends.
5. Announces summary to Telegram: # sent, top confidence scores, any failures.

---

## 2. Why It Cannot Run Yet — Blockers

### BLOCKER A: No JiraFlow Prospect List (CRITICAL)

- `outreach-queue.md` has 30+ templated messages with `[Name]` placeholders.
- **There is no file with actual JiraFlow prospect names + email addresses.**
- FermWare has `POTENTIAL-LEADS.md` (company names, no email addresses).
- JiraFlow has zero equivalent.

**What's needed from Michael:**
- [ ] Provide a CSV or Markdown file: `JiraFlow-prospects.md` with columns: Company, Name, Email, Title, Status (not-contacted/attempted/replied).
- [ ] OR confirm that LinkedIn DMs are the channel (instead of email) — then cron uses a different send path.
- [ ] OR set a minimum batch size (e.g., "only run if 5+ prospects available").

### BLOCKER B: Send Authorization (AGENTS.md §12)

Per `AGENTS.md §12` decision threshold:
> **External communication (email/DM): Require explicit GO or 2hr timeout**

Sending real emails to real prospects is an irreversible external action. Michael must explicitly approve before the cron is enabled.

**Required signal:** Michael posts "GO revenue-mode" in Telegram, OR replies to this spec.

### BLOCKER C: FermWare vs JiraFlow Priority

- FermWare: `POTENTIAL-LEADS.md` lists 15+ named companies but no email addresses.
- JiraFlow: has email templates but no prospects.
- **Which product should Revenue Mode prioritize first?** Needs Michael's call.

---

## 3. Proposed Cron Definition (Ready to Deploy Once Unblocked)

```
Name: Revenue Mode — JiraFlow Daily Outreach
Schedule: cron 0 8 * * 1-5 (8 AM ET, weekdays)
Session: isolated
Timeout: 300s
Model: anthropic/claude-sonnet-4-6
Best-effort-deliver: true
Announce: true
To: <Coding Projects Telegram group>
```

**Prompt (draft):**
```
You are the Revenue Mode agent. Your ONLY job today: send 3 JiraFlow outreach emails.

1. Read /Volumes/Edrive/Projects/agent-coordination/JiraFlow-prospects.md
   — find the next 3 prospects with status "not-contacted" or "attempted" (attempt count < 2).
2. Read /Volumes/Edrive/Projects/agent-coordination/outreach-queue.md
   — pick the 3 highest-confidence-score messages not yet used for this prospect.
3. For each prospect: fill [Name] / [Company] placeholders, then send:
   export GOG_KEYRING_PASSWORD="openclaw"
   gog gmail send --to <email> --subject "<subject>" --body "<body>" --account protelynx@gmail.com
4. Update /Volumes/Edrive/Projects/agent-coordination/outreach-sent-log.jsonl:
   {"prospect":"<email>","message_id":<id>,"sent_at":"<iso>","variant":"A|B"}
5. Update prospect status in JiraFlow-prospects.md to "attempted".
6. Announce: "Revenue Mode: sent <N> emails. Top: <subject1>. Next run: tomorrow 8 AM."

STOP after 3 sends. Do not retry failures. Log errors to outreach-sent-log.jsonl with status "failed".
```

---

## 4. Success Criteria

- ≥3 emails sent per weekday run
- Zero duplicate sends (idempotent via outreach-sent-log.jsonl)
- Telegram summary delivered after each run
- Sent-log available for Michael to review engagement

---

## 5. Michael — Action Required

**To unblock this, please provide:**

1. **GO / NO-GO** on autonomous email sends from protelynx@gmail.com
2. **JiraFlow prospect list** (even 5 names + emails to start)
3. **Product priority** — JiraFlow first, or FermWare first?

Once you give GO, Mack can create the cron in < 15 minutes.

---

## 6. Escalation History

| Date | Source | Signal |
|------|--------|--------|
| 2026-02-20 (midnight) | 8ea09e28 Strategic Critique | "95% internal tooling; JiraFlow queue full, never sending" |
| 2026-02-20 (12:47 AM) | 98fecdc5 Goal Progress | "No agent has been tasked with deployment or outreach in the autonomous loop" |
| 2026-02-20 (03:00 AM) | 98fecdc5 Goal Progress | "Step 2: Add a revenue cron (Rosie, 45 min)" |
| 2026-02-20 (09:01 AM) | Rosie SI Cycle | Spec written; prospect list missing → blocked |
