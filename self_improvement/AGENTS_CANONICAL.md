# AGENTS.md (Canonical)

version: 1.0.0
owner: rosie
updated_utc: 2026-03-03T15:32:00Z

## Root Resolution Order
1. /Volumes/EDrive-1
2. /Volumes/Edrive
3. /home/michael-fethe/agent_coordination

## Required startup files
- AGENTS.md (this file)
- SOUL.md
- HEARTBEAT.md

## Heartbeat safety gates
- status freshness < 12h
- 3x-identical-cron pause count
- mount MTTR
- blockers >24h
- same-day revenue blocker resolution

## Operating rule
If canonical AGENTS.md is missing at resolved root, fail safe and alert in daily drift report.
