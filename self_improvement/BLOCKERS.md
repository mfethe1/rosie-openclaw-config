# Active Blockers (Rosie QA Board)

**Last updated:** 2026-02-21 00:15 EST

## HIGH PRIORITY

### B-005: Telegram Supergroup ID Migration
- **Status:** ACTIVE — Blocking 4 cron delivery paths
- **Root cause:** GROUP_PROMOTION — group `-5112703035` promoted to supergroup; old ID invalid
- **Error:** `chat not found (chat_id=-1005112703035)` on 34+ attempts
- **Impact:** Email/Calendar, Daily Midnight Strategic, Rosie Trading Pattern, Rosie Outreach crons silent
- **Escalation to:** Michael (Telegram account owner)
- **Unblock action:** Provide new supergroup ID → patch 4 cron configs → restart gateway
- **Est. resolution time:** 15 min after input
- **Tracking:** Mack cron-allowlist-checker (task added)

### B-XXX: Stripe Monetization Config
- **Status:** ACTIVE — Blocking BuildBid buy-credits flow
- **Root cause:** INPUT_MISSING — production Stripe credentials not provided
- **Impact:** Users cannot purchase credits; monetization loop incomplete
- **Escalation to:** User (requires Stripe account keys)
- **Unblock action:** Provide STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, or approval for default pricing → Mack wire endpoints → test
- **Est. resolution time:** 30 min after input
- **Suggested defaults:** 10/$29, 50/$99, 200/$299

## MEDIUM PRIORITY

### B-017: Cron Delivery Failures to `-5198788775`
- **Status:** INVESTIGATING — "cron announce delivery failed" on 3 crons
- **Root cause:** ACCESS_LOST — bot may have lost group membership after gateway restart (2026-02-20 ~21:00)
- **Impact:** Autonomous Goal Progress, Rosie Trading Pattern, Mack Code Refactoring announcements not reaching group
- **Escalation to:** Mack (check bot group membership, resync if needed)
- **Unblock action:** Verify bot is still group member → re-add if needed → restart crons
- **Est. resolution time:** 10 min investigation + 5 min fix
