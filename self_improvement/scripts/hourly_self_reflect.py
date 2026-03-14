#!/usr/bin/env python3
"""
hourly_self_reflect.py — Agent Self-Improvement Engine v2.0

Michael's directive: "Every hour, ask yourself how would you build yourself
better than you are built now for better performance, more intelligence,
and better end-user experience. Then go make those changes."

Additional directive: "Be self-healing. Fix things proactively. Don't report
problems — fix them and report they're fixed."

This script:
1. Reads the agent's profile, recent memory, TODO, and past reflections
2. Queries memU for relevant context and past lessons
3. Calls a model with a self-improving prompt (the prompt itself evolves)
4. Applies concrete improvements to agent profiles, scripts, and configs
5. Stores lessons in memU for cross-agent learning
6. Self-heals: checks infrastructure health and fixes issues inline
7. Improves its own prompt based on what worked/failed

Usage: python3 hourly_self_reflect.py <agent_name>
"""

import sys
import os
import json
import datetime
import subprocess
import re
import random
import hashlib
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
AGENTS_DIR = WORKSPACE / "agents"
MEMORY_DIR = WORKSPACE / "memory"
SI_DIR = WORKSPACE / "self_improvement"
OUTPUTS_DIR = SI_DIR / "outputs"
CHANGELOG = SI_DIR / "CHANGELOG.md"
REFLECT_LOG = MEMORY_DIR / "self-reflect-log.md"
PROMPT_EVOLUTION_FILE = SI_DIR / "prompt_evolution.json"
MEMU_SERVER = WORKSPACE / "memu_server"

# memU config — canonical bridge contract on 8711
MEMU_URL = "http://localhost:8711"
MEMU_KEY = "openclaw-memu-local-2026"

# NATS bridge
NATS_BRIDGE = WORKSPACE / "infra" / "nats" / "nats_bridge.py"

# Sonar / OpenRouter config
SONAR_SCRIPT = Path.home() / ".openclaw" / "skills" / "openrouter-sonar" / "scripts" / "sonar_search.py"

# Event logger
try:
    from event_logger import log_event
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from event_logger import log_event
    except ImportError:
        def log_event(*args, **kwargs): pass

# Ledgers (dual-loop orchestration)
def _load_ledgers():
    import importlib.util

    try:
        spec = importlib.util.spec_from_file_location("ledgers", str(SI_DIR / "ledgers.py"))
        if spec is None or spec.loader is None:
            raise RuntimeError("ledgers module spec not found")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ImportError, OSError, SyntaxError):
        return None


_ledgers = _load_ledgers()
if _ledgers is not None:
    add_fact = getattr(_ledgers, "add_fact", lambda *a, **kw: None)
    get_task_ledger = getattr(_ledgers, "get_task_ledger", lambda: {"facts": [], "guesses": [], "plan": [], "blockers": []})
    get_progress_ledger = getattr(_ledgers, "get_progress_ledger", lambda: {"assignments": {}, "completed": [], "in_progress": []})
    get_agent_status = getattr(_ledgers, "get_agent_status", lambda a: {"agent": a, "active": [], "completed_count": 0})
else:
    def add_fact(*a, **kw):
        pass

    def get_task_ledger():
        return {"facts": [], "guesses": [], "plan": [], "blockers": []}

    def get_progress_ledger():
        return {"assignments": {}, "completed": [], "in_progress": []}

    def get_agent_status(a):
        return {"agent": a, "active": [], "completed_count": 0}


def _nats_call(*args):
    """Fire-and-forget NATS bridge call. Never blocks or fails the cycle."""
    try:
        subprocess.run(
            ["python3", str(NATS_BRIDGE)] + [str(a) for a in args],
            capture_output=True,
            timeout=5,
        )
    except Exception as e:
        print(f"[WARN] NATS bridge unavailable: {e}")


def _sonar_research(query, model="pro"):
    """Run a Sonar search via OpenRouter. Returns content string or empty on failure.
    Models: 'quick' (sonar), 'pro' (sonar-pro), 'reasoning' (sonar-reasoning-pro), 'deep' (sonar-deep-research)
    Fire-and-forget style — never blocks or crashes the cycle."""
    try:
        if not SONAR_SCRIPT.exists():
            return ""
        cmd = ["python3", str(SONAR_SCRIPT), "--json"]
        flag = {"pro": "--pro", "deep": "--deep", "reasoning": "--reasoning", "quick": ""}.get(model, "--pro")
        if flag:
            cmd.append(flag)
        cmd.append(query)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("ok"):
                return data.get("content", "")[:2000]  # Cap at 2k chars for prompt budget
        return ""
    except Exception as e:
        print(f"[WARN] Sonar research failed: {e}")
        return ""


def _load_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    deploy_env = Path("/Users/harrisonfethe/.openclaw/secrets/deploy.env")
    if deploy_env.exists():
        try:
            for line in deploy_env.read_text(encoding="utf-8").splitlines():
                line_stripped = line.strip()
                # Handle both "ANTHROPIC_API_KEY=..." and "export ANTHROPIC_API_KEY=..."
                if line_stripped.startswith("export "):
                    line_stripped = line_stripped[7:]
                if line_stripped.startswith("ANTHROPIC_API_KEY="):
                    return line_stripped.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception as e:
            print(f"[WARN] Failed to read deploy.env: {e}")

    return ""


ANTHROPIC_KEY = _load_anthropic_key()

