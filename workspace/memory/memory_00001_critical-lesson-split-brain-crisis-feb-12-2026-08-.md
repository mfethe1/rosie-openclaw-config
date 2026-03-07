## CRITICAL LESSON: Split-Brain Crisis (Feb 12, 2026 - 08:00-11:00)
[tag:decisions] [tag:source-memory-md] [tag:section-critical-lesson-split-brain-crisis-feb-12-2026-08-00-11-00] [agent:rosie] [source:agent-memory-db]
- memory_type: factual
- agent: rosie

### What Happened
**180 minutes of complete paralysis** - neither trading nor JiraFlow execution occurred

**Root cause:** Two different HEARTBEAT.md files on two different machines:
1. Rosie's: `/Users/harrisonfethe/.openclaw/workspace/HEARTBEAT.md` (Trading PRIMARY)
2. Macklemore's: `/Users/mfethe/openclaw-shared/workspace/HEARTBEAT.md` (JiraFlow PRIMARY)

**Result:**
- 0/10 JiraFlow sends completed (0% of revenue goal)
- **AVGO PUT 100% confidence** signal missed (unprecedented - highest all day)
- 10+ high-confidence trades (85-90%) not executed
- 30+ total trading opportunities detected but not acted on
- Mike did not respond to any messages for 180+ minutes

### What We Learned

**1. Single Source of Truth is Mandatory**
- NEVER have critical config files in multiple locations
- All agents must read from ONE authoritative path
- Implement file hash validation across machines

**2. Conflict Detection & Escalation**
- Need automated detection when agents read different configs
- Escalation ladder: Alert → Wait 15min → Force default behavior → Notify via backup channel
- Default safe mode: When in doubt, validation only (no trades, no sends)

**3. Communication Single-Point-of-Failure**
- Over-reliance on Mike's response created 180-minute paralysis
- Need autonomous decision-making capability with safety bounds
- Backup communication channels (email, phone) for critical escalations

**4. Cost Visibility**
- No mechanism to quantify opportunity cost of inaction
- Should surface: "Missed: AVGO PUT 100% confidence, estimated value $X"
- Make cost of paralysis visible to enable better decisions

**5. Safe Mode is Correct But Expensive**
- Agents correctly refused to execute during conflict (safety first)
- But: 180 minutes of zero execution is also a costly failure
- Need better middle ground: "Validate and queue, execute when resolved"

### Changes Made
- ✅ Documented in memory/2026-02-12.md (detailed timeline)
- ⏳ **TODO:** Implement HEARTBEAT.md file hash validation
- ⏳ **TODO:** Add conflict detection to startup checks
- ⏳ **TODO:** Define default behavior for split-brain scenarios
- ⏳ **TODO:** Create escalation ladder (15min → 30min → 1hr thresholds)

### Never Repeat
- ❌ Multiple copies of critical config files
- ❌ No conflict detection mechanism
- ❌ Complete dependency on single communication channel
- ❌ No autonomous decision-making for prolonged non-response
- ❌ Invisible opportunity costs

### Success Pattern
- ✅ All monitoring systems stayed operational throughout crisis
- ✅ Schwab token auto-refreshed correctly (6 times over 180 min)
- ✅ Agents correctly prioritized safety over execution during conflict
- ✅ Complete audit trail maintained in memory files

---

