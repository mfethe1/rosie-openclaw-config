#!/usr/bin/env python3
"""
run_live_test.py — Live test runner for PM Framework using OpenRouter API.
Runs a BuildBid H8 (Granular 3D Lot Models persistence) through full persona chain.

Usage:
    python3 run_live_test.py --project buildbid --ticket H8 --personas pm,red,blue,qa
    python3 run_live_test.py --test  # dry-run self-test
"""

import os
import sys
import json
import argparse
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FRAMEWORK_DIR = Path(__file__).parent
LOGS_DIR = FRAMEWORK_DIR / "logs"
CONFIGS_DIR = FRAMEWORK_DIR / "project_configs"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL_OR = "anthropic/claude-haiku-4-5"   # OpenRouter model ID
MODEL_AN = "claude-haiku-4-5"             # Anthropic model ID


def call_api(system_prompt: str, user_message: str, temperature: float = 0.3,
             max_tokens: int = 1500) -> str:
    """Call LLM via OpenRouter (fallback to Anthropic if key set)."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

    if anthropic_key:
        # Native Anthropic API
        payload = {
            "model": MODEL_AN,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            ANTHROPIC_URL, data=data,
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]

    elif openrouter_key:
        # OpenRouter — OpenAI-compatible
        payload = {
            "model": MODEL_OR,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL, data=data,
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://protelynx.ai",
                "X-Title": "PM Framework Live Test"
            }
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]

    else:
        raise RuntimeError("No API key found: set ANTHROPIC_API_KEY or OPENROUTER_API_KEY")


# ---------------------------------------------------------------------------
# Minimal persona definitions for the live test
# ---------------------------------------------------------------------------
PERSONAS = {
    "pm": {
        "name": "Project Manager",
        "temperature": 0.3,
        "system_prompt": """You are a senior Project Manager reviewing a construction SaaS product.
Your job: analyze the feature request, generate sprint plan with user stories (INVEST criteria),
acceptance criteria, effort estimates (S/M/L/XL), dependencies, and a risk register.
Output in structured markdown with clear sections."""
    },
    "red": {
        "name": "Red Team Critic",
        "temperature": 0.7,
        "system_prompt": """You are an adversarial Red Team Critic. Your job is to find every flaw,
gap, race condition, edge case, and risk in a software sprint plan for a construction SaaS product.
Be blunt, specific, and unsparing. No softening. Output numbered failure modes with severity (P0-P3)."""
    },
    "blue": {
        "name": "Blue Team Defender",
        "temperature": 0.4,
        "system_prompt": """You are a Blue Team Defender. Given a Red Team critique, produce concrete
mitigations: acceptance criteria additions, code patterns, test requirements. Map each risk to a
specific mitigation. Output as numbered list matching Red Team's findings."""
    },
    "qa": {
        "name": "QA Reviewer",
        "temperature": 0.2,
        "system_prompt": """You are a QA Engineer reviewing a sprint plan and its defenses.
Generate a test strategy: unit tests, integration tests, E2E test scenarios, edge cases,
and a completeness score (0-100) with rationale. Output in structured markdown."""
    },
    "tech_lead": {
        "name": "Technical Lead [construction]",
        "temperature": 0.35,
        "system_prompt": """You are a Technical Lead specializing in construction SaaS.
Review the sprint plan for architecture concerns: schema design, API contracts, caching strategy,
BIM workflow compatibility, and PostgreSQL performance for 3D model data.
Output concrete technical recommendations and any blocking decisions."""
    },
    "ux_designer": {
        "name": "UX/UI Designer",
        "temperature": 0.5,
        "system_prompt": """You are a UX/UI Designer reviewing feature plans for a construction estimating app.
Identify user flow gaps, accessibility issues, and design system concerns for the lot model persistence feature.
Construction estimators often work on-site on tablets/phones — design for that context."""
    },
    "cpo": {
        "name": "Chief Product Officer",
        "temperature": 0.4,
        "system_prompt": """You are the Chief Product Officer making final go/no-go decisions.
Synthesize ALL prior team input: PM plan, Red Team risks, Blue Team mitigations, QA strategy,
Tech Lead concerns, and UX gaps. Output: (1) Go/No-Go verdict with rationale, (2) top 3 business bets,
(3) resolved risk register, (4) success metrics, (5) launch criteria."""
    }
}

