# TOOLS.md

## Channel IDs
- Telegram:  `-1003753060481`
- Telegram bot: `@RosieFetheBot`

## Shared paths
- Workspace: `/Users/harrisonfethe/.openclaw/workspace`
- Canonical data mount: `/Volumes/Edrive/`

## API token/key locations
- AudioPod: secrets via env (`AUDIOPOD_API_KEY`), never hardcoded
- YouTube: `GOOGLE`/`YOUTUBE` API key via env
- Twilio: `~/.openclaw/secrets/twilio.env` (or env vars)
- Google Ads: `~/.openclaw/secrets/google-ads.env`
- X/Twitter: `~/.openclaw/secrets/x-twitter.env`
- Schwab token: `/Volumes/Edrive/Projects/agent-coordination/schwab_token.json`
- Local clawdbot copy: `~/.clawdbot/schwab_token.json`

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

## Coding Agent CLIs

Use these tools to delegate coding work. Always use `pty:true` when spawning via exec.
See the `coding-agent` skill for full patterns (background, monitoring, parallel worktrees).

### auggie (Augment Agent v0.17.1)
- **Best for**: Codebase-aware tasks — auggie auto-indexes the workspace for deep context retrieval.
- **One-shot**: `auggie -p --quiet "Your prompt"` (print mode, final answer only)
- **With images**: `auggie -p --image screenshot.png "Explain this UI"`
- **In a project**: `auggie -w ~/Projects/myapp -p "Add input validation to the signup form"`
- **Sequential tasks**: `auggie -p "Task 1" --queue "Task 2" --queue "Task 3"`
- **Interactive**: `auggie "Your prompt"` (conversational session, supports `--continue` / `--resume`)
- **When to use**: Large refactors where deep codebase understanding matters, multi-file changes that need cross-reference context.

### opencode (OpenCode v1.2.15)
- **Best for**: Structured coding sessions with built-in agent delegation (Sisyphus/Oracle/Hephaestus harness).
- **One-shot**: `opencode run "Your prompt"`
- **With model**: `opencode run -m anthropic/claude-sonnet-4-6 "Your prompt"`
- **Continue session**: `opencode run --continue "Follow-up prompt"`
- **Attach to running**: `opencode attach http://localhost:PORT`
- **Background server**: `opencode serve` (headless, attach from multiple terminals)
- **Web UI**: `opencode web` (browser-based interface)
- **PR workflow**: `opencode pr 130` (fetches + checks out PR branch, launches session)
- **When to use**: Complex multi-step coding with agent orchestration, PR reviews, tasks needing LSP/AST tools.

### Delegation patterns
| Task | Tool | Why |
|------|------|-----|
| Quick one-file fix | Direct edit | Fastest, no overhead |
| Multi-file refactor | `auggie -p` or `opencode run` | Deep codebase context |
| PR review | `opencode pr <n>` or `codex review` | Built-in diff awareness |
| New feature/app | `codex --full-auto` in background | Auto-approves, sandboxed |
| Parallel issue fixes | Git worktrees + multiple agents | Each agent gets isolated branch |
| Research + implement | `auggie -p` (indexes first) | Best retrieval for large codebases |
