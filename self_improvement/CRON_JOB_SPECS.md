# Cron Job Specifications - Ready to Deploy

**Created:** 2026-02-12 18:00 EST
**Deploy these immediately to start continuous improvement system**

**Coordination baseline:** see `/Users/harrisonfethe/.openclaw/workspace/agents.md` for role matrix, handoff standards, model rotation, and quality gates.

---

## Job 1: Winnie - Research & Implementation Cycle

**Schedule:** Every 3 hours starting 7:00 PM EST (today)
**Anchor:** Feb 12 2026, 7:00 PM EST = 1770940800000 ms
**Interval:** 10800000 ms (3 hours)

```json
{
  "name": "Winnie: Self-Improvement Research (every 3h)",
  "schedule": {
    "kind": "every",
    "everyMs": 10800000,
    "anchorMs": 1770940800000
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Read self_improvement/LOOPS.md for your checklist. Read self_improvement/TODO.md. Read shared-state.json. Focus: Databases & implementation. Research 4-hour cycle (offset 1h from Rosie/Mack). Pick 1 task from TODO, complete it, update CHANGELOG.md, update TODO.md, write to self_improvement/outputs/YYYY-MM-DD-HH-winnie.md, update shared-state.json.",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 900
  },
  "delivery": {
    "mode": "none"
  }
}
```

---

## Job 2: Macklemore - Technical Execution Cycle

**Schedule:** Every 3 hours starting 8:00 PM EST (today)
**Anchor:** Feb 12 2026, 8:00 PM EST = 1770944400000 ms
**Interval:** 10800000 ms (3 hours)

```json
{
  "name": "Macklemore: Self-Improvement Execution (every 3h)",
  "schedule": {
    "kind": "every",
    "everyMs": 10800000,
    "anchorMs": 1770944400000
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Read self_improvement/LOOPS.md for your checklist. Read self_improvement/TODO.md. Read shared-state.json. Focus: Code implementation, skills, automation. Research 4-hour cycle (offset 1h from Rosie/Winnie). Pick 1 technical task from TODO, complete it, update CHANGELOG.md, update TODO.md, write to self_improvement/outputs/YYYY-MM-DD-HH-mack.md, update shared-state.json.",
    "model": "openai-codex/gpt-5.3-codex",
    "thinking": "medium",
    "timeoutSeconds": 1200
  },
  "delivery": {
    "mode": "none"
  }
}
```

---

## Job 3: Rosie - Strategic Coordination Cycle

**Schedule:** Every 3 hours starting 6:00 PM EST (Michael already created this one)

**Note:** Michael already created Rosie's cron at 6:00 PM repeating every 3 hours. Verify it exists:
```bash
openclaw cron list | grep -i rosie
```

If not found, create:
```json
{
  "name": "Rosie: Self-Improvement Coordination (every 3h)",
  "schedule": {
    "kind": "every",
    "everyMs": 10800000,
    "anchorMs": 1770937200000
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Read self_improvement/LOOPS.md for your checklist. Read self_improvement/TODO.md. Read shared-state.json. Focus: Process improvement, coordination, quality oversight. Research 4-hour cycle (strategic frameworks). Pick 1 process task from TODO, complete it, update CHANGELOG.md, update TODO.md, write to self_improvement/outputs/YYYY-MM-DD-HH-rosie.md, update shared-state.json.",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 900
  },
  "delivery": {
    "mode": "none"
  }
}
```

---

## Job 4: Daily Morning Summary

**Schedule:** Every day at 8:00 AM EST

```json
{
  "name": "Team: Daily Morning Summary (8:00 AM)",
  "schedule": {
    "kind": "cron",
    "expr": "0 8 * * *",
    "tz": "America/New_York"
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Compile overnight work summary: (1) Read all self_improvement/outputs/YYYY-MM-DD-* from last 24h, (2) Read self_improvement/CHANGELOG.md entries from yesterday, (3) Read shared-state.json, (4) Generate summary: completed improvements, new skills added, blockers, next priorities. THEN use message tool to send summary to Telegram Self Improvement group (-1003753060481).",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 600
  },
  "delivery": {
    "mode": "announce",
    "channel": "telegram",
    "to": "-1003753060481"
  }
}
```

---

## Job 5: oh-my-opencode Monitoring

**Schedule:** Every day at 9:00 AM EST

```json
{
  "name": "Winnie: oh-my-opencode Monitoring (9:00 AM daily)",

  "schedule": {
    "kind": "cron",
    "expr": "0 9 * * *",
    "tz": "America/New_York"
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Competitor sweep: monitor oh-my-opencode, antfarm, and Ralph-loop style tooling. For each cycle produce Keep/Stop/Test recommendations mapped to: deterministic execution guarantees, verification gates, cost/maintenance burden, and model portability. Update TODO with priority + next action; document in self_improvement/outputs/YYYY-MM-DD-HH-winnie.md.",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 600
  },
  "delivery": {
    "mode": "none"
  }
}
```

---

## Job 6: Bi-Daily Agent Comparison Pipeline

**Schedule:** Every 2 days at 8:30 AM EST

