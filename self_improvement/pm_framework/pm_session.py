#!/usr/bin/env python3
"""
pm_session.py — PM Session Runner (Enterprise Edition)
Runs multi-persona PM review sessions with phased memory-stream aggregation.

Usage:
    # Simple session (backward compatible)
    python3 pm_session.py run --project "BuildBid" \
        --context "Estimating module complete, need lot model persistence" \
        --personas pm,red,blue,qa

    # From project config
    python3 pm_session.py run --project "BuildBid" --config project_configs/buildbid.json

    # Phased enterprise session (auto-selects team)
    python3 pm_session.py run --project "BuildBid" \
        --config project_configs/buildbid.json \
        --mode phased \
        --industry construction \
        --stage growth \
        --focus feature_development

    # With verbose output
    python3 pm_session.py run --project "BuildBid" --context "..." --verbose

    # Self-test (no API calls)
    python3 pm_session.py --test
"""

import os
import sys
import json
import argparse
import datetime
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any

# Graceful event_logger import
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from event_logger import log_event
except ImportError:
    def log_event(event_type, data=None, **kwargs):
        pass

from personas import (
    get_persona, build_system_prompt, PERSONAS,
    list_personas, get_tech_lead_for_domain,
    CustomerPersonaGenerator, TeamBuilder
)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"
LOGS_DIR = Path(__file__).parent / "logs"

# ---------------------------------------------------------------------------
# PERSONA FLOW (legacy linear mode)
# ---------------------------------------------------------------------------

PERSONA_FLOW = {
    "pm": {"label": "PM Analysis", "depends_on": []},
    "red": {"label": "Red Team Critique", "depends_on": ["pm"]},
    "blue": {"label": "Blue Team Defense", "depends_on": ["pm", "red"]},
    "interviewer": {"label": "User Story Interview", "depends_on": ["pm"]},
    "qa": {"label": "QA Review", "depends_on": ["pm", "blue"]},
    "marketing": {"label": "Marketing Strategy", "depends_on": ["pm"]},
    # Extended roles
    "cpo": {"label": "CPO Strategic Assessment", "depends_on": ["pm"]},
    "tech_lead": {"label": "Technical Lead Review", "depends_on": ["pm"]},
    "engineering_manager": {"label": "Engineering Manager Review", "depends_on": ["pm", "tech_lead"]},
    "ux_designer": {"label": "UX/UI Design Review", "depends_on": ["pm", "interviewer"]},
    "data_scientist": {"label": "Data Science Assessment", "depends_on": ["pm", "tech_lead"]},
    "devops": {"label": "DevOps / Infrastructure Review", "depends_on": ["pm", "tech_lead"]},
    "security": {"label": "Security Audit", "depends_on": ["pm", "red"]},
    "tech_writer": {"label": "Technical Writing Review", "depends_on": ["pm", "qa"]},
    "solutions_architect": {"label": "Solutions Architecture Review", "depends_on": ["pm", "tech_lead"]},
    "performance_engineer": {"label": "Performance Engineering Review", "depends_on": ["pm", "tech_lead", "devops"]},
    "product_marketing": {"label": "Product Marketing Assessment", "depends_on": ["pm", "cpo"]},
    "sales_engineer": {"label": "Sales Engineering Review", "depends_on": ["pm", "product_marketing"]},
    "customer_success": {"label": "Customer Success Planning", "depends_on": ["pm", "product_marketing"]},
    "business_analyst": {"label": "Business Analysis", "depends_on": ["pm"]},
    "legal": {"label": "Legal / Compliance Review", "depends_on": ["pm", "security"]},
    "chaos_engineer": {"label": "Chaos Engineering Assessment", "depends_on": ["pm", "red", "devops"]},
    "ethical_ai": {"label": "Ethical AI Review", "depends_on": ["pm", "data_scientist"]},
    "competitive_intel": {"label": "Competitive Intelligence Analysis", "depends_on": ["pm", "cpo"]},
    "accessibility": {"label": "Accessibility Audit", "depends_on": ["pm", "ux_designer"]},
}

# ---------------------------------------------------------------------------
# PHASED SESSION DEFINITION
# ---------------------------------------------------------------------------

