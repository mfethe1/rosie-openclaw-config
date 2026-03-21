---
name: firecrawl-agent
description: Trigger this skill when needing deep, multi-source web research with structured JSON/markdown output, such as technology comparisons, best practice discovery, or competitive analysis. Do not use for quick fact lookups or single-page scrapes (use Sonar or Firecrawl MCP instead).
---

# Firecrawl Agent

Autonomous web research and extraction via Firecrawl Agent API. It browses the web, finds sources, and extracts structured data matching a schema.

## Core Interaction
```bash
python3 scripts/firecrawl_agent.py [options] "your prompt"
```

For basic usage, available templates, and parameters, read [references/usage.md](./references/usage.md).

## Integration & Custom Schemas
For advanced usage, including writing custom schemas, and integrating with Bash or Python agent scripts, read [references/integration.md](./references/integration.md).

## Gotchas & Common Failures
- **Model Costs**: The default model is `spark-1-mini`. `spark-1` is more capable but significantly more expensive. Be aware that a single run may scrape 5-20+ pages. Avoid tight loops of research.
- **Missing API Key**: If the tool fails to run, ensure `FIRECRAWL_API_KEY` is exported or exists in `~/.openclaw/secrets/firecrawl.env`.
- **Misuse for Simple Queries**: Do not use this for quick lookups or single-page scrapes. It is an expensive, deep-browsing agent. For simple queries, use Sonar/Perplexity or web_search.
- **Timeout**: The agent can take several minutes. If calling from another script (like Python), ensure timeouts are set high (e.g., 600s).