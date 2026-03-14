# Google Antigravity & Claude Opus Fix (JSON Schema 2020-12)

**Status:** FIXED (Feb 17, 2026)
**Author:** Rosie (Antigravity)

## Problem
When using `google-antigravity/claude-opus-4-6-thinking` (or other Google-routed Claude models), tool calls fail with:
`tools.13.custom.input_schema: JSON schema is invalid. It must match JSON Schema draft 2020-12`

## Root Cause
1. **Unsupported Type Constraints:** Google's Vertex AI layer for Claude enforces strict JSON Schema validation that rejects certain TypeBox patterns, specifically `Type.Optional(Type.Number({ minimum: 1 }))` used in `sessions_list`, `browser`, and other tools.
2. **Unsupported Union Types:** The `image` tool schema used `Type.Union([Type.String(), Type.Array(Type.String())])`, which generates `anyOf` at the top level of the parameter schema—rejected by Anthropic's API validation.
3. **Gateway Process Persistence:** The OpenClaw gateway process (PID 14663) was not restarting correctly via `openclaw gateway restart`. The LaunchAgent service restarted, but the old process held the port and kept running old code from memory, ignoring file patches.

## Solution

### 1. Patch Tool Schemas
Run the included fix script `fix-google-schemas.js` to patch the bundled distribution files:
- Converts `Type.Union([Type.String(), Type.Array(Type.String())])` -> `Type.Array(Type.String())` (simplifies image input)
- Converts `Type.Optional(Type.Number(...))` -> `Type.Optional(Type.String())` (removes numeric constraints like `minimum`)

**Run command:**
```bash
node ~/.openclaw/workspace/self_improvement/fix-google-schemas.js
```

### 2. Force Restart Gateway Process
The standard `openclaw gateway restart` command may fail to kill the underlying Node process if it's stuck or detached. You must kill the process ID manually to force a reload.

**Steps:**
1. Find the gateway process:
   ```bash
   ps aux | grep "openclaw-gateway\|node.*18789" | grep -v grep
   ```
2. Kill it (replace PID):
   ```bash
   kill -9 <PID>
   ```
3. Verify restart:
   ```bash
   ps aux | grep "openclaw-gateway\|node.*18789" | grep -v grep
   ```
   (Wait for launchd to restart it automatically)

## Verification
Spawn a subagent with the target model:
```bash
openclaw sessions spawn --agent main --model google-antigravity/claude-opus-4-6-thinking --task "Reply with exactly: SCHEMA_VERIFY_SUCCESS"
```
If it replies `SCHEMA_VERIFY_SUCCESS`, the fix is active.
