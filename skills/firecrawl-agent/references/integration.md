# Integration & Custom Schemas

## Custom Schemas

Create a JSON file with your schema and pass it via `--schema`:

```json
{
  "type": "object",
  "properties": {
    "key_findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "finding": {"type": "string"},
          "source_url": {"type": "string"}
        },
        "required": ["finding"]
      }
    },
    "conclusion": {"type": "string"}
  },
  "required": ["key_findings", "conclusion"]
}
```

```bash
python3 scripts/firecrawl_agent.py --schema my_schema.json "research prompt here"
```

## Integration with Agent Workflows

### From Python (agent scripts)

```python
import subprocess, json
from pathlib import Path

def firecrawl_research(prompt, template="research", urls=None):
    script = Path("~/.openclaw/skills/firecrawl-agent/scripts/firecrawl_agent.py").expanduser()
    cmd = ["python3", str(script), "--json", "--template", template]
    if urls:
        for url in urls:
            cmd.extend(["--url", url])
    cmd.append(prompt)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return json.loads(result.stdout) if result.returncode == 0 else None
```

### From Bash (OpenClaw cron agents)

```bash
python3 ~/.openclaw/skills/firecrawl-agent/scripts/firecrawl_agent.py \
    --json --template tech-comparison \
    "Compare vector databases for RAG pipelines" \
    > /tmp/research_results.json
```