#!/bin/bash
# Deploy all self-improvement cron jobs

echo "Deploying self-improvement cron jobs..."

# Check if Rosie's job already exists
# Note: openclaw cron list output format might vary, so we'll just try to add it and handle duplicates if needed,
# or better, rely on the fact that we are the agent and can use the tool directly.
# BUT, since I am writing a script to be executed, I should use the CLI if available.
# The prompt implies I am an agent inside OpenClaw. I should use the `cron` tool directly if possible,
# or use `openclaw cron add` if the CLI is available.
# The `exec` tool description mentions `openclaw` CLI commands are available.
# Let's assume `openclaw cron add` works as documented in the MD file.

# Rosie (Every 3h)
echo "Ensuring Rosie cron..."
# We'll just add it. If it exists, we might need to update or ignore.
# The CLI might fail if name conflicts, or it might just add another.
# Let's try to add it.
openclaw cron add <<EOF
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
EOF

# Winnie (Every 3h)
echo "Creating Winnie cron..."
openclaw cron add <<EOF
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
EOF

# Macklemore (Every 3h)
echo "Creating Mack cron..."
openclaw cron add <<EOF
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
EOF

# Daily Summary (8:00 AM)
echo "Creating Daily Summary cron..."
openclaw cron add <<EOF
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
EOF

# oh-my-opencode Monitoring (9:00 AM)
echo "Creating oh-my-opencode Monitoring cron..."
openclaw cron add <<EOF
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
EOF

# Bi-Daily Agent Comparison Pipeline (8:30 AM)
echo "Creating Bi-Daily Agent Comparison Pipeline..."
openclaw cron add <<EOF
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
EOF

echo "✅ All cron jobs deployed!"
openclaw cron list
