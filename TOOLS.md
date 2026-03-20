# TOOLS.md

## Channel IDs
- Telegram:  `-1003753060481`
- Telegram bot: `@RosieFetheBot`

## Shared paths
- Workspace: `/Users/harrisonfethe/.openclaw/workspace`
- Canonical data mount: `/Volumes/Edrive/`

## API token/key locations
All secrets stored in `~/.openclaw/secrets/` or environment variables. Never hardcode.
- AudioPod: env `AUDIOPOD_API_KEY`
- YouTube: env `GOOGLE`/`YOUTUBE` API key
- Twilio: `~/.openclaw/secrets/twilio.env`
- Google Ads: `~/.openclaw/secrets/google-ads.env`
- X/Twitter: `~/.openclaw/secrets/x-twitter.env`
- Schwab: `~/.openclaw/secrets/schwab.env`
- Gateway: `~/.openclaw/secrets/gateway_token`

## Runtime notes
- Keep command snippets and credentials in local env/secrets files only.
- Do not paste secrets into logs/chats/commits.

## Oh My OpenCode tool catalog (v3.9.0)

### Code search
- `grep`: Content search using regular expressions. Filter files by pattern.
- `glob`: Fast file pattern matching. Find files by name patterns.

### Edit
- `edit`: Hash-anchored LINE#ID format. Validates content hashes before applying changes.

### LSP (IDE features)
- `lsp_diagnostics`: Errors/warnings before build.
- `lsp_rename`: Rename symbol across entire workspace.
- `lsp_goto_definition`: Jump to symbol definition.
- `lsp_find_references`: Find all usages across workspace.
- `lsp_symbols`: File outline or workspace-wide symbol search.
- `lsp_prepare_rename`: Validate rename before executing.

### AST-Grep
- `ast_grep_search`: AST-aware code pattern search (25 languages).
- `ast_grep_replace`: AST-aware code replacement with dry-run mode.

### Delegation
- `task`: Category-based delegation (visual-engineering, deep, quick, ultrabrain, etc.).
- `background_output`: Retrieve background task results.
- `background_cancel`: Cancel running background tasks (always cancel individually by taskId).

### Sessions
- `session_list`: List all OpenCode sessions.
- `session_read`: Read messages and history from a session.
- `session_search`: Full-text search across session messages.
- `session_info`: Get session metadata and statistics.

### Visual
- `look_at`: Analyze PDFs, images, diagrams via Multimodal-Looker agent.

### Built-in MCPs
- **Exa**: Real-time web search (websearch_web_search_exa).
- **Context7**: Official documentation lookup for any library/framework.
- **Grep.app**: Code search across public GitHub repositories.

### CLI commands
- `auggie`: Augment Agent CLI at `/opt/homebrew/bin/auggie`. Supports `-p` (print/one-shot), `--quiet`, `--image`.
- `opencode`: OpenCode CLI at `/opt/homebrew/bin/opencode`. Supports `run` (one-shot), `serve` (headless), `web` (browser UI).
- `openclaw`: OpenClaw CLI at `/opt/homebrew/bin/openclaw`. Supports `doctor`, `update`, `gateway`, `secrets`.

## Coding Agent CLIs — Multi-Harness Routing

Use these tools to delegate coding work. Each harness has distinct strengths — route to the right one.

### Intelligent Routing Matrix

| Task Type | Primary Harness | Fallback | Why |
|-----------|----------------|----------|-----|
| Architecture decisions, debugging | **Claude Code** | OpenCode | Deep reasoning, problem decomposition |
| Backend API, DB schemas, security | **Codex** | Claude Code | Deterministic, security-focused |
| Frontend UI, docs, scaffolding | **Gemini** | Claude Code | Fast generation, multimodal, creative |
| Multi-agent orchestration, LSP/AST | **OpenCode** | Claude Code | 46 lifecycle hooks, deep tooling |
| Large codebase refactors (10+ files) | **Auggie** | OpenCode | Auto-indexes for deep retrieval |
| Quick one-file fix | **Direct edit** | — | No agent overhead |
| PR review | **Codex review** or **OpenCode pr** | Claude Code | Built-in diff awareness |
| Parallel issue fixes | **Git worktrees + multiple agents** | — | Each agent gets isolated branch |

