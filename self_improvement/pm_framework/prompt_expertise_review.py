#!/usr/bin/env python3
"""Run a PM-led expert prompt review session for workflow and prompt quality."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


DEFAULT_PERSONAS = [
    "pm",
    "tech_lead",
    "engineering_manager",
    "security",
    "qa",
    "red",
    "blue",
    "solutions_architect",
]


def write_offline_report(
    script_dir: Path, project: str, context: str, personas: str
) -> Path:
    logs_dir = script_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = project.lower().replace(" ", "-")
    out = logs_dir / f"prompt-review-offline-{slug}-{ts}.md"
    roles = [r.strip() for r in personas.split(",") if r.strip()]

    lines = [
        f"# Offline Prompt Review — {project}",
        "",
        f"Timestamp: {datetime.now().isoformat()}",
        f"Context: {context}",
        "",
        "## Review Board",
        ", ".join(roles),
        "",
        "## Required Checks",
        "- PM: backlog clarity, dependency ordering, acceptance criteria quality",
        "- Tech Lead: architecture correctness, failure modes, complexity controls",
        "- Engineering Manager: execution realism, handoff quality, throughput bottlenecks",
        "- Security: auth/data handling risks and safe defaults",
        "- QA: testability and regression coverage",
        "- Red Team: adversarial edge cases and hidden assumptions",
        "- Blue Team: mitigation quality and residual risk",
        "- Solutions Architect: integration contracts and boundary definitions",
        "",
        "## Action Template",
        "1. List top 5 prompt failures seen in recent runs.",
        "2. Map each failure to one role check above.",
        "3. Patch the owning prompt file with a precise rule.",
        "4. Re-run verification (`openclaw doctor`, `openclaw health`, targeted workflow run).",
        "5. Keep only rules that measurably improve output quality.",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run PM-led expert review for prompt quality"
    )
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument(
        "--context", required=True, help="Prompt/workflow context to review"
    )
    parser.add_argument(
        "--personas",
        default=",".join(DEFAULT_PERSONAS),
        help="Comma-separated persona roles",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    env = dict(os.environ)

    if not env.get("ANTHROPIC_API_KEY"):
        candidates = sorted(
            Path("/Users/harrisonfethe/.openclaw/agents").glob(
                "*/agent/auth-profiles.json"
            )
        )
        for candidate in candidates:
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                continue
            profiles = data.get("profiles", {})
            for profile in profiles.values():
                token = profile.get("token")
                if (
                    profile.get("provider") == "anthropic"
                    and isinstance(token, str)
                    and token.startswith("sk-ant-api")
                ):
                    env["ANTHROPIC_API_KEY"] = token
                    break
            if env.get("ANTHROPIC_API_KEY"):
                break

    if not env.get("ANTHROPIC_API_KEY"):
        report = write_offline_report(
            script_dir, args.project, args.context, args.personas
        )
        print(
            f"No valid ANTHROPIC_API_KEY found. Wrote offline review template: {report}"
        )
        return 0
    cmd = [
        "python3",
        str(script_dir / "pm_session.py"),
        "run",
        "--project",
        args.project,
        "--context",
        args.context,
        "--personas",
        args.personas,
    ]

    completed = subprocess.run(cmd, cwd=str(script_dir), env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
