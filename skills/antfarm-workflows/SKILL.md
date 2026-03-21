---
name: antfarm-workflows
description: Trigger this skill when the user asks to run an antfarm workflow, asks for the status of antfarm, or wants to install/uninstall antfarm workflows. This handles multi-agent orchestrated pipelines like 'feature-dev' or 'bug-fix'.
user-invocable: false
---

# Antfarm Workflows

Multi-agent workflow orchestration using specialized agents (planner, developer, verifier, tester, reviewer) running as cron jobs that poll a shared SQLite database.

## Core Interaction
Interact with Antfarm via its CLI:
`node ~/.openclaw/workspace/antfarm/dist/cli/cli.js <command>`

For a complete CLI reference and workflow management commands, read [references/cli-reference.md](./references/cli-reference.md).

## Running Workflows
To start a run:
`node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow run <workflow-id> "<detailed task with acceptance criteria>"`

Available workflow IDs: `feature-dev`, `bug-fix`, `security-audit`.

## Gotchas & Common Failures
- **Vague Task Strings**: A vague task string produces bad results. Always ensure the task includes specific details, constraints, and explicit acceptance criteria before starting a run. If the user request is vague, ask clarifying questions before triggering.
- **Path Issues**: Always use the absolute path `~/.openclaw/workspace/antfarm/dist/cli/cli.js`. Do not rely on relative paths or global aliases unless explicitly configured.
- **Stuck Workflows**: Agents run on 15-minute cron intervals. If a run seems stalled, check its status (`workflow status`). To force-trigger an agent, find its job ID via the `cron` tool and trigger it manually, rather than assuming it's broken.

## Deep Dives
- [Workflow Creation & Customization](./references/creating-workflows.md)