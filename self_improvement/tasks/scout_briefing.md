# Ecosystem Scout Briefing (Weekly)
**Frequency:** Every Monday 06:00 UTC (Winnie cron)
**Output:** `self_improvement/outputs/YYYY-MM-DD-scout-ecosystem.md`

## Scope & Sources
1. **Agent/autonomy frameworks** — Github trending (last 7d), Product Hunt (AI category), Hacker News (`Ask HN: favorite agent framework`)
2. **LLM capability releases** — Model cards from Anthropic, OpenAI, Google, Mistral; release notes from all.
3. **Dependency updates** — Security advisories (NVD), critical CVEs in our stack.
4. **Cost signals** — Pricing changes, rate limits, deprecations from API docs of tools in use.
5. **Monitoring/observability** — New tools for cost tracking, cron health, output quality measurement.

## Report Structure
```
## Signals Detected (This Week)
### High Priority
- **[Tool/Pattern]** — [Why significant in 1 line]
  - Source: [URL]
  - Preliminary assessment: [WATCH | IMMEDIATE_EVAL | SKIP]
  - Next: [Task added to TODO: D-XXX]

### Medium Priority
- [Tool/Pattern] — [Why notable]
  - Source: [URL]
  - Preliminary assessment: [WATCH | SKIP]

## Dependency Hygiene Scan
- **Security alerts:** [0/N]
- **Deprecations in next 12mo:** [0/N]
- **Cost estimate changes:** [±%]

## Todo Additions (If Any)
None yet this week. | D-NNN: [New evaluation task]
```

## Success Criteria
- ≥1 new tool evaluated per month that reaches SANDBOX_TEST or better
- Zero surprise deprecations (caught ≥30d in advance)
- Cost signals tracked and flagged before bill shock