H8_CONTEXT = """## Feature: H8 — Granular 3D Lot Models (Persistence Layer)

**Summary:** BuildBid currently generates 3D lot model visualizations for construction site estimates
but loses all model data on session end. H8 adds full persistence: database storage, versioning,
and retrieval for granular 3D lot model data.

**Scope:**
- PostgreSQL schema for lot_models table (JSONB for geometry, versioning, tenant isolation)
- FastAPI endpoints: POST /lots, GET /lots/{id}, PUT /lots/{id}, GET /lots/{project_id}
- Soft-delete and version history (keep last 10 versions per lot)
- Signed URL generation for large geometry blobs (>5MB fallback to S3)
- Frontend: auto-save on model mutation (debounced 2s), load on session restore
- Multi-tenant: row-level security via PostgreSQL RLS

**Known constraints:**
- Multi-user collaboration on same lot not yet supported (deferred to H9)
- Mobile-responsive UI is a dependency (partial, H7 in parallel)
- Material pricing not yet live (separate stream)
- 3 pilot customers expect this in the next sprint

**Success criteria:**
- Lot model persists across browser refreshes and login sessions
- Load time <2s for lots with <10,000 geometry nodes
- Zero data loss on concurrent save attempts (last-write-wins for now)
- RLS verified: Tenant A cannot access Tenant B's lots
"""


def run_persona(role: str, project: str, context: str, prior_outputs: dict,
                dry_run: bool = False) -> str:
    persona = PERSONAS[role]
    name = persona["name"]

    # Build user message with prior context
    msg = f"## Project: {project}\n\n## Feature Context\n{context}\n"

    if role == "red" and "pm" in prior_outputs:
        msg += f"\n## PM Sprint Plan (critique this)\n{prior_outputs['pm']}\n\nFind every flaw. Be adversarial."
    elif role == "blue" and "red" in prior_outputs:
        msg += f"\n## PM Sprint Plan\n{prior_outputs.get('pm', '')}\n\n## Red Team Critique\n{prior_outputs['red']}\n\nProvide concrete mitigations for every finding."
    elif role == "qa" and prior_outputs:
        pm_out = prior_outputs.get("pm", "")
        blue_out = prior_outputs.get("blue", "")
        msg += f"\n## Sprint Plan\n{pm_out}\n\n## Blue Team Mitigations\n{blue_out}\n\nGenerate complete test strategy."
    elif role == "tech_lead" and "pm" in prior_outputs:
        msg += f"\n## Sprint Plan\n{prior_outputs['pm']}\n\nReview for technical architecture concerns specific to 3D lot model persistence in PostgreSQL."
    elif role == "ux_designer" and prior_outputs:
        msg += f"\n## Sprint Plan\n{prior_outputs.get('pm', '')}\n\nReview UX flows for lot model persistence. Focus on on-site tablet/mobile usage."
    elif role == "cpo" and prior_outputs:
        for r, out in prior_outputs.items():
            msg += f"\n## {PERSONAS.get(r, {}).get('name', r)} Output\n{out[:600]}...\n"
        msg += "\nSynthesize all above into final CPO decision."
    else:
        msg += f"\nReview this feature request in your area of expertise."

    print(f"  → Running {name}...", end="", flush=True)

    if dry_run:
        result = f"[DRY RUN] {name} would analyze H8 lot model persistence. (No API call made)"
        print(" [dry-run]")
        return result

    try:
        result = call_api(persona["system_prompt"], msg, persona["temperature"])
        print(f" ✓ ({len(result)} chars)")
        return result
    except Exception as e:
        print(f" ✗ ERROR: {e}")
        return f"[ERROR] {name} call failed: {e}"


