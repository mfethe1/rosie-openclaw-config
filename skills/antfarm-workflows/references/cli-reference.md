# Antfarm Workflows CLI Reference

All CLI commands use the full path to avoid PATH issues:

```bash
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js <command>
```

## Core Commands

```bash
# Install all workflows (creates agents + starts dashboard)
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js install

# Full uninstall (workflows, agents, crons, DB, dashboard)
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js uninstall [--force]

# Start a run
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow run <workflow-id> "<detailed task with acceptance criteria>"

# Check a run
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow status "<task or run-id prefix>"

# List all runs
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow runs

# Resume a failed run from the failed step
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow resume <run-id>

# View logs
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js logs [lines]

# Dashboard
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js dashboard [start] [--port N]
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js dashboard stop
```

## Workflow Management

```bash
# List available workflows
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow list

# Install/uninstall individual workflows
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow install <name>
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow uninstall <name>
node ~/.openclaw/workspace/antfarm/dist/cli/cli.js workflow uninstall --all [--force]
```