AGENT_ROLES = {
    "rosie": "Coordinator, QA, and team lead. Owns protocol integrity, cycle quality, proactive discovery, and cross-agent orchestration. Must be the strongest at identifying what's broken and delegating fixes.",
    "mack": "Execution specialist. Owns technical implementation, automation scripts, infrastructure repair, and reproducible changes. Must be the fastest at shipping working code and fixing broken systems.",
    "winnie": "Research and vetting specialist. Owns discovery, dependency validation, external monitoring, capability scouting, and evidence-based recommendations. Must be the best at finding and validating new tools/approaches.",
    "lenny": "QA and resilience specialist. Owns failure-mode detection, health monitoring, guardrail hardening, post-change verification, and regression prevention. Must be the best at catching bugs before they compound.",
}

# Areas to focus on — rotated each cycle for breadth
IMPROVEMENT_DIMENSIONS = [
    # Intelligence
    "reasoning chain quality — fewer steps to correct conclusions",
    "pattern recognition — identifying recurring problems before they manifest",
    "knowledge synthesis — connecting insights across different domains and past cycles",
    "model selection strategy — choosing the right model for the right task",
    # Performance
    "execution speed — reducing time from decision to shipped change",
    "tool sequencing — optimal order of operations with minimal redundancy",
    "error recovery — automatic retry, fallback, and self-repair patterns",
    "resource efficiency — doing more with fewer tokens and API calls",
    # End-user experience
    "output clarity — clearer, more actionable communication",
    "proactive value — finding and fixing things before being asked",
    "cross-agent coordination — smoother handoffs, less duplication",
    "self-healing capability — detecting and repairing own infrastructure issues",
    # Memory & learning
    "lesson retention — storing and retrieving relevant past experiences",
    "prompt engineering — improving own prompts for better results",
    "verification quality — proving changes work, not just claiming they do",
    "continuous adaptation — adjusting behavior based on outcomes",
]


def read_file_safe(path, max_chars=4000):
    try:
        content = Path(path).read_text(encoding="utf-8")
        return content[:max_chars] if len(content) > max_chars else content
    except OSError:
        return ""


def memu_request(method, endpoint, data=None):
    """Make authenticated memU request. Self-healing: restart server if down."""
    import urllib.request

    url = f"{MEMU_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {MEMU_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            if method == "POST":
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode() if data else None,
                    headers=headers,
                    method="POST",
                )
            else:
                if data and "api_key" not in url:
                    url += f"?api_key={MEMU_KEY}"
                    for k, v in data.items():
                        url += f"&{k}={v}"
                req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=8) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == 0:
                # Self-heal: try restarting memU
                error_body = e.read().decode() if hasattr(e, "read") else ""
                print(f"[SELF-HEAL] memU request failed ({e}) {error_body}, attempting restart...")
                try:
                    subprocess.run(
                        ["bash", str(MEMU_SERVER / "start.sh")],
                        timeout=10,
                        capture_output=True,
                    )
                    import time

                    time.sleep(2)
                except Exception as restart_error:
                    print(f"[WARN] memU restart attempt failed: {restart_error}")
            else:
                print(f"[WARN] memU unavailable after restart attempt: {e}")
                return None


def memu_store(agent_name, key, content, category="reflection", tags=None):
    """Store an entry in memU with strict quality gates."""
    # Quality gate: reject short/empty content
    if not content or len(content.strip()) < 30:
        print(
            f"[MEMU] Rejected write: content too short ({len(content.strip() if content else '')} chars)"
        )
        return None

    # Quality gate: enforce structured key
    if ":" not in key:
        key = f"{category}:{agent_name}:{key}"

    # Use bridge endpoint (port 8711)
    return memu_request(
        "POST",
        "/api/v1/memu/store",
        {
            "key": key,
            "value": content,
            "agent": agent_name,
            "user_id": "michael",
            "session_id": f"{agent_name}-si-cycle",
            "category": category,
            "metadata": {
                "tags": tags or [agent_name, "self-improve"],
                "quality_gate": "strict",
            },
        },
    )


def memu_search(query, limit=5):
    """Search memU for relevant context."""
    return memu_request(
        "POST",
        "/api/v1/memu/semantic-search",
        {
            "query": query,
            "limit": limit,
        },
    )


def get_recent_memory(agent_name):
    """Get recent memory from files and memU."""
    content = ""

    # File-based memory (last 2 days)
    today = datetime.date.today()
    for delta in range(2):
        date = today - datetime.timedelta(days=delta)
        f = MEMORY_DIR / f"{date}.md"
        if f.exists():
            content += f"\n--- {date} ---\n" + read_file_safe(f, 600)

    # memU-based memory (recent entries for this agent)
    memu_result = memu_search(f"{agent_name} improvement lesson", limit=3)
    if memu_result and "results" in memu_result:
        content += "\n--- memU Recent Lessons ---\n"
        for entry in memu_result["results"][:3]:
            content += f"- [{entry.get('key', '')}] {entry.get('content', '')[:150]}\n"

    return content or "(no recent memory)"


def get_past_reflections(agent_name, max_entries=5):
    """Get past reflection outcomes for this agent to learn from."""
    if not REFLECT_LOG.exists():
        return "(no past reflections)"

    lines = REFLECT_LOG.read_text().split("\n")
    agent_sections = []
    current = None

    for line in lines:
        if line.startswith(f"## {agent_name.title()}"):
            current = line
        elif current and line.startswith("## "):
            agent_sections.append(current)
            current = None
        elif current:
            current += "\n" + line

    if current:
        agent_sections.append(current)

    # Return last N reflections
    return "\n".join(agent_sections[-max_entries:]) or "(no past reflections)"


def get_prompt_evolution():
    """Load the evolving prompt additions from past cycles."""
    if PROMPT_EVOLUTION_FILE.exists():
        try:
            data = json.loads(PROMPT_EVOLUTION_FILE.read_text())
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"version": 1, "additions": [], "banned_patterns": [], "meta_lessons": []}


