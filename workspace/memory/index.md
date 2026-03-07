# Memory Index

Quick map for where to store and find context.

## Categories

- `projects/` - Project plans, per-repo context, milestone notes
- `decisions/` - Design and architecture decisions (`D-xxx`)
- `learnings/` - Lessons, incident reflections, anti-patterns, best practices
- `infrastructure/` - Deploy notes, health checks, host/service configuration
- `agents/` - Agent behavior, role notes, execution constraints
- `tools/` - CLI/tool usage, API reference notes, config locations
- `workflows/` - SOPs, repeatable checklists, operational playbooks

## Search Shortcuts

- All memory: `python3 ~/.openclaw/workspace/memory/search.py "keyword"`
- Category only: `python3 ~/.openclaw/workspace/memory/search.py "keyword" --category projects`
- Regex mode: `python3 ~/.openclaw/workspace/memory/search.py "pattern" --regex`
- JSON output: `python3 ~/.openclaw/workspace/memory/search.py "keyword" --json`