PHASES = [
    {
        "name": "Discovery",
        "description": "Requirements gathering via user interviews and customer personas",
        "roles": ["interviewer"],
        "customer_roles": True,  # include customer personas if available
        "synthesizer": None,
    },
    {
        "name": "Planning",
        "description": "Sprint planning, architecture, and business analysis",
        "roles": ["pm", "tech_lead", "solutions_architect", "business_analyst", "engineering_manager"],
        "customer_roles": False,
        "synthesizer": "pm",
    },
    {
        "name": "Review",
        "description": "Adversarial critique — security, chaos, and competitive analysis",
        "roles": ["red", "chaos_engineer", "security", "competitive_intel", "ethical_ai"],
        "customer_roles": False,
        "synthesizer": None,
    },
    {
        "name": "Defense",
        "description": "Mitigations and strengthened plan",
        "roles": ["blue", "engineering_manager"],
        "customer_roles": False,
        "synthesizer": "blue",
    },
    {
        "name": "Quality",
        "description": "Completeness check — QA, accessibility, documentation",
        "roles": ["qa", "accessibility", "tech_writer"],
        "customer_roles": False,
        "synthesizer": "qa",
    },
    {
        "name": "Go-to-Market",
        "description": "Launch readiness — marketing, sales, and customer success",
        "roles": ["product_marketing", "sales_engineer", "customer_success"],
        "customer_roles": False,
        "synthesizer": "product_marketing",
    },
    {
        "name": "Synthesis",
        "description": "CPO arbitrates all input and produces final decision",
        "roles": ["cpo"],
        "customer_roles": False,
        "synthesizer": "cpo",
    },
]


# ---------------------------------------------------------------------------
# ANTHROPIC API CALL
# ---------------------------------------------------------------------------

def call_anthropic(system_prompt: str, user_message: str, temperature: float = 0.3,
                   max_tokens: int = 2048) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"API error {e.code}: {body}")


# ---------------------------------------------------------------------------
# USER MESSAGE BUILDERS
# ---------------------------------------------------------------------------

