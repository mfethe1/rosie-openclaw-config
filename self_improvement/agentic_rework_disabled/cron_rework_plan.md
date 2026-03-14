# Cron Rework Plan: Legacy Broad Loops → Control Loops

Base folder: `/Users/harrisonfethe/.openclaw/workspace/self_improvement/agentic_rework`

## Mapping

| Legacy broad loop | New control loop | Schedule | Primary action | Output artifact |
|---|---|---|---|---|
| Generic status sweep | Agent Journal Loop | Every 30 minutes | Append lane notes + health snapshots | `logs/journal_YYYYMMDD_HHMM.log` |
| Ad-hoc skill drift checks | Agent Skill Hygiene | Daily 05:30 ET | Run `skill_count_lint.py` against catalog | `logs/skill_hygiene_YYYYMMDD.json` |
| Inconsistent KPI checks | Agent KPI Daily Score | Daily 06:30 ET (+ optional weekly rollup) | Run `kpi_rollup.py` for previous day and 7-day window | `logs/kpi_daily_YYYYMMDD.json`, `logs/kpi_weekly_YYYYMMDD.json` |
| Manual spend review | Agent Budget Guard | Hourly | Read latest KPI/budget signals and flag cap risk | `logs/budget_guard_YYYYMMDD_HH.json` |
| Stale lane cleanup | Agent Sunset Review | Daily 07:30 ET | Evaluate sunset rules per lane contract | `logs/sunset_review_YYYYMMDD.json` |

## Command Examples

### Journal 30m
```bash
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/agentic_rework
mkdir -p logs
python3 scripts/kpi_rollup.py --input logs/kpi_events.jsonl --date "$(date +%F)" --out "logs/journal_$(date +%Y%m%d_%H%M).log"
```

### Skill hygiene daily
```bash
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/agentic_rework
python3 scripts/skill_count_lint.py --catalog agent_catalog.json > "logs/skill_hygiene_$(date +%Y%m%d).json"
```

### KPI scoring daily/weekly
```bash
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/agentic_rework
python3 scripts/kpi_rollup.py --input logs/kpi_events.jsonl --date "$(date -v-1d +%F)" --out "logs/kpi_daily_$(date -v-1d +%Y%m%d).json"
python3 scripts/kpi_rollup.py --input logs/kpi_events.jsonl --window 7 --out "logs/kpi_weekly_$(date +%Y%m%d).json"
```

### Budget guard hourly
```bash
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/agentic_rework
python3 scripts/kpi_rollup.py --input logs/kpi_events.jsonl --date "$(date +%F)" --out "logs/budget_guard_$(date +%Y%m%d_%H).json"
```

### Sunset daily
```bash
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/agentic_rework
python3 scripts/intent_packet_gate.py --packet intent_packet_template.md > "logs/sunset_review_$(date +%Y%m%d).json"
```

## Notes
- All jobs run in `America/New_York`.
- No message delivery in cron config (`--no-deliver`).
- Model pin: `google/gemini-3.1-pro-preview`.
