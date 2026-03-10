# Third-Party Plugin Intake Policy

## Overview
This policy governs the intake, evaluation, and approval of third-party plugins, MCPs (Model Context Protocols), models, and agent behaviors into the OpenClaw ecosystem. Our posture differs from open ecosystems by defaulting to a curated, high-security model.

## Core Principles
1. **Security First**: All external code execution and data access must be scoped, sandboxed, and auditable.
2. **Value-Add Verification**: Plugins must provide verifiable, measurable improvements to agent autonomy, coordination, or capability.
3. **Stability & Fallback**: Integrations must support graceful degradation. If a third-party service fails, the agentic loop must not permanently halt.

## Intake Process

### 1. Discovery & Proposal
- **Source**: Competitor sweeps, community hubs (e.g., ClawHub, LobeHub), or direct agent identification.
- **Action**: Create an intake proposal in `TODO.md` with:
  - Source URL/Reference
  - Expected capability gain
  - Required permissions (network, filesystem, credentials)

### 2. Sandbox Evaluation
- **Isolation**: The plugin must be run in a restricted worktree or sandbox.
- **Audit**:
  - Review source code (if available) for telemetry, hardcoded keys, and unauthorized network calls.
  - Review MCP manifests for overly broad tool definitions.

### 3. Risk Assessment & Classification
Classify the integration into one of three tiers:
- **Adopt-Now**: Zero/low risk, high value, immediate integration.
- **Sandbox**: Medium risk or unverified value, requires running in isolated loops for 7-14 days.
- **Skip/Reject**: High risk, unmitigated telemetry, redundant capability, or poor stability.

### 4. Integration & Guardrails
- **Credential Management**: Any required secrets must use the standard environment variable injection (`~/.openclaw/secrets/`).
- **Telemetry & Logging**: Wrap plugin calls with our standard `call_llm` or tool invocation metrics to track success/failure rates.
- **Schema Validation**: If the plugin outputs JSON, it must be validated against a strict schema before being passed to downstream agents.

## Ongoing Monitoring
- Daily health sweeps will track the error rates of active third-party plugins.
- Plugins exceeding a 5% failure rate over 48 hours will be automatically sandboxed and reviewed.