def build_user_message(role: str, project: str, context: str, prior_outputs: dict) -> str:
    """Build the user message for a persona given prior outputs (legacy + extended roles)."""
    msg = f"## Project: {project}\n\n## Current Context\n{context}\n"

    # --- Tier 0 core ---
    if role == "pm":
        msg += "\nAnalyze this project context. Generate a sprint plan, user stories with acceptance criteria, and risk register."

    elif role == "red":
        pm_output = prior_outputs.get("pm", "No PM analysis available.")
        msg += f"\n## PM Sprint Plan (to critique)\n{pm_output}\n\nFind every flaw, gap, and risk in this plan. Be adversarial."

    elif role == "blue":
        pm_output = prior_outputs.get("pm", "")
        red_output = prior_outputs.get("red", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Red Team Critiques\n{red_output}\n\nDefend the plan, address each critique, and propose concrete mitigations."

    elif role == "interviewer":
        pm_output = prior_outputs.get("pm", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\nGenerate user personas for this project and extract requirements through simulated interviews."

    elif role == "qa":
        pm_output = prior_outputs.get("pm", "")
        blue_output = prior_outputs.get("blue", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Blue Team Mitigations\n{blue_output}\n\nReview for testability. Write test scenarios and flag gaps."

    elif role == "marketing":
        pm_output = prior_outputs.get("pm", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\nCreate a marketing strategy for this sprint's deliverables."

    # --- Tier 1 ---
    elif role == "cpo":
        pm_output = prior_outputs.get("pm", "")
        all_outputs = _summarize_prior(prior_outputs, exclude=["cpo"])
        msg += f"\n## All Team Inputs\n{all_outputs}\n\nAs CPO, review all team input. Produce a strategic assessment: go/no-go, top 3 business bets, success metrics, and your final arbitration of conflicting priorities."

    elif role == "tech_lead":
        pm_output = prior_outputs.get("pm", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\nProvide a technical architecture review, identify top technical risks, and make build/buy/integrate recommendations."

    elif role == "engineering_manager":
        pm_output = prior_outputs.get("pm", "")
        tech_output = prior_outputs.get("tech_lead", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Technical Lead Review\n{tech_output}\n\nProvide capacity planning, sprint commitment analysis, and dependency mapping."

    # --- Tier 2 ---
    elif role == "ux_designer":
        pm_output = prior_outputs.get("pm", "")
        interviewer_output = prior_outputs.get("interviewer", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## User Research\n{interviewer_output}\n\nReview user flows, identify UX risks, and provide accessibility and design system recommendations."

    elif role == "data_scientist":
        pm_output = prior_outputs.get("pm", "")
        tech_output = prior_outputs.get("tech_lead", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Technical Lead Review\n{tech_output}\n\nAssess data and ML feasibility, data readiness, and model risk."

    elif role == "devops":
        pm_output = prior_outputs.get("pm", "")
        tech_output = prior_outputs.get("tech_lead", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Technical Lead Review\n{tech_output}\n\nReview infrastructure impact, CI/CD requirements, deployment strategy, and observability plan."

    elif role == "security":
        pm_output = prior_outputs.get("pm", "")
        red_output = prior_outputs.get("red", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Red Team Findings\n{red_output}\n\nConduct a security review: OWASP Top 10, threat modeling, compliance requirements, and authentication review."

    elif role == "tech_writer":
        pm_output = prior_outputs.get("pm", "")
        qa_output = prior_outputs.get("qa", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## QA Review\n{qa_output}\n\nIdentify documentation gaps, draft changelog entries, and flag stale documentation risk."

    elif role == "solutions_architect":
        pm_output = prior_outputs.get("pm", "")
        tech_output = prior_outputs.get("tech_lead", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Technical Lead Review\n{tech_output}\n\nReview integration architecture, API design, and third-party vendor risks."

    elif role == "performance_engineer":
        pm_output = prior_outputs.get("pm", "")
        devops_output = prior_outputs.get("devops", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## DevOps Review\n{devops_output}\n\nDefine latency budgets, identify performance risks, and produce a load test plan."

    # --- Tier 3 ---
    elif role == "product_marketing":
        pm_output = prior_outputs.get("pm", "")
        cpo_output = prior_outputs.get("cpo", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## CPO Assessment\n{cpo_output}\n\nCreate launch positioning, messaging hierarchy, competitive battlecard update, and success metrics."

    elif role == "sales_engineer":
        pm_output = prior_outputs.get("pm", "")
        mktg_output = prior_outputs.get("product_marketing", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Product Marketing\n{mktg_output}\n\nProduce a demo script, top 5 technical objections with responses, and POC success criteria."

    elif role == "customer_success":
        pm_output = prior_outputs.get("pm", "")
        mktg_output = prior_outputs.get("product_marketing", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Product Marketing\n{mktg_output}\n\nCreate an onboarding update plan, feature adoption playbook, and churn risk assessment."

    elif role == "business_analyst":
        pm_output = prior_outputs.get("pm", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\nProduce a requirements traceability matrix, ROI model, process change impact analysis, and gap analysis."

    elif role == "legal":
        pm_output = prior_outputs.get("pm", "")
        security_output = prior_outputs.get("security", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Security Review\n{security_output}\n\nConduct a legal and compliance review: data privacy, regulatory requirements, IP risks, and contract implications."

    # --- Tier 5 ---
    elif role == "chaos_engineer":
        pm_output = prior_outputs.get("pm", "")
        devops_output = prior_outputs.get("devops", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## DevOps Review\n{devops_output}\n\nProduce a chaos experiment catalog with 8-12 failure scenarios ranked by probability × impact."

    elif role == "ethical_ai":
        pm_output = prior_outputs.get("pm", "")
        ds_output = prior_outputs.get("data_scientist", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## Data Science Assessment\n{ds_output}\n\nConduct an ethical AI review: bias risks, fairness testing requirements, human oversight needs, and regulatory mapping."

    elif role == "competitive_intel":
        pm_output = prior_outputs.get("pm", "")
        cpo_output = prior_outputs.get("cpo", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## CPO Assessment\n{cpo_output}\n\nUpdate competitive position, forecast competitor responses, and recommend messaging updates."

    elif role == "accessibility":
        pm_output = prior_outputs.get("pm", "")
        ux_output = prior_outputs.get("ux_designer", "")
        msg += f"\n## PM Sprint Plan\n{pm_output}\n\n## UX Review\n{ux_output}\n\nConduct a WCAG 2.1 AA accessibility audit, classify debt by severity, and produce an AT testing plan."

    # --- Customer personas ---
    elif role.startswith("customer_"):
        pm_output = prior_outputs.get("pm", "")
        interviewer_output = prior_outputs.get("interviewer", "")
        msg += f"\n## Product Plan\n{pm_output}\n\n## Research Context\n{interviewer_output}\n\nAs your persona, provide authentic feedback on this plan. What excites you? What concerns you? What questions would you ask? What objections do you have?"

    else:
        msg += f"\nReview this project context and provide your expert assessment from your role's perspective."

    return msg


def build_synthesis_message(project: str, context: str, outputs: dict) -> str:
    summary = "\n\n".join([
        f"## {role.upper()} Output\n{text}"
        for role, text in outputs.items()
        if role != "synthesis" and not role.startswith("customer_")
    ])
    return (
        f"## Project: {project}\n\n## Context\n{context}\n\n"
        f"{summary}\n\n"
        "As PM, synthesize all the above. Produce a final action plan: "
        "top 3 priorities, resolved risks, QA requirements, and next sprint goal."
    )


def _summarize_prior(outputs: dict, exclude: Optional[List[str]] = None) -> str:
    exclude = exclude or []
    parts = []
    for role, text in outputs.items():
        if role in exclude:
            continue
        parts.append(f"### [{role.upper()}]\n{text[:600]}{'...' if len(text) > 600 else ''}")
    return "\n\n".join(parts) if parts else "No prior outputs."


# ---------------------------------------------------------------------------
# SINGLE-ROLE RUNNER
# ---------------------------------------------------------------------------

def run_role(persona: Dict[str, Any], project: str, context: str, prior_outputs: dict,
             verbose: bool = False) -> str:
    """Run a single persona and return its output."""
    role = persona["role"]
    system_prompt = persona.get("system_prompt", "")
    if not system_prompt and role in PERSONAS:
        system_prompt = build_system_prompt(role)

    temperature = persona.get("temperature", 0.4)
    label = PERSONA_FLOW.get(role, {}).get("label", persona.get("name", role))

    user_msg = build_user_message(role, project, context, prior_outputs)
    result = call_anthropic(system_prompt, user_msg, temperature=temperature)
    return result


# ---------------------------------------------------------------------------
# LINEAR SESSION RUNNER (legacy)
# ---------------------------------------------------------------------------

def run_session(project: str, context: str, personas: list, verbose: bool = False) -> dict:
    """
    Run a linear multi-persona session (backward compatible with original API).

    Args:
        project: Project name
        context: Project context string
        personas: List of role strings (e.g. ["pm", "red", "blue", "qa"])
        verbose: If True, print full persona outputs

    Returns:
        Session report dict
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    outputs = {}

    print(f"\n{'='*60}")
    print(f"PM SESSION: {project}")
    print(f"Personas: {', '.join(personas)}")
    print(f"{'='*60}\n")

    for role in personas:
        if role not in PERSONAS:
            print(f"[WARN] Unknown persona '{role}', skipping.")
            continue

        persona = get_persona(role)
        flow = PERSONA_FLOW.get(role, {})
        label = flow.get("label", persona["name"])

        print(f"[{label}] Running...")
        system_prompt = build_system_prompt(role)
        user_msg = build_user_message(role, project, context, outputs)

        try:
            result = call_anthropic(system_prompt, user_msg, temperature=persona["temperature"])
            outputs[role] = result
            if verbose:
                print(f"\n--- {label} ---\n{result}\n")
            else:
                preview = result[:200].replace("\n", " ")
                print(f"  ✓ {preview}...")
        except Exception as e:
            outputs[role] = f"ERROR: {e}"
            print(f"  ✗ Error: {e}")

    # PM synthesis
    if "pm" in personas:
        print("\n[PM Synthesis] Generating final recommendations...")
        synthesis_msg = build_synthesis_message(project, context, outputs)
        try:
            synthesis = call_anthropic(
                build_system_prompt("pm", "You are synthesizing a full multi-agent review session."),
                synthesis_msg,
                temperature=0.3
            )
            outputs["synthesis"] = synthesis
            if verbose:
                print(f"\n--- Final Synthesis ---\n{synthesis}\n")
            else:
                print(f"  ✓ Synthesis complete ({len(synthesis)} chars)")
        except Exception as e:
            outputs["synthesis"] = f"ERROR: {e}"
            print(f"  ✗ Synthesis error: {e}")

    report = {
        "project": project,
        "timestamp": timestamp,
        "context": context,
        "personas_run": personas,
        "outputs": outputs,
        "model": MODEL,
        "mode": "linear"
    }

    _save_and_log(report, project)
    return report


# ---------------------------------------------------------------------------
# PHASED SESSION RUNNER
# ---------------------------------------------------------------------------

def run_phased_session(
    project: str,
    context: str,
    industry: str = "software",
    stage: str = "growth",
    focus: str = "feature_development",
    domain: Optional[str] = None,
    include_customers: bool = True,
    customer_count: int = 2,
    verbose: bool = False,
    skip_phases: Optional[List[str]] = None,
) -> dict:
    """
    Run a phased enterprise session with memory-stream aggregation.

    Each phase passes its outputs to the next phase as context.
    Follows the MetaGPT memory-stream aggregation pattern.

    Args:
        project: Project name
        context: Project context string
        industry: Industry context (construction, healthcare, fintech, etc.)
        stage: Company stage (startup, growth, enterprise, maintenance)
        focus: Session focus (feature_development, bug_fix, security_audit, launch, pivot)
        domain: Technical domain override for tech_lead persona
        include_customers: Whether to include synthetic customer personas in Discovery
        customer_count: Number of customer personas to generate
        verbose: Print full outputs
        skip_phases: List of phase names to skip (e.g. ["Go-to-Market"])

    Returns:
        Full session report dict with phase-by-phase outputs
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    skip_phases = skip_phases or []

    # Build the team
    builder = TeamBuilder(domain=domain or _infer_domain(industry))
    team = builder.for_project(
        project_type="saas",
        industry=industry,
        stage=stage,
        focus=focus,
        include_customers=include_customers,
        customer_count=customer_count,
    )
    team_by_role = {p["role"]: p for p in team}

    print(f"\n{'='*70}")
    print(f"PHASED PM SESSION: {project}")
    print(f"Industry: {industry} | Stage: {stage} | Focus: {focus}")
    print(f"Team: {len(team)} personas")
    print(f"{'='*70}\n")
    print(builder.describe_team(team))
    print()

    all_outputs: Dict[str, str] = {}
    phase_reports: Dict[str, Dict[str, Any]] = {}

    for phase in PHASES:
        phase_name = phase["name"]
        if phase_name in skip_phases:
            print(f"[SKIP] Phase: {phase_name}")
            continue

        print(f"\n{'─'*60}")
        print(f"PHASE: {phase_name} — {phase['description']}")
        print(f"{'─'*60}")

        phase_roles = list(phase["roles"])

        # Add customer personas to Discovery phase
        if phase.get("customer_roles") and include_customers:
            for role_key in team_by_role:
                if role_key.startswith("customer_"):
                    phase_roles.append(role_key)

        phase_outputs: Dict[str, str] = {}

        for role in phase_roles:
            # Get persona from team (may have domain adaptation)
            persona = team_by_role.get(role)
            if persona is None:
                # Try base PERSONAS
                if role in PERSONAS:
                    persona = PERSONAS[role]
                else:
                    print(f"  [SKIP] Role '{role}' not in team, skipping.")
                    continue

            name = persona.get("name", role)
            label = PERSONA_FLOW.get(role, {}).get("label", name)
            print(f"  [{label}] Running...")

            try:
                result = run_role(persona, project, context, all_outputs, verbose=verbose)
                phase_outputs[role] = result
                all_outputs[role] = result  # accumulate in global memory stream

                if verbose:
                    print(f"\n    --- {label} ---\n{result}\n")
                else:
                    preview = result[:150].replace("\n", " ")
                    print(f"    ✓ {preview}...")
            except Exception as e:
                error_msg = f"ERROR: {e}"
                phase_outputs[role] = error_msg
                all_outputs[role] = error_msg
                print(f"    ✗ Error ({role}): {e}")

        # Phase synthesis (if defined)
        synthesizer_role = phase.get("synthesizer")
        if synthesizer_role and phase_outputs:
            print(f"\n  [{phase_name} Synthesis via {synthesizer_role}] Summarizing...")
            synthesizer = team_by_role.get(synthesizer_role) or PERSONAS.get(synthesizer_role)
            if synthesizer:
                phase_summary_msg = (
                    f"## Project: {project}\n\n## Context\n{context}\n\n"
                    f"## {phase_name} Phase Outputs\n"
                    + "\n\n".join(f"### [{r.upper()}]\n{t}" for r, t in phase_outputs.items())
                    + f"\n\nSummarize the key decisions, risks, and action items from this {phase_name} phase. Be concise."
                )
                try:
                    synth = call_anthropic(
                        synthesizer.get("system_prompt", ""),
                        phase_summary_msg,
                        temperature=synthesizer.get("temperature", 0.35)
                    )
                    phase_key = f"{phase_name.lower()}_synthesis"
                    phase_outputs[phase_key] = synth
                    all_outputs[phase_key] = synth
                    print(f"    ✓ Phase synthesis: {len(synth)} chars")
                except Exception as e:
                    print(f"    ✗ Phase synthesis error: {e}")

        phase_reports[phase_name] = phase_outputs
        print(f"\n  ✅ Phase '{phase_name}' complete ({len(phase_outputs)} outputs)")

    report = {
        "project": project,
        "timestamp": timestamp,
        "context": context,
        "industry": industry,
        "stage": stage,
        "focus": focus,
        "team": [{"role": p["role"], "name": p["name"]} for p in team],
        "phases": phase_reports,
        "outputs": all_outputs,
        "model": MODEL,
        "mode": "phased",
    }

    _save_and_log(report, project)

    # Print CPO synthesis as final output
    final = all_outputs.get("synthesis_synthesis") or all_outputs.get("cpo") or "No synthesis generated."
    print(f"\n{'='*70}\nFINAL SYNTHESIS (CPO)\n{'='*70}")
    print(final)

    return report


def _infer_domain(industry: str) -> str:
    domain_map = {
        "construction": "construction",
        "building": "construction",
        "biotech": "biotech",
        "pharma": "biotech",
        "healthcare": "biotech",
        "finance": "finance",
        "fintech": "finance",
        "banking": "finance",
        "marketing": "marketing",
        "adtech": "marketing",
    }
    return domain_map.get(industry.lower(), "software")


def _save_and_log(report: dict, project: str):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    safe_project = project.lower().replace(" ", "-")
    mode = report.get("mode", "linear")
    report_path = LOGS_DIR / f"session-{safe_project}-{mode}-{date_str}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n✅ Session complete. Report: {report_path}")
    log_event("pm_session_complete", {
        "project": project,
        "mode": mode,
        "report": str(report_path)
    })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PM Session Runner (Enterprise Edition)")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a PM session")
    run_parser.add_argument("--project", required=False, help="Project name")
    run_parser.add_argument("--context", default="", help="Current project context")
    run_parser.add_argument("--config", help="Path to project config JSON")
    run_parser.add_argument("--personas", default="pm,red,blue,qa",
                            help="Comma-separated persona roles (linear mode)")
    run_parser.add_argument("--verbose", action="store_true", help="Print full persona outputs")
    run_parser.add_argument("--mode", choices=["linear", "phased"], default="linear",
                            help="Session mode: linear (default) or phased (enterprise)")
    run_parser.add_argument("--industry", default="software",
                            help="Industry context for phased mode (construction, healthcare, fintech, ...)")
    run_parser.add_argument("--stage", default="growth",
                            choices=["startup", "growth", "enterprise", "maintenance"],
                            help="Company stage for phased mode")
    run_parser.add_argument("--focus", default="feature_development",
                            choices=["feature_development", "bug_fix", "security_audit", "launch", "pivot", "data_ml", "accessibility"],
                            help="Session focus for phased mode")
    run_parser.add_argument("--domain", default=None,
                            help="Technical domain override for tech_lead (software, construction, biotech, marketing, finance)")
    run_parser.add_argument("--skip-phases", default="",
                            help="Comma-separated phase names to skip (e.g. 'Go-to-Market,Quality')")
    run_parser.add_argument("--no-customers", action="store_true",
                            help="Skip synthetic customer personas in phased mode")

    parser.add_argument("--test", action="store_true", help="Run self-test without API calls")

    args = parser.parse_args()

    if args.test or (hasattr(args, 'command') and args.command is None and '--test' in sys.argv):
        _run_self_test()
        return

    if args.command == "run":
        project = args.project
        context = args.context

        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                print(f"Config not found: {config_path}")
                sys.exit(1)
            with open(config_path) as f:
                config = json.load(f)
            project = project or config.get("name", "Unknown")
            context = context or json.dumps({
                "description": config.get("description", ""),
                "current_state": config.get("current_state", ""),
                "known_issues": config.get("known_issues", []),
                "next_priorities": config.get("next_priorities", [])
            }, indent=2)

        if not project:
            print("Error: --project or --config required")
            sys.exit(1)

        if args.mode == "phased":
            skip_phases = [p.strip() for p in args.skip_phases.split(",") if p.strip()]
            report = run_phased_session(
                project=project,
                context=context,
                industry=args.industry,
                stage=args.stage,
                focus=args.focus,
                domain=args.domain,
                include_customers=not args.no_customers,
                verbose=args.verbose,
                skip_phases=skip_phases,
            )
        else:
            personas = [p.strip() for p in args.personas.split(",")]
            report = run_session(project, context, personas, verbose=args.verbose)
            print("\n" + "="*60)
            print("FINAL SYNTHESIS")
            print("="*60)
            print(report["outputs"].get("synthesis", "No synthesis generated."))
    else:
        parser.print_help()


def _run_self_test():
    print("=== pm_session.py SELF-TEST ===\n")

    # 1. Persona list
    from personas import list_personas
    all_personas = list_personas()
    print(f"Personas available: {len(all_personas)}")
    print(f"  Roles: {[p['role'] for p in all_personas]}")

    # 2. build_user_message for all known roles
    print("\n--- build_user_message coverage ---")
    prior = {
        "pm": "Sample PM output for testing",
        "red": "Sample Red output",
        "blue": "Sample Blue output",
        "interviewer": "Sample interviewer output",
        "devops": "Sample devops output",
        "tech_lead": "Sample tech lead output",
        "cpo": "Sample CPO output",
        "data_scientist": "Sample DS output",
        "ux_designer": "Sample UX output",
        "product_marketing": "Sample marketing output",
        "security": "Sample security output",
        "qa": "Sample QA output",
    }
    test_roles = list(PERSONAS.keys()) + ["customer_novice", "customer_expert"]
    for role in test_roles:
        try:
            msg = build_user_message(role, "TestProject", "Test context", prior)
            assert len(msg) > 50, f"Message too short for role {role}"
            print(f"  [{role}]: ✓ ({len(msg)} chars)")
        except Exception as e:
            print(f"  [{role}]: ✗ {e}")

    # 3. TeamBuilder
    print("\n--- TeamBuilder ---")
    builder = TeamBuilder()
    team = builder.for_project(
        project_type="saas",
        industry="construction",
        stage="growth",
        focus="feature_development"
    )
    assert len(team) >= 5
    print(f"  for_project team: {len(team)} personas")
    print(f"  Roles: {[p['role'] for p in team]}")

    # 4. CustomerPersonaGenerator
    print("\n--- CustomerPersonaGenerator ---")
    gen = CustomerPersonaGenerator()
    customers = gen.generate(
        product="BuildBid",
        industry="construction",
        count=3,
        expertise_distribution={"novice": 1, "intermediate": 1, "expert": 1},
        roles=["general_contractor", "estimator", "architect"]
    )
    assert len(customers) == 3
    for c in customers:
        print(f"  {c['name']} | {c['expertise']} | tech={c['tech_savviness']}/10")

    # 5. Phase structure validation
    print("\n--- Phase structure ---")
    for phase in PHASES:
        print(f"  {phase['name']}: {phase['roles']}")

    print("\n✅ Self-test passed (no API calls made)")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _run_self_test()
        sys.exit(0)
    main()
