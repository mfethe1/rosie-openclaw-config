#!/usr/bin/env python3
"""
firecrawl_agent.py — Autonomous web research via Firecrawl Agent API.

Firecrawl Agent browses the web autonomously, finds relevant sources,
and extracts structured data matching a provided JSON schema.

Usage:
    # With inline prompt (uses default research schema)
    python3 firecrawl_agent.py "Find best practices for multi-agent orchestration"

    # With custom schema file
    python3 firecrawl_agent.py --schema schemas/custom.json "your prompt"

    # With predefined schema template
    python3 firecrawl_agent.py --template tech-comparison "Compare Temporal vs NATS for workflows"

    # JSON output for pipeline integration
    python3 firecrawl_agent.py --json "your prompt"

    # Save results
    python3 firecrawl_agent.py --output results.json "your prompt"

    # Custom model
    python3 firecrawl_agent.py --model spark-1 "your prompt"

    # With URL hints (seeds the agent with specific starting points)
    python3 firecrawl_agent.py --url https://docs.temporal.io "Temporal workflow patterns"
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

FIRECRAWL_AGENT_URL = "https://api.firecrawl.dev/v2/agent"
DEFAULT_MODEL = "spark-1-mini"
SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = SKILL_DIR / "schemas"
RESULTS_DIR = Path.home() / ".openclaw" / "workspace" / "memory" / "tools"


def get_api_key():
    """Load Firecrawl API key from env or secrets file."""
    key = os.environ.get("FIRECRAWL_API_KEY", "")
    if key:
        return key
    env_file = Path.home() / ".openclaw" / "secrets" / "firecrawl.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("FIRECRAWL_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


# ── Schema Templates ────────────────────────────────────────────────────────

TEMPLATES = {
    "research": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "description": "Key findings from research",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Finding title"},
                        "summary": {
                            "type": "string",
                            "description": "Detailed summary of the finding",
                        },
                        "source_url": {
                            "type": "string",
                            "description": "Source URL for this finding",
                        },
                        "relevance": {
                            "type": "string",
                            "description": "Why this finding is relevant",
                        },
                        "actionable_insight": {
                            "type": "string",
                            "description": "Concrete action that can be taken based on this finding",
                        },
                    },
                    "required": ["title", "summary"],
                },
            },
            "synthesis": {
                "type": "string",
                "description": "Overall synthesis of all findings into a coherent conclusion",
            },
            "knowledge_gaps": {
                "type": "array",
                "description": "Topics that could not be fully resolved through online research",
                "items": {"type": "string"},
            },
        },
        "required": ["findings", "synthesis"],
    },
    "tech-comparison": {
        "type": "object",
        "properties": {
            "technologies": {
                "type": "array",
                "description": "Technologies being compared",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "weaknesses": {"type": "array", "items": {"type": "string"}},
                        "best_for": {
                            "type": "string",
                            "description": "Use cases where this technology excels",
                        },
                        "production_readiness": {
                            "type": "string",
                            "description": "Assessment of production readiness",
                        },
                        "documentation_url": {"type": "string"},
                    },
                    "required": ["name", "description", "strengths", "weaknesses"],
                },
            },
            "recommendation": {
                "type": "string",
                "description": "Overall recommendation with reasoning",
            },
            "decision_matrix": {
                "type": "object",
                "description": "Key decision criteria and how each technology scores",
                "properties": {
                    "criteria": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "criterion": {"type": "string"},
                                "weight": {
                                    "type": "string",
                                    "description": "high/medium/low",
                                },
                                "scores": {
                                    "type": "object",
                                    "description": "Technology name -> score description",
                                },
                            },
                            "required": ["criterion", "scores"],
                        },
                    },
                },
            },
        },
        "required": ["technologies", "recommendation"],
    },
    "agentic-framework": {
        "type": "object",
        "properties": {
            "agenticFrameworkPractices": {
                "type": "array",
                "description": "Latest practices for building a generalist agentic framework",
                "items": {
                    "type": "object",
                    "properties": {
                        "practiceDescription": {"type": "string"},
                        "practiceDescription_citation": {
                            "type": "string",
                            "description": "Source URL",
                        },
                        "dynamicSkillExecutionOptimizations": {
                            "type": "string",
                            "description": "Technical optimizations or risks associated with dynamic skill execution",
                        },
                        "offlineKnowledgeGaps": {
                            "type": "string",
                            "description": "Knowledge or skills that cannot be acquired via online means",
                        },
                    },
                    "required": ["practiceDescription"],
                },
            },
            "organizationalWorkflows": {
                "type": "array",
                "description": "Workflows involving PM/Technical personas and alternative roles",
                "items": {
                    "type": "object",
                    "properties": {
                        "workflowDescription": {"type": "string"},
                        "primaryPersonas": {
                            "type": "string",
                            "description": "Core roles involved",
                        },
                        "alternativeSynergisticRoles": {
                            "type": "string",
                            "description": "Roles like Critics, Mediators, or Adversarial agents",
                        },
                    },
                    "required": ["workflowDescription"],
                },
            },
            "conflictResolution": {
                "type": "object",
                "description": "Strategies for handling conflicting knowledge",
                "properties": {
                    "votingConsensusStrategies": {"type": "string"},
                    "performanceEvidence": {"type": "string"},
                },
                "required": ["votingConsensusStrategies"],
            },
            "openClawOptimization": {
                "type": "string",
                "description": "Specific optimization strategies for OpenClaw environments",
            },
        },
        "required": [
            "agenticFrameworkPractices",
            "organizationalWorkflows",
            "conflictResolution",
        ],
    },
    "best-practices": {
        "type": "object",
        "properties": {
            "practices": {
                "type": "array",
                "description": "Best practices discovered",
                "items": {
                    "type": "object",
                    "properties": {
                        "practice": {
                            "type": "string",
                            "description": "The practice itself",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Why this is recommended",
                        },
                        "source": {
                            "type": "string",
                            "description": "Where this practice comes from",
                        },
                        "implementation_notes": {
                            "type": "string",
                            "description": "How to implement",
                        },
                        "pitfalls": {
                            "type": "string",
                            "description": "Common mistakes to avoid",
                        },
                    },
                    "required": ["practice", "rationale"],
                },
            },
            "anti_patterns": {
                "type": "array",
                "description": "Things to avoid",
                "items": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "why_bad": {"type": "string"},
                        "alternative": {"type": "string"},
                    },
                    "required": ["pattern", "why_bad"],
                },
            },
            "summary": {"type": "string"},
        },
        "required": ["practices", "summary"],
    },
}


def load_schema(schema_path=None, template_name=None):
    """Load schema from file, template name, or return default."""
    if schema_path:
        path = Path(schema_path)
        if not path.is_absolute():
            path = SCHEMAS_DIR / path
        if not path.exists():
            print(f"Schema file not found: {path}", file=sys.stderr)
            sys.exit(1)
        return json.loads(path.read_text())

    if template_name:
        if template_name not in TEMPLATES:
            print(
                f"Unknown template: {template_name}. Available: {', '.join(TEMPLATES.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)
        return TEMPLATES[template_name]

    return TEMPLATES["research"]


def agent_extract(prompt, schema, model=DEFAULT_MODEL, urls=None, poll_interval=5, max_wait=600):
    """Call Firecrawl Agent API for autonomous web research + structured extraction.

    The agent API is async: POST creates a job, then we poll GET until complete.
    """
    import time

    api_key = get_api_key()
    if not api_key:
        return {
            "ok": False,
            "error": "No FIRECRAWL_API_KEY found. Set env var or add to ~/.openclaw/secrets/firecrawl.env",
        }

    payload = {
        "prompt": prompt,
        "schema": schema,
        "model": model,
    }

    if urls:
        payload["urls"] = urls

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        # Step 1: Create the agent job
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            FIRECRAWL_AGENT_URL, data=data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            create_result = json.loads(resp.read().decode("utf-8", errors="replace"))

        job_id = create_result.get("id")
        if not job_id:
            # Synchronous response — some endpoints return data directly
            return {
                "ok": True,
                "model": model,
                "prompt": prompt,
                "data": create_result.get("data", create_result),
                "sources": create_result.get("sources", []),
                "metadata": {
                    "status": create_result.get("status", "completed"),
                    "steps": create_result.get("steps", []),
                    "total_sources": len(create_result.get("sources", [])),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Step 2: Poll for completion
        poll_url = f"{FIRECRAWL_AGENT_URL}/{job_id}"
        poll_headers = {"Authorization": f"Bearer {api_key}"}
        elapsed = 0
        status = "processing"

        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            poll_req = urllib.request.Request(poll_url, headers=poll_headers, method="GET")
            with urllib.request.urlopen(poll_req, timeout=30) as resp:
                poll_result = json.loads(resp.read().decode("utf-8", errors="replace"))

            status = poll_result.get("status", "")
            print(f"  [{elapsed}s] Status: {status}", file=sys.stderr)

            if status == "completed":
                return {
                    "ok": True,
                    "model": model,
                    "prompt": prompt,
                    "data": poll_result.get("data", poll_result.get("result", {})),
                    "sources": poll_result.get("sources", []),
                    "metadata": {
                        "status": "completed",
                        "job_id": job_id,
                        "steps": poll_result.get("steps", []),
                        "total_sources": len(poll_result.get("sources", [])),
                        "elapsed_seconds": elapsed,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            if status in ("failed", "error", "cancelled"):
                return {
                    "ok": False,
                    "error": f"Agent job {status}: {poll_result.get('error', 'unknown')}",
                    "model": model,
                    "prompt": prompt,
                    "job_id": job_id,
                }

        return {
            "ok": False,
            "error": f"Agent job timed out after {max_wait}s (status: {status})",
            "model": model,
            "prompt": prompt,
            "job_id": job_id,
        }

    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "ok": False,
            "error": f"HTTP {e.code}: {e.reason}",
            "detail": body,
            "model": model,
            "prompt": prompt,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "model": model, "prompt": prompt}

def format_markdown(result):
    """Format agent result as readable markdown."""
    if not result.get("ok"):
        return f"# Agent Error\n\n{result.get('error', 'Unknown error')}\n\n{result.get('detail', '')}"

    lines = [
        f"# Firecrawl Agent Research",
        f"\n**Prompt:** {result['prompt'][:200]}",
        f"**Model:** {result['model']}",
        f"**Time:** {result['timestamp']}",
        f"**Sources Found:** {result['metadata'].get('total_sources', 0)}",
        f"\n---\n",
    ]

    data = result.get("data", {})
    if isinstance(data, dict):
        lines.append("## Extracted Data\n")
        lines.append(f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```")
    else:
        lines.append(f"## Raw Result\n\n{data}")

    sources = result.get("sources", [])
    if sources:
        lines.append("\n---\n## Sources")
        for i, src in enumerate(sources, 1):
            if isinstance(src, str):
                lines.append(f"{i}. {src}")
            elif isinstance(src, dict):
                url = src.get("url", src.get("source", ""))
                title = src.get("title", "Source")
                lines.append(f"{i}. [{title}]({url})")

    steps = result.get("metadata", {}).get("steps", [])
    if steps:
        lines.append("\n---\n## Agent Steps")
        for i, step in enumerate(steps, 1):
            if isinstance(step, str):
                lines.append(f"{i}. {step}")
            elif isinstance(step, dict):
                lines.append(
                    f"{i}. {step.get('action', step.get('description', str(step)))}"
                )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Firecrawl Agent — Autonomous web research with structured extraction"
    )
    parser.add_argument("prompt", nargs="*", help="Research prompt / question")
    parser.add_argument("--schema", help="Path to custom JSON schema file")
    parser.add_argument(
        "--template",
        "-t",
        choices=list(TEMPLATES.keys()),
        help="Use predefined schema template",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        help=f"Firecrawl model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--url",
        action="append",
        dest="urls",
        help="Seed URL(s) for the agent to start from (can be repeated)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_out", help="JSON output"
    )
    parser.add_argument("--output", "-o", help="Save results to file")
    parser.add_argument(
        "--list-templates", action="store_true", help="List available schema templates"
    )
    args = parser.parse_args()

    if args.list_templates:
        print("Available schema templates:\n")
        for name, schema in TEMPLATES.items():
            desc = schema.get("description", "")
            top_keys = ", ".join(schema.get("properties", {}).keys())
            print(f"  {name:20s}  fields: {top_keys}")
        return 0

    if not args.prompt:
        parser.error("prompt is required (unless using --list-templates)")

    prompt = " ".join(args.prompt)
    schema = load_schema(schema_path=args.schema, template_name=args.template)

    print(f"Launching Firecrawl Agent ({args.model})...", file=sys.stderr)
    print(f"Prompt: {prompt[:120]}...", file=sys.stderr)
    if args.urls:
        print(f"Seed URLs: {', '.join(args.urls)}", file=sys.stderr)

    result = agent_extract(
        prompt=prompt,
        schema=schema,
        model=args.model,
        urls=args.urls,
    )

    if args.json_out:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        md = format_markdown(result)
        print(md)

    if args.output and result.get("ok"):
        out_path = Path(args.output)
        if args.output.endswith(".json"):
            out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            out_path.write_text(format_markdown(result))
        print(f"\nSaved to {args.output}", file=sys.stderr)

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