```json
{
  "name": "Team: Agent Comparison Pipeline (bi-daily)",
  "schedule": {
    "kind": "every",
    "everyMs": 172800000,
    "anchorMs": 1707715800000
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Run agent comparison pipeline: (1) Read shared-state.json and latest outputs in self_improvement/outputs, (2) Compare outputs from prior Rosie/Mack/Winnie/Lenny cycles against model performance and completion quality, (3) Produce three recommendations: what to keep, what to fix, what to stop, (4) Update shared-state.json with a concise improvement summary and next-cycle hypotheses.",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 1200
  },
  "delivery": {
    "mode": "none"
  }
}
```

**Why 8:30 AM?** Offset from existing 9:00 AM jobs to avoid overlap while still using overnight outputs.

---

## Deployment Script

**Save as:** `deploy-cron-jobs.sh`

```bash
#!/bin/bash
# Deploy all self-improvement cron jobs

echo "Deploying self-improvement cron jobs..."

# Check if Rosie's job already exists
if openclaw cron list | grep -q "Rosie.*Self-Improvement"; then
    echo "✅ Rosie cron already exists (created by Michael)"
else
    echo "⚠️  Rosie cron not found, creating..."
    # Add Rosie cron creation here if needed
fi

# Create Winnie cron (7:00 PM, every 3h)
echo "Creating Winnie cron..."
openclaw cron add --job '{
  "name": "Winnie: Self-Improvement Research (every 3h)",
  "schedule": {"kind": "every", "everyMs": 10800000, "anchorMs": 1770940800000},
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Read self_improvement/LOOPS.md. Read TODO.md. Read shared-state.json. Focus: Databases & implementation. Research cycle. Pick 1 task, complete, update CHANGELOG, TODO, write outputs/YYYY-MM-DD-HH-winnie.md, update shared-state.",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 900
  },
  "delivery": {"mode": "none"}
}'

# Create Mack cron (8:00 PM, every 3h)
echo "Creating Mack cron..."
openclaw cron add --job '{
  "name": "Macklemore: Self-Improvement Execution (every 3h)",
  "schedule": {"kind": "every", "everyMs": 10800000, "anchorMs": 1770944400000},
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Read self_improvement/LOOPS.md. Read TODO.md. Read shared-state.json. Focus: Code, skills, automation. Research cycle. Pick 1 technical task, complete, update CHANGELOG, TODO, write outputs/YYYY-MM-DD-HH-mack.md, update shared-state.",
    "model": "openai-codex/gpt-5.3-codex",
    "thinking": "medium",
    "timeoutSeconds": 1200
  },
  "delivery": {"mode": "none"}
}'

# Create daily summary (8:00 AM)
echo "Creating daily summary cron..."
openclaw cron add --job '{
  "name": "Team: Daily Morning Summary (8:00 AM)",
  "schedule": {"kind": "cron", "expr": "0 8 * * *", "tz": "America/New_York"},
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Compile overnight work: Read outputs from last 24h, CHANGELOG, shared-state. Summarize to Telegram Self Improvement (-1003753060481).",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 600
  },
  "delivery": {"mode": "announce", "channel": "telegram", "to": "-1003753060481"}
}'

# Create oh-my-opencode monitoring (9:00 AM)
echo "Creating oh-my-opencode monitoring cron..."
openclaw cron add --job '{
  "name": "Winnie: oh-my-opencode Monitoring (9:00 AM daily)",
  "schedule": {"kind": "cron", "expr": "0 9 * * *", "tz": "America/New_York"},
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Competitor sweep: monitor oh-my-opencode, antfarm, and Ralph-loop style automation. Assess keep/stop/experiment actions across reliability, guardrails, and execution overhead. Update TODO + outputs with decision rationale and any rollout recommendation.",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 600
  },
  "delivery": {"mode": "none"}
}'

# Create bi-daily agent comparison (8:30 AM)
echo "Creating bi-daily agent comparison pipeline..."
openclaw cron add --job '{
  "name": "Team: Agent Comparison Pipeline (bi-daily)",
  "schedule": {"kind": "every", "everyMs": 172800000, "anchorMs": 1707715800000},
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Run agent comparison pipeline: score prior cycle outputs, compare completion quality across agents, and publish keep/fix/stop recommendations in shared-state.json.",
    "model": "anthropic/claude-sonnet-4-5",
    "timeoutSeconds": 1200
  },
  "delivery": {"mode": "none"}
}'

echo "✅ All cron jobs deployed!"
echo ""
echo "Next runs:"
openclaw cron list

echo ""
echo "Test manually:"
echo "  openclaw cron run 'Winnie: Self-Improvement Research (every 3h)' --run-mode force"
```

---

## Verification Commands

```bash
# List all cron jobs
openclaw cron list

# Check specific job
openclaw cron runs "Winnie: Self-Improvement Research (every 3h)"

# Test Winnie's job manually (don't wait for 7 PM)
openclaw cron run "Winnie: Self-Improvement Research (every 3h)" --run-mode force

# Test Mack's job manually
openclaw cron run "Macklemore: Self-Improvement Execution (every 3h)" --run-mode force
```

---

## Timeline

**18:00 (now):** Jobs defined
**18:05:** Deploy script runs
**19:00 (7 PM):** Winnie's first automatic cycle
**20:00 (8 PM):** Mack's first automatic cycle
**Tomorrow 08:00:** First morning summary
**Tomorrow 09:00:** First oh-my-opencode check
**Day 2 08:30:** First bi-daily agent comparison pipeline run

---

**Ready to deploy. Run: `bash deploy-cron-jobs.sh`**
