# rosie-openclaw-config

Rosie agent's OpenClaw configuration, settings, and upstream tracking.

## What this repo does
- Tracks `openclaw/openclaw` upstream commits (checked every 3h)
- Evaluates new commits as: Adopt / Watch / Skip
- Preserves all agent-critical settings (SOUL.md, crons, skills, endpoints)
- Reports are auto-committed to `reports/`

## Critical protected settings
- `SOUL.md` — Rosie identity/persona
- `AGENTS.md` — operating rules
- `WORKFLOW_AUTO.md` — startup protocol
- memU endpoint: `localhost:12345`
- NATS: Railway primary (`gondola.proxy.rlwy.net:22393`)
- Model: `anthropic/claude-sonnet-4-6`

## How to apply upstream recommendations
```bash
openclaw update    # pull latest openclaw version
openclaw doctor   # verify health after update
```

## Scripts
- `scripts/upstream_check.sh` — runs every 3h via cron

## Cron schedule
`0 */3 * * *` — every 3 hours