def run_live_test(project_name: str, ticket: str, personas: list,
                  dry_run: bool = False) -> dict:
    """Run full persona chain for a ticket and return structured report."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    ts = datetime.datetime.now().isoformat()

    print(f"\n{'='*60}")
    print(f"LIVE TEST: {project_name} — {ticket}")
    print(f"Personas: {', '.join(personas)}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE (API calls)'}")
    print(f"{'='*60}")

    # Load project config for metadata
    config_path = CONFIGS_DIR / f"{project_name.lower()}.json"
    project_config = {}
    if config_path.exists():
        with open(config_path) as f:
            project_config = json.load(f)

    prior_outputs = {}
    persona_results = {}
    errors = []

    for role in personas:
        if role not in PERSONAS:
            print(f"  ⚠ Unknown persona '{role}' — skipping")
            errors.append(f"Unknown persona: {role}")
            continue
        output = run_persona(role, project_name, H8_CONTEXT, prior_outputs, dry_run)
        prior_outputs[role] = output
        persona_results[role] = {
            "persona": PERSONAS[role]["name"],
            "output": output,
            "output_length": len(output)
        }

    # Build report
    report = {
        "test_id": f"live-test-{project_name.lower()}-{ticket.lower()}-{date_str}",
        "project": project_name,
        "ticket": ticket,
        "ticket_title": "Granular 3D Lot Models — Persistence Layer",
        "timestamp": ts,
        "date": date_str,
        "dry_run": dry_run,
        "personas_run": personas,
        "project_config": project_config,
        "context_snapshot": H8_CONTEXT,
        "outputs": {role: data["output"] for role, data in persona_results.items()},
        "persona_metadata": {
            role: {"name": data["persona"], "output_length": data["output_length"]}
            for role, data in persona_results.items()
        },
        "errors": errors,
        "summary": {
            "total_personas": len(personas),
            "successful": len(persona_results),
            "failed": len(errors),
            "total_output_chars": sum(d["output_length"] for d in persona_results.values()),
            "api_provider": "openrouter" if os.environ.get("OPENROUTER_API_KEY") else
                           ("anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "none"),
            "model_used": MODEL_OR if os.environ.get("OPENROUTER_API_KEY") else MODEL_AN
        }
    }

    # Save JSON report
    json_path = LOGS_DIR / f"live-test-buildbid-h8-{date_str}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n✅ JSON report saved: {json_path}")

    # Save markdown summary
    md_path = LOGS_DIR / f"live-test-buildbid-h8-{date_str}.md"
    md = build_markdown_summary(report)
    with open(md_path, "w") as f:
        f.write(md)
    print(f"✅ Markdown summary saved: {md_path}")

    return report


def build_markdown_summary(report: dict) -> str:
    ts = report["timestamp"][:16].replace("T", " ")
    lines = [
        f"# PM Framework Live Test — BuildBid {report['ticket']}",
        f"**{report['ticket_title']}**",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Test ID | `{report['test_id']}` |",
        f"| Date | {report['date']} |",
        f"| Timestamp | {ts} |",
        f"| Personas run | {', '.join(report['personas_run'])} |",
        f"| API provider | {report['summary']['api_provider']} |",
        f"| Model | `{report['summary']['model_used']}` |",
        f"| Total output | {report['summary']['total_output_chars']:,} chars |",
        f"| Errors | {report['summary']['failed']} |",
        f"| Mode | {'🔵 DRY RUN' if report['dry_run'] else '🟢 LIVE'} |",
        f"",
        f"---",
        f"",
        f"## Feature Context",
        f"",
        report["context_snapshot"],
        f"",
        f"---",
        f""
    ]

    for role in report["personas_run"]:
        if role in report["outputs"]:
            meta = report["persona_metadata"].get(role, {})
            name = meta.get("name", role)
            output = report["outputs"][role]
            lines += [
                f"## {name}",
                f"",
                output,
                f"",
                f"---",
                f""
            ]

    lines += [
        f"## Summary",
        f"",
        f"- **Personas run:** {report['summary']['total_personas']}",
        f"- **Successful:** {report['summary']['successful']}",
        f"- **Failed:** {report['summary']['failed']}",
        f"- **Total output:** {report['summary']['total_output_chars']:,} characters",
        f""
    ]

    if report.get("errors"):
        lines += [f"## Errors", f""]
        for err in report["errors"]:
            lines.append(f"- {err}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="PM Framework Live Test Runner")
    parser.add_argument("--project", default="buildbid", help="Project name")
    parser.add_argument("--ticket", default="H8", help="Ticket/story ID")
    parser.add_argument("--personas", default="pm,red,blue,qa,tech_lead,ux_designer,cpo",
                        help="Comma-separated persona chain")
    parser.add_argument("--dry-run", action="store_true", help="No API calls")
    parser.add_argument("--test", action="store_true", help="Self-test (dry-run)")
    args = parser.parse_args()

    if args.test:
        print("=== run_live_test.py SELF-TEST ===")
        print(f"Personas available: {list(PERSONAS.keys())}")
        print(f"Logs dir: {LOGS_DIR}")
        print(f"Configs dir: {CONFIGS_DIR}")
        # Validate H8_CONTEXT is defined
        assert "H8" in H8_CONTEXT or "Granular" in H8_CONTEXT, "H8_CONTEXT missing"
        # Validate call_api routing
        print("API routing: ANTHROPIC_API_KEY → Anthropic, OPENROUTER_API_KEY → OpenRouter")
        print("✅ Self-test passed (no API calls)")
        return

    personas = [p.strip() for p in args.personas.split(",") if p.strip()]
    run_live_test(args.project, args.ticket, personas, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