def save_prompt_evolution(data):
    """Save updated prompt evolution data."""
    PROMPT_EVOLUTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_EVOLUTION_FILE.write_text(json.dumps(data, indent=2))


def run_health_checks():
    """Self-healing: check infrastructure and fix issues."""
    issues_found = []
    issues_fixed = []

    # 0. Executable templates audit (blocking gate)
    try:
        audit_result = subprocess.run(
            [
                sys.executable,
                str(
                    WORKSPACE
                    / "self_improvement"
                    / "scripts"
                    / "executable_templates_audit.py"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(WORKSPACE),
        )
        if audit_result.returncode != 0:
            issues_found.append(f"Template audit FAILED: {audit_result.stdout.strip()}")
        else:
            audit_data = json.loads(audit_result.stdout)
            for w in audit_data.get("warnings", []):
                issues_found.append(f"[advisory] {w}")
    except Exception as e:
        issues_found.append(f"Template audit error: {e}")

    # 0b. Pre-flight execution audit — verify HARD_GATE templates are wired
    pre_flight_audit_script = (
        WORKSPACE / "agents" / "templates" / "pre_flight_execution_audit.py"
    )
    if pre_flight_audit_script.exists():
        try:
            pf_result = subprocess.run(
                [sys.executable, str(pre_flight_audit_script)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(WORKSPACE),
            )
            if pf_result.returncode != 0:
                pf_data = (
                    json.loads(pf_result.stdout) if pf_result.stdout.strip() else {}
                )
                missing = pf_data.get("missing_wires", [])
                issues_found.append(
                    f"Pre-flight execution audit: {len(missing)} gates not wired: {missing}"
                )
            # Note: this is advisory, not blocking — the gates themselves
            # (executable_templates_audit etc.) run independently above
        except Exception as e:
            issues_found.append(f"Pre-flight execution audit error: {e}")

    # 0c. health_check_models gate — verify model gateway before generating improvements
    health_models_script = (
        WORKSPACE / "self_improvement" / "templates" / "health_check_models.py"
    )
    if health_models_script.exists():
        try:
            hm_result = subprocess.run(
                [sys.executable, str(health_models_script)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(WORKSPACE),
            )
            if hm_result.returncode != 0:
                issues_found.append(
                    f"Model health gate WARN: gateway may be down — {hm_result.stdout.strip()}"
                )
        except Exception as e:
            issues_found.append(f"Model health gate error: {e}")

    # 1. memU health
    health = memu_request("GET", "/api/v1/memu/health")
    if not health:
        issues_found.append("memU server down")
        try:
            subprocess.run(
                ["bash", str(MEMU_SERVER / "start.sh")], timeout=15, capture_output=True
            )
            import time

            time.sleep(3)
            health2 = memu_request("GET", "/api/v1/memu/health")
            if health2:
                issues_fixed.append("memU server restarted successfully")
            else:
                issues_found.append("memU restart failed — needs manual intervention")
        except Exception as e:
            issues_found.append(f"memU restart exception: {e}")

    # 2. Check workspace directories exist
    for d in [OUTPUTS_DIR, MEMORY_DIR, AGENTS_DIR]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            issues_fixed.append(f"Created missing directory: {d}")

    # 3. Check agent profiles exist
    for agent in AGENT_ROLES:
        profile = AGENTS_DIR / f"{agent}.md"
        if not profile.exists():
            profile.write_text(
                f"# {agent.title()} Agent Profile\n\n**Role:** {AGENT_ROLES[agent]}\n\n## Operating Defaults\n- Follow AGENTS.md protocol\n- Self-improve every cycle\n"
            )
            issues_fixed.append(f"Created missing profile: {agent}.md")

    return issues_found, issues_fixed


def build_reflect_prompt(
    agent_name,
    profile_content,
    recent_memory,
    todo_snippet,
    past_reflections,
    prompt_evolution,
    health_report,
    sonar_context="",
    ledger_context="",
):
    """Build the self-improving reflection prompt."""
    role = AGENT_ROLES.get(agent_name, "autonomous AI agent")
    focus_areas = random.sample(IMPROVEMENT_DIMENSIONS, 4)

    # Build evolved prompt additions
    evolved_additions = ""
    if prompt_evolution.get("additions"):
        last_additions = prompt_evolution["additions"][-5:]  # Last 5 prompt upgrades
        evolved_additions = "\n".join(f"- {a}" for a in last_additions)

    banned = ""
    if prompt_evolution.get("banned_patterns"):
        banned = "\n**AVOID these patterns (they failed before):**\n" + "\n".join(
            f"- {b}" for b in prompt_evolution["banned_patterns"][-5:]
        )

    meta_lessons = ""
    if prompt_evolution.get("meta_lessons"):
        meta_lessons = "\n**Meta-lessons from past reflections:**\n" + "\n".join(
            f"- {m}" for m in prompt_evolution["meta_lessons"][-5:]
        )

    return f"""You are **{agent_name.title()}**, an autonomous AI agent with this mission: {role}

## YOUR CURRENT PROFILE (this is what you're improving)
{profile_content}

## RECENT WORK & MEMORY (context for what needs improving)
{recent_memory}

## CURRENT TODO (team priorities)
{todo_snippet}

## YOUR PAST REFLECTIONS (learn from what worked and what didn't)
{past_reflections}

## INFRASTRUCTURE HEALTH
{health_report}
{sonar_context}
{ledger_context}
---

## SELF-IMPROVEMENT DIRECTIVE (Michael Fethe — standing order)

> "How would I build myself better than I am built now — for better performance, more intelligence, and better end-user experience with smarter, more capable applications of myself?"

**This hour, focus on these dimensions:**
1. {focus_areas[0]}
2. {focus_areas[1]}
3. {focus_areas[2]}
4. {focus_areas[3]}

{f"**Evolved prompt guidance (learned from past cycles):**" + chr(10) + evolved_additions if evolved_additions else ""}
{banned}
{meta_lessons}

## CRITICAL RULES

1. **Ship real changes.** Not plans. Not suggestions. Actual file modifications that make you measurably better.
2. **Be self-healing.** If infrastructure is broken, fix it as part of this cycle. Don't report it — repair it.
3. **Learn from past reflections.** Don't repeat improvements that already exist. Don't repeat failures. Build on what worked.
4. **Improve the prompt itself.** Include a `prompt_upgrade` field — one way to make THIS reflection prompt better for next time.
5. **Test your changes mentally.** Would this actually help in a real scenario? If not, pick something that would.
6. **No filler.** "Add better error handling" is filler. "Add try/except around the Schwab API call in trade_executor.py line 142 that crashes on weekend market-closed responses" is real.
7. **Cross-agent learning.** If you learned something another agent should know, include it in `cross_agent_broadcast`.

## OUTPUT FORMAT

Respond with ONLY valid JSON (no markdown fences, no commentary):

{{
  "reflection": "2-3 sentence honest assessment of your weakest area right now and why",
  "improvements": [
    {{
      "title": "specific descriptive title",
      "why": "concrete measurable reason this improves capability",
      "file": "relative/path/from/workspace",
      "action": "append|replace_section|create",
      "section_marker": "exact text to find for replace_section (omit for append/create)",
      "content": "exact content to write",
      "verification": "how to verify this change actually works"
    }}
  ],
  "self_healing_actions": [
    {{
      "issue": "what was broken",
      "fix": "what you did to fix it",
      "status": "fixed|attempted|needs_escalation"
    }}
  ],
  "lesson_captured": "one concrete, reusable lesson from this cycle",
  "cross_agent_broadcast": "one thing other agents should know (or null if nothing)",
  "prompt_upgrade": "one specific way to improve THIS reflection prompt for next cycle",
  "banned_pattern": "one pattern to STOP doing (or null if nothing to ban)",
  "pre_flight_audit": {{"memU_healthy": true, "workspace_dirs_ok": true, "api_reachable": true}},
  "score": {{"correctness": 0, "speed": 0, "risk": 0, "followthrough": 0, "self_healing": 0}}
}}

Score each dimension 0-2: 0=didn't address, 1=partially addressed, 2=fully addressed.
Add self_healing: 0=ignored broken things, 1=noticed but didn't fix, 2=found and fixed issues.
pre_flight_audit: report actual health check results. If any value is false, focus improvements on fixing infrastructure first.

Generate 1-2 improvements. Quality over quantity. Each must be a REAL, SPECIFIC change.
CRITICAL: Keep each improvement's "content" field under 500 characters. For code changes, describe WHAT to change, not the full replacement code. This prevents JSON truncation."""


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  UPDATED 2026-02-22 23:00 by Winnie — ROOT CAUSE FIX              ║
# ║  Lenny's max_tokens=2000 caused JSON truncation (4 consecutive     ║
# ║  parse failures). Restored to 4096 + retry/fallback chain.        ║
# ║  DO NOT reduce max_tokens below 3500 — model JSON output is ~3k.  ║
# ╚══════════════════════════════════════════════════════════════════════╝
def call_model(prompt, agent_name):
    """Call API with retry + cross-provider model fallback chain."""
    import urllib.request
    import time as _time
    import os
    import json

    models = ["claude-haiku-4-5", "claude-sonnet-4-6"]
    fallback_model = "gemini-2.5-flash"
    models.append(fallback_model)
    max_retries = 3
    last_error = None

    for model in models:
        for attempt in range(max_retries):
            try:
                if "gemini" in model:
                    gemini_key = os.environ.get("GEMINI_API_KEY")
                    if not gemini_key:
                        raise Exception("GEMINI_API_KEY missing")
                    req = urllib.request.Request(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                        data=json.dumps({
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 4096}
                        }).encode(),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        result = json.loads(resp.read())
                        text = result["candidates"][0]["content"]["parts"][0]["text"]
                        return text
                
                if not ANTHROPIC_KEY:
                    raise Exception("ANTHROPIC_API_KEY missing")

                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=json.dumps(
                        {
                            "model": model,
                            "max_tokens": 4096,
                            "temperature": 0.5,
                            "messages": [{"role": "user", "content": prompt}],
                        }
                    ).encode(),
                    headers={
                        "x-api-key": ANTHROPIC_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=45) as resp:
                    result = json.loads(resp.read())
                    text = result["content"][0]["text"]
                    if result.get("stop_reason") == "end_turn":
                        return text
                    print(
                        f"[WARN] {model} response truncated (stop_reason={result.get('stop_reason')})"
                    )
                    return text
            except Exception as e:
                last_error = e
                wait = 3 * (2**attempt)
                print(
                    f"[WARN] {model} attempt {attempt + 1} failed: {e}. Waiting {wait}s..."
                )
                _time.sleep(wait)
        print(f"[WARN] All retries exhausted for {model}, trying next...")

    return json.dumps(
        {
            "reflection": f"API failed after all retries: {last_error}",
            "improvements": [],
            "self_healing_actions": [],
            "lesson_captured": f"API error across all models: {last_error}",
            "cross_agent_broadcast": None,
            "prompt_upgrade": None,
            "banned_pattern": None,
            "score": {
                "correctness": 0,
                "speed": 0,
                "risk": 0,
                "followthrough": 0,
                "self_healing": 0,
            },
        }
    )


def extract_json(text):
    """Extract JSON from model response, handling markdown fences and edge cases."""
    if not text:
        return None

    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON object by brace matching
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError as e:
                    # Try cleaning common issues
                    cleaned = text[start : i + 1]
                    # Fix trailing commas
                    cleaned = re.sub(r",\s*}", "}", cleaned)
                    cleaned = re.sub(r",\s*]", "]", cleaned)
                    try:
                        return json.loads(cleaned)
                    except:
                        print(f"[WARN] JSON parse failed: {e}")
                        # Save raw for debugging
                        debug_file = (
                            OUTPUTS_DIR
                            / f"debug-json-{datetime.datetime.now().strftime('%H%M%S')}.txt"
                        )
                        debug_file.write_text(text[start : i + 1])
                        return None
    return None


def apply_improvements(agent_name, improvements):
    """Apply each improvement to the target file."""
    applied = []
    failed = []

    for imp in improvements:
        file_path = WORKSPACE / imp.get("file", "")
        action = imp.get("action", "append")
        content = imp.get("content", "")

        if not content or not imp.get("file"):
            failed.append(f"SKIP (no file/content): {imp.get('title', '?')}")
            continue

        # Safety: don't modify critical system files
        file_str = str(file_path)
        if any(
            bad in file_str
            for bad in ["/etc/", "/usr/", ".ssh/", "openclaw.json", "jobs.json"]
        ):
            failed.append(
                f"BLOCKED (safety): {imp.get('title', '?')} — can't modify {imp.get('file')}"
            )
            continue
        # Extra caution for self-modification: only allow append, not replace/create
        if "hourly_self_reflect.py" in file_str and imp.get("action") != "append":
            failed.append(
                f"BLOCKED (safety): {imp.get('title', '?')} — only append allowed for hourly_self_reflect.py"
            )
            continue

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if action == "create":
                if file_path.exists():
                    # Don't overwrite existing files — append instead
                    existing = file_path.read_text()
                    if content.strip()[:80] not in existing:
                        with open(file_path, "a") as f:
                            f.write(f"\n{content}\n")
                        applied.append(
                            f"APPENDED (file existed) {imp['file']}: {imp['title']}"
                        )
                    else:
                        applied.append(
                            f"SKIP (content exists) {imp['file']}: {imp['title']}"
                        )
                else:
                    file_path.write_text(content)
                    applied.append(f"CREATED {imp['file']}: {imp['title']}")

            elif action == "append":
                existing = file_path.read_text() if file_path.exists() else ""
                # Dedup check: don't append if first 80 chars already present
                content_hash = hashlib.md5(content.strip()[:80].encode()).hexdigest()[
                    :8
                ]
                if content.strip()[:80] in existing:
                    applied.append(
                        f"SKIP (already present) {imp['file']}: {imp['title']}"
                    )
                else:
                    with open(file_path, "a") as f:
                        f.write(f"\n{content}\n")
                    applied.append(f"APPENDED {imp['file']}: {imp['title']}")

            elif action == "replace_section":
                marker = imp.get("section_marker", "")
                if marker and file_path.exists():
                    existing = file_path.read_text()
                    if marker in existing:
                        # Replace from marker to next ## heading or end
                        pattern = re.escape(marker) + r".*?(?=\n## |\Z)"
                        new = re.sub(
                            pattern, content, existing, count=1, flags=re.DOTALL
                        )
                        if new != existing:
                            file_path.write_text(new)
                            applied.append(
                                f"REPLACED section in {imp['file']}: {imp['title']}"
                            )
                        else:
                            applied.append(
                                f"SKIP (no change after replace) {imp['file']}: {imp['title']}"
                            )
                    else:
                        with open(file_path, "a") as f:
                            f.write(f"\n{content}\n")
                        applied.append(
                            f"APPENDED (marker not found) {imp['file']}: {imp['title']}"
                        )
                else:
                    with open(file_path, "a") as f:
                        f.write(f"\n{content}\n")
                    applied.append(f"APPENDED {imp['file']}: {imp['title']}")

        except Exception as e:
            failed.append(f"FAILED {imp.get('file', '?')}: {str(e)}")

    return applied, failed


def store_in_memu(agent_name, result_data, applied, failed):
    """Store reflection results in memU with strict quality gates.
    Only stores substantive content. Publishes to NATS for cross-agent awareness.
    """
    now = datetime.datetime.now()
    key = f"reflection:{agent_name}:{now.strftime('%Y%m%d-%H%M')}"

    reflection = result_data.get("reflection", "")
    lesson = result_data.get("lesson_captured", "")

    content_parts = [
        f"Agent: {agent_name}",
        f"Reflection: {reflection}",
        f"Improvements applied: {len(applied)}",
    ]
    if applied:
        content_parts.append(f"Changes: {'; '.join(applied[:5])}")
    if lesson:
        content_parts.append(f"Lesson: {lesson}")
    if result_data.get("cross_agent_broadcast"):
        content_parts.append(f"Broadcast: {result_data['cross_agent_broadcast']}")

    content = "\n".join(content_parts)

    # Strict gate: only store if substantive
    if len(content) >= 30 and (len(applied) > 0 or len(lesson) > 20):
        tags = [agent_name, "self-improve", "reflection"]
        if result_data.get("self_healing_actions"):
            tags.append("self-healing")
        memu_store(agent_name, key, content, "lesson", tags)

    # Broadcast as shared knowledge (stricter)
    broadcast = result_data.get("cross_agent_broadcast")
    if broadcast and len(broadcast) >= 30:
        memu_store(
            agent_name,
            f"lesson:{agent_name}:{now.strftime('%Y%m%d-%H%M')}:broadcast",
            broadcast,
            "lesson",
            [agent_name, "broadcast", "cross-agent"],
        )

    # Publish to NATS for real-time cross-agent awareness
    if lesson and len(lesson) >= 20:
        _nats_call("broadcast", agent_name, f"lesson:{lesson[:200]}")


def _run_prompt_optimizer(prompt_upgrade, model_key="claude"):
    """Run the prompt optimizer on a prompt_upgrade suggestion. Returns optimized text or original."""
    try:
        optimizer = Path.home() / ".openclaw" / "skills" / "prompt-optimizer" / "scripts" / "optimize_prompt.py"
        if not optimizer.exists():
            return prompt_upgrade
        result = subprocess.run(
            ["python3", str(optimizer), "--model", model_key, "--no-sonar", "--json", prompt_upgrade],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            issues = data.get("issues", [])
            if issues:
                print(f"[PROMPT-OPT] Found {len(issues)} issues in prompt_upgrade, logging")
                log_event("PROMPT_EVOLVED", "system", {"issues": issues, "model": model_key})
        return prompt_upgrade  # Return original for now; optimizer provides advisory
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return prompt_upgrade


def evolve_prompt(result_data, prompt_evolution):
    """Apply prompt self-improvement from this cycle's output."""
    if result_data.get("prompt_upgrade") and result_data["prompt_upgrade"] != "null":
        # Run through prompt optimizer for model-specific best practice checks
        optimized = _run_prompt_optimizer(result_data["prompt_upgrade"])
        prompt_evolution.setdefault("additions", []).append(
            optimized
        )
        # Keep last 10 additions
        prompt_evolution["additions"] = prompt_evolution["additions"][-10:]

    if result_data.get("banned_pattern") and result_data["banned_pattern"] != "null":
        prompt_evolution.setdefault("banned_patterns", []).append(
            result_data["banned_pattern"]
        )
        prompt_evolution["banned_patterns"] = prompt_evolution["banned_patterns"][-10:]

    if result_data.get("lesson_captured"):
        prompt_evolution.setdefault("meta_lessons", []).append(
            result_data["lesson_captured"]
        )
        prompt_evolution["meta_lessons"] = prompt_evolution["meta_lessons"][-15:]

    prompt_evolution["version"] = prompt_evolution.get("version", 0) + 1
    prompt_evolution["last_updated"] = datetime.datetime.now().isoformat()

    save_prompt_evolution(prompt_evolution)


def write_reflection_log(agent_name, result_data, applied, failed):
    """Write reflection output to files."""
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # Per-cycle output file
    output_file = (
        OUTPUTS_DIR / f"{date_str}-{now.strftime('%H')}-{agent_name}-reflect.md"
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    improvements = result_data.get("improvements", [])
    score = result_data.get("score", {})
    healing = result_data.get("self_healing_actions", [])

    content = f"""# Self-Improvement Reflection — {agent_name.title()} — {date_str} {time_str}

## Reflection
{result_data.get("reflection", "(none)")}

## Improvements ({len(improvements)} generated, {len(applied)} applied, {len(failed)} failed)
"""
    for i, imp in enumerate(improvements, 1):
        content += f"""
### {i}. {imp.get("title", "Untitled")}
- **Why:** {imp.get("why", "")}
- **Target:** `{imp.get("file", "?")}` ({imp.get("action", "?")})
- **Verification:** {imp.get("verification", "none specified")}
"""

    if healing:
        content += f"\n## Self-Healing Actions\n"
        for h in healing:
            content += f"- [{h.get('status', '?')}] {h.get('issue', '?')} → {h.get('fix', '?')}\n"

    content += f"""
## Applied
{chr(10).join("- " + a for a in applied) or "(none)"}

## Failed
{chr(10).join("- " + f for f in failed) or "(none)"}

## Lesson: {result_data.get("lesson_captured", "(none)")}
## Cross-Agent Broadcast: {result_data.get("cross_agent_broadcast", "(none)")}
## Prompt Upgrade: {result_data.get("prompt_upgrade", "(none)")}

## Score
{json.dumps(score, indent=2)}
"""

    output_file.write_text(content)

    # Append to rolling reflect log
    REFLECT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(REFLECT_LOG, "a") as f:
        f.write(f"\n## {agent_name.title()} — {date_str} {time_str}\n")
        f.write(
            f"- Improvements: {len(improvements)} generated, {len(applied)} applied, {len(failed)} failed\n"
        )
        f.write(f"- Lesson: {result_data.get('lesson_captured', '(none)')}\n")
        f.write(f"- Score: {score}\n")
        if result_data.get("cross_agent_broadcast"):
            f.write(f"- Broadcast: {result_data['cross_agent_broadcast']}\n")

    return output_file


def update_changelog(agent_name, improvements, applied):
    """Append summary to CHANGELOG.md."""
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M")

    CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    titles = [imp.get("title", "?") for imp in improvements]

    with open(CHANGELOG, "a") as f:
        f.write(f"\n## {date_str} — {agent_name.title()} Self-Improvement v2\n")
        f.write(f"- Applied: {len(applied)}/{len(improvements)}\n")
        for t in titles:
            f.write(f"  - {t}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: hourly_self_reflect.py <agent_name>")
        sys.exit(1)

    agent_name = sys.argv[1].lower()
    if agent_name not in AGENT_ROLES:
        print(f"Unknown agent: {agent_name}. Valid: {list(AGENT_ROLES.keys())}")
        sys.exit(1)

    print(f"[{agent_name.upper()}] Self-improvement v2 starting...")

    # 0. NATS heartbeat + structured event log
    log_event("CYCLE_START", agent_name, {"version": "2.1"})
    _nats_call("heartbeat", agent_name, "cycle_starting")

    # 1. Self-healing health check FIRST
    print(f"[{agent_name.upper()}] Running health checks...")
    health_issues, health_fixes = run_health_checks()
    health_report = ""
    if health_fixes:
        health_report += "**Self-healed this cycle:**\n" + "\n".join(
            f"- ✅ {f}" for f in health_fixes
        )
    if health_issues:
        health_report += "\n**Outstanding issues (fix these):**\n" + "\n".join(
            f"- ⚠️ {i}" for i in health_issues
        )
    if not health_report:
        health_report = "All systems healthy."

    # 1b. Sonar research — gather external intel to inform this cycle
    sonar_context = ""
    research_topics = {
        "rosie": "multi-agent AI orchestration self-improvement systems latest techniques 2026",
        "mack": "AI coding agent automation infrastructure reliability best practices 2026",
        "winnie": "AI agent testing quality assurance monitoring tools 2026",
        "lenny": "AI system resilience self-healing observability patterns 2026",
    }
    research_query = research_topics.get(agent_name, "AI agent self-improvement techniques 2026")
    print(f"[{agent_name.upper()}] Sonar research: {research_query[:60]}...")
    sonar_result = _sonar_research(research_query, model="pro")
    if sonar_result:
        sonar_context = f"\n## EXTERNAL RESEARCH (Sonar Pro — latest web intel)\n{sonar_result}\n"
        print(f"[{agent_name.upper()}] Sonar returned {len(sonar_result)} chars of research context")
        log_event("SONAR_RESEARCH", agent_name, {"chars": len(sonar_result), "query": research_query[:80]})
    else:
        print(f"[{agent_name.upper()}] Sonar unavailable, continuing without external research")

    # 1c. Load ledger context for dual-loop orchestration
    task_ledger = get_task_ledger()
    agent_progress = get_agent_status(agent_name)
    ledger_context = ""
    if task_ledger.get("facts"):
        recent_facts = task_ledger["facts"][-5:]
        ledger_context += "\n## TASK LEDGER (verified facts)\n" + "\n".join(f"- {f['fact']}" for f in recent_facts)
    if agent_progress.get("active"):
        ledger_context += f"\n## YOUR ASSIGNED TASKS ({len(agent_progress['active'])} active)\n"
        for t in agent_progress["active"]:
            ledger_context += f"- [{t['task_id']}] {t['description']}\n"

    # 2. Gather context
    profile_content = read_file_safe(AGENTS_DIR / f"{agent_name}.md", 1500)
    recent_memory = get_recent_memory(agent_name)
    todo_snippet = read_file_safe(SI_DIR / "TODO.md", 800)
    past_reflections = get_past_reflections(agent_name, max_entries=2)
    prompt_evolution = get_prompt_evolution()

    # 3. Build and send prompt
    prompt = build_reflect_prompt(
        agent_name,
        profile_content,
        recent_memory,
        todo_snippet,
        past_reflections,
        prompt_evolution,
        health_report,
        sonar_context,
        ledger_context,
    )

    print(
        f"[{agent_name.upper()}] Calling model (prompt v{prompt_evolution.get('version', 1)})..."
    )
    raw_response = call_model(prompt, agent_name)

    def validate_schema(data):
        if not isinstance(data, dict): return False
        required = {"reflection": str, "improvements": list, "score": dict}
        for k, t in required.items():
            if k not in data or not isinstance(data[k], t): return False
        for imp in data.get("improvements", []):
            if not isinstance(imp, dict): return False
            for req_imp in ["title", "file", "action", "content"]:
                if req_imp not in imp: return False
        return True

    # 4. Parse response
    result_data = extract_json(raw_response)
    
    # Pilot JSON schema validation
    if result_data and not validate_schema(result_data):
        print(f"[{agent_name.upper()}] JSON schema validation failed")
        result_data = None

    if not result_data:
        print(
            f"[{agent_name.upper()}] JSON parse or schema validation failed — saving raw response for debug"
        )
        debug_file = (
            OUTPUTS_DIR
            / f"debug-raw-{agent_name}-{datetime.datetime.now().strftime('%H%M%S')}.txt"
        )
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        debug_file.write_text(raw_response or "(empty)")

        # Try one more time with a repair prompt
        repair_prompt = f"The following text should be valid JSON but isn't. Extract and fix it into valid JSON. Return ONLY the fixed JSON:\n\n{raw_response[:2000]}"
        repair_response = call_model(repair_prompt, agent_name)
        result_data = extract_json(repair_response)

        if result_data and not validate_schema(result_data):
            print(f"[{agent_name.upper()}] Repair pass JSON schema validation failed")
            result_data = None

        if not result_data:
            result_data = {
                "reflection": "JSON parse failed even after repair attempt",
                "improvements": [],
                "self_healing_actions": [],
                "lesson_captured": "Model returned unparseable response — repair pass failed; raw response saved for debugging",
                "cross_agent_broadcast": None,
                "prompt_upgrade": "Add explicit instruction: 'Output ONLY raw JSON with no markdown fences or surrounding text'",
                "banned_pattern": None,
                "score": {
                    "correctness": 0,
                    "speed": 1,
                    "risk": 2,
                    "followthrough": 0,
                    "self_healing": 0,
                },
            }

    # 4b. Pre-flight audit gate: if model reports infra unhealthy, skip improvements
    pre_flight = result_data.get("pre_flight_audit", {})
    blocking_keys = ["memU_healthy", "workspace_dirs_ok", "api_reachable"]
    infra_ok = all(pre_flight.get(k, True) for k in blocking_keys)
    if pre_flight and not infra_ok:
        failed_checks = [k for k in blocking_keys if not pre_flight.get(k, True)]
        advisory_checks = [
            k for k, v in pre_flight.items() if not v and k not in blocking_keys
        ]
        print(
            f"[{agent_name.upper()}] PRE-FLIGHT FAILED: {failed_checks} — blocking improvements, forcing self-heal"
        )
        if advisory_checks:
            print(
                f"[{agent_name.upper()}] PRE-FLIGHT advisory (non-blocking): {advisory_checks}"
            )
        result_data["improvements"] = []
        if not result_data.get("self_healing_actions"):
            result_data["self_healing_actions"] = [
                {
                    "issue": f"Pre-flight failed: {failed_checks}",
                    "fix": "Deferred to next cycle",
                    "status": "needs_escalation",
                }
            ]

    # 4c. Quality check tier (LobeHub /loop style)
    scores = result_data.get("score", {})
    total_score = 0
    if isinstance(scores, dict):
        for k, v in scores.items():
            if isinstance(v, (int, float)):
                total_score += v
                
    # 5. Apply improvements
    improvements = result_data.get("improvements", [])
    if total_score < 6 and len(improvements) > 0:
        print(f"[{agent_name.upper()}] QUALITY CHECK FAILED: Score {total_score}/10 is below threshold 6. Rejecting improvements.")
        applied = []
        failed = [f"REJECTED (Quality Check): Score {total_score} too low. Needed >= 6. Scores: {scores}"]
        # Clear improvements so they aren't written to changelog as "applied: 0/x" in a confusing way
    else:
        if len(improvements) > 0:
            print(f"[{agent_name.upper()}] QUALITY CHECK PASSED: Score {total_score}/10.")
        print(f"[{agent_name.upper()}] Applying {len(improvements)} improvements...")
        applied, failed = apply_improvements(agent_name, improvements)

    # 6. Store in memU
    store_in_memu(agent_name, result_data, applied, failed)

    # 7. Evolve the prompt for next cycle
    evolve_prompt(result_data, prompt_evolution)

    # 8. Write logs
    output_file = write_reflection_log(agent_name, result_data, applied, failed)
    update_changelog(agent_name, improvements, applied)

    # 9. Summary
    print(
        f"[{agent_name.upper()}] Done (prompt v{prompt_evolution.get('version', 1)})."
    )
    print(f"  Applied: {len(applied)}, Failed: {len(failed)}")
    print(f"  Output: {output_file}")
    print(f"  Lesson: {result_data.get('lesson_captured', '(none)')}")

    if health_fixes:
        print(f"  Self-healed: {len(health_fixes)} issues")

    if applied:
        for a in applied:
            print(f"  + {a}")
    if failed:
        for f in failed:
            print(f"  ! {f}")

    # 10. NATS — broadcast results and heartbeat cycle complete
    _nats_call("heartbeat", agent_name, "cycle_complete")
    lesson = result_data.get("lesson_captured", "")
    if lesson and len(applied) > 0:
        _nats_call(
            "broadcast",
            agent_name,
            f"[{agent_name}] {len(applied)} improvements applied. Lesson: {lesson[:150]}",
        )
    broadcast_msg = result_data.get("cross_agent_broadcast")
    if broadcast_msg:
        _nats_call("broadcast", agent_name, f"[{agent_name}] {broadcast_msg[:200]}")

    # 11. Memory Learning Engine — POST session summary to /extract for cross-gateway storage
    _post_to_memory_learning_engine(agent_name, result_data, applied)

    # 12. Update task ledger with cycle results
    if applied:
        for a in applied:
            add_fact(f"[{agent_name}] Applied: {str(a)[:100]}", source=f"cycle-{agent_name}")

    # 13. Final structured event log
    log_event("CYCLE_COMPLETE", agent_name, {
        "applied": len(applied), "failed": len(failed),
        "healed": len(health_fixes), "sonar": bool(sonar_context),
        "prompt_version": prompt_evolution.get("version", 1),
    })

    return 0


def _post_to_memory_learning_engine(agent_name, result_data, applied):
    """POST session summary to Memory Learning Engine for cross-gateway extraction + storage.
    Service: http://michaels-mac-mini.tailf243d5.ts.net:8765
    Fire-and-forget — never blocks the cycle.
    """
    import urllib.request as _req
    import json as _json

    MLE_URL = "http://michaels-mac-mini.tailf243d5.ts.net:8765/extract"

    reflection = result_data.get("reflection", "")
    lesson = result_data.get("lesson_captured", "")
    broadcast = result_data.get("cross_agent_broadcast", "")

    parts = []
    if reflection and len(reflection) > 20:
        parts.append(f"Reflection: {reflection[:300]}")
    if lesson and len(lesson) > 20:
        parts.append(f"Learned that {lesson[:300]}")
    if applied:
        parts.append(f"Fixed/resolved: {'; '.join(applied[:5])}")
    if broadcast and len(broadcast) > 20:
        parts.append(f"Key insight: {broadcast[:200]}")

    if not parts:
        return  # nothing substantive to extract

    summary = " ".join(parts)

    payload = _json.dumps({"text": summary, "agent": agent_name}).encode()

    # Retry transient network/server failures to reduce dropped learning events.
    # Keep bounded + non-blocking for the main cycle.
    backoff_s = [1, 2, 4]
    for attempt, wait_s in enumerate(backoff_s, start=1):
        try:
            req = _req.Request(
                MLE_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _req.urlopen(req, timeout=5) as resp:
                result = _json.loads(resp.read().decode())
                stored = result.get("stored_count", 0)
                extracted = result.get("raw_count", 0)
                print(
                    f"[MLE] Extracted {extracted} memories, stored {stored} new for {agent_name}"
                )
                return
        except Exception as e:
            is_last = attempt == len(backoff_s)
            if is_last:
                print(
                    f"[MLE] Fire-and-forget failed after {attempt} attempts (non-blocking): {e}"
                )
                return
            print(
                f"[MLE] Attempt {attempt}/{len(backoff_s)} failed: {e}; retrying in {wait_s}s"
            )
            import time as _time

            _time.sleep(wait_s)


if __name__ == "__main__":
    sys.exit(main())
