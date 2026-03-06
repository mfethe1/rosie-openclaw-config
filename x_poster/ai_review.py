#!/usr/bin/env python3
"""
AI Post Reviewer — improves X posts before they go out.
Uses Anthropic API to rewrite/improve each post for max engagement.
Also scores and stores quality feedback for continuous improvement.
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
REVIEW_LOG = BASE_DIR / "review_log.jsonl"
IMPROVEMENT_NOTES = BASE_DIR / "improvement_notes.md"

def load_env():
    env_file = Path.home() / ".openclaw/secrets/x-twitter.env"
    deploy_env = Path.home() / ".openclaw/secrets/deploy.env"
    for f in [env_file, deploy_env]:
        if f.exists():
            with open(f) as fh:
                for line in fh:
                    line = line.strip().lstrip("export ")
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ[k] = v.strip('"')

def improve_post(original_text: str, brand_context: str = "") -> dict:
    """Send post to Claude for improvement before publishing."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"improved": original_text, "score": 5, "reasoning": "No API key — using original"}

    prompt = f"""You are a senior social media strategist for Protelynx, a B2B AI SaaS company.
Active product to promote: IssuesFlow (issuesflow.ai).
Do NOT mention JiraFlow, Content Flow, ContentPilot, jiraflow.io, or contentpilot.ai.
Brand voice: Bold, direct, data-backed, founder-led. No fluff.

Review this X (Twitter) post and improve it for maximum engagement:

ORIGINAL POST:
{original_text}

{f"ADDITIONAL CONTEXT: {brand_context}" if brand_context else ""}

Return a JSON object with:
{{
  "improved_text": "rewritten post (keep under 280 chars if possible, max 500)",
  "engagement_score": <1-10 score for expected engagement>,
  "original_score": <1-10 score for original>,
  "changes_made": ["list", "of", "key changes"],
  "reasoning": "brief explanation of improvements",
  "cta_strength": <1-10>,
  "hook_strength": <1-10>
}}

Rules:
- Keep hashtags (3-5 max, relevant ones only)
- Preserve the core message and any URLs
- Make the hook (first line) punchier
- Use concrete numbers/specifics where possible
- Avoid corporate jargon
- Enforce product policy: only IssuesFlow/Issuesflow.ai may be promoted"""

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-haiku-4-5",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=30
    )

    if resp.status_code != 200:
        print(f"⚠️  AI review failed ({resp.status_code}) — using original")
        return {"improved": original_text, "score": 5, "reasoning": f"API error {resp.status_code}"}

    content = resp.json()["content"][0]["text"]

    # Parse JSON from response
    import re
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "improved": data.get("improved_text", original_text),
                "score": data.get("engagement_score", 5),
                "original_score": data.get("original_score", 5),
                "changes": data.get("changes_made", []),
                "reasoning": data.get("reasoning", ""),
                "cta_strength": data.get("cta_strength", 5),
                "hook_strength": data.get("hook_strength", 5),
            }
        except json.JSONDecodeError:
            pass

    return {"improved": original_text, "score": 5, "reasoning": "Parse error — using original"}

def log_review(original: str, result: dict, posted_text: str):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "original": original[:200],
        "posted": posted_text[:200],
        "engagement_score": result.get("score"),
        "original_score": result.get("original_score"),
        "changes": result.get("changes", []),
        "reasoning": result.get("reasoning", ""),
        "hook_strength": result.get("hook_strength"),
        "cta_strength": result.get("cta_strength"),
    }
    with open(REVIEW_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

def update_improvement_notes(entry: dict):
    """Append insights to the running improvement notes file."""
    ts = entry["ts"][:10]
    changes = "\n".join(f"  - {c}" for c in entry.get("changes", []))
    note = f"""
## {ts} — Score {entry.get('original_score', '?')} → {entry.get('engagement_score', '?')}
**Reasoning:** {entry.get('reasoning', '')}
**Hook strength:** {entry.get('hook_strength', '?')}/10 | **CTA:** {entry.get('cta_strength', '?')}/10
**Changes:**
{changes if changes else '  - No changes needed'}
"""
    with open(IMPROVEMENT_NOTES, "a") as f:
        f.write(note)

def main():
    """Main: read post text from stdin or arg, return improved version."""
    load_env()

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("ERROR: No post text provided", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Reviewing post ({len(text)} chars)...")
    result = improve_post(text)
    improved = result["improved"]

    # Log it
    entry = log_review(text, result, improved)
    update_improvement_notes(entry)

    print(f"📊 Score: {result.get('original_score', '?')} → {result.get('score', '?')}/10")
    if result.get("changes"):
        print(f"✏️  Changes: {', '.join(result['changes'])}")
    print(f"\n--- IMPROVED POST ---\n{improved}\n---")

    # Write improved text to stdout for pipeline
    return improved

if __name__ == "__main__":
    improved = main()
    # Also write just the final text to a temp file for the poster to pick up
    tmp = Path("/tmp/x_next_post.txt")
    tmp.write_text(improved)