### Claude Code
- **Best for**: Architecture, code review, complex debugging, problem decomposition.
- **One-shot**: `claude --permission-mode bypassPermissions --print "Your task"` (no PTY needed)
- **Background**: `claude --permission-mode bypassPermissions --print "Your task"` with `background:true`
- **When NOT to use**: Simple one-liners, frontend scaffolding, bulk generation.

### Codex (gpt-5.4)
- **Best for**: Backend implementation, DB schemas, security audits, deterministic coding.
- **One-shot**: `codex exec "Your prompt"` (PTY required)
- **Full auto**: `codex exec --full-auto "Your prompt"` (auto-approves in workspace)
- **Review**: `codex review --base origin/main`
- **Flags**: `--full-auto` (sandboxed auto-approve), `--yolo` (no sandbox, no approvals)

### Gemini CLI (v0.31.0)
- **Best for**: Frontend components, UI/UX, documentation, multimodal analysis, rapid prototyping.
- **One-shot**: `gemini -p "Your prompt"` (print mode)
- **With model**: `gemini -m gemini-3.1-pro "Your prompt"`
- **Sandbox mode**: `gemini --sandbox "Your prompt"` (isolated execution)
- **When to use**: Creative exploration, screenshot analysis, fast scaffolding.

### auggie (Augment Agent v0.17.1)
- **Best for**: Codebase-aware tasks — auggie auto-indexes the workspace for deep context retrieval.
- **One-shot**: `auggie -p --quiet "Your prompt"` (print mode, final answer only)
- **With images**: `auggie -p --image screenshot.png "Explain this UI"`
- **In a project**: `auggie -w ~/Projects/myapp -p "Add input validation to the signup form"`
- **Sequential tasks**: `auggie -p "Task 1" --queue "Task 2" --queue "Task 3"`
- **Interactive**: `auggie "Your prompt"` (conversational session, supports `--continue` / `--resume`)
- **When to use**: Large refactors where deep codebase understanding matters, multi-file changes that need cross-reference context.

### opencode (OpenCode v1.2.16)
- **Best for**: Structured coding sessions with built-in agent delegation (Sisyphus/Oracle/Hephaestus harness).
- **One-shot**: `opencode run "Your prompt"`
- **With model**: `opencode run -m anthropic/claude-sonnet-4-6 "Your prompt"`
- **Continue session**: `opencode run --continue "Follow-up prompt"`
- **Attach to running**: `opencode attach http://localhost:PORT`
- **Background server**: `opencode serve` (headless, attach from multiple terminals)
- **Web UI**: `opencode web` (browser-based interface)
- **PR workflow**: `opencode pr 130` (fetches + checks out PR branch, launches session)
- **When to use**: Complex multi-step coding with agent orchestration, PR reviews, tasks needing LSP/AST tools.

### Cross-Harness Handoff Protocol

When one harness completes partial work and another should pick up:
1. Write structured handoff to `~/.openclaw/workspace/.harness-handoff.json`
2. Include: `task_id`, `from`, `to`, `spec`, `files_modified`, `context`, `verification`
3. Receiving harness reads handoff on session start via hooks
4. Verification criteria MUST include runnable test commands

### Async Execution Pattern (for tasks >30s)

All harnesses support background execution to avoid API timeouts:
1. Spawn task as background process → get sessionId/jobId immediately
2. Poll status every 25 seconds (safely under 30s API timeout)
3. On "running": log tail provides visibility into progress
4. On "completed": collect output and verify
5. Never block main reasoning loop waiting for compilation/tests
