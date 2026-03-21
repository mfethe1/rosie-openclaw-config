# Usage & Templates

## Basic Examples

```bash
# Basic research (uses default "research" schema)
python3 scripts/firecrawl_agent.py "Find latest practices for multi-agent orchestration"

# Technology comparison
python3 scripts/firecrawl_agent.py --template tech-comparison "Compare Temporal vs NATS for workflow orchestration"

# Agentic framework research
python3 scripts/firecrawl_agent.py --template agentic-framework "Extract latest practices for building generalist agentic frameworks"

# Best practices discovery
python3 scripts/firecrawl_agent.py --template best-practices "Python async error handling patterns"

# With seed URLs to guide the agent
python3 scripts/firecrawl_agent.py --url https://docs.temporal.io --url https://nats.io "Compare workflow engines"

# Save to file
python3 scripts/firecrawl_agent.py --output results.json "your prompt"
```

## Available Templates

| Template | Fields | Best For |
|----------|--------|----------|
| `research` (default) | findings, synthesis, knowledge_gaps | General research questions |
| `tech-comparison` | technologies, recommendation, decision_matrix | Comparing tools/frameworks |
| `agentic-framework` | practices, workflows, conflict resolution, optimization | AI agent architecture research |
| `best-practices` | practices, anti_patterns, summary | Learning best practices for any topic |