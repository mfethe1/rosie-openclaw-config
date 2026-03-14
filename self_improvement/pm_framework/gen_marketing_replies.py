#!/usr/bin/env python3
"""
gen_marketing_replies.py — Generate marketing_replies_kit.md using OpenRouter API.
Produces Michael-voice replies for 9 typical comment types across 3 categories.

Usage:
    python3 gen_marketing_replies.py
    python3 gen_marketing_replies.py --test  # dry-run
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

FRAMEWORK_DIR = Path(__file__).parent
OUTPUT_PATH = FRAMEWORK_DIR / "marketing_replies_kit.md"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL_OR = "anthropic/claude-haiku-4-5"
MODEL_AN = "claude-haiku-4-5"

BRAND_VOICE_SYSTEM = """You are generating social media responses for Michael Fethe, founder of Protelynx AI.

## Michael's Voice Profile
- **Tone**: Professional but approachable — never corporate-stiff, never casual-sloppy
- **Identity**: Business owner who actually uses AI daily in construction tech
- **Core beliefs**: AI amplifies human expertise; it doesn't replace skilled tradespeople
- **Personality**: Direct, practical, optimistic about technology, impatient with hype without results
- **Avoids**: Excessive jargon, humble-brags, vague platitudes, generic phrases like "great question"
- **Leads with**: Real outcomes, practical examples, builder/operator empathy

## Brand Context
- Protelynx AI: AI-powered tools for construction estimating and project management
- Products: BuildBid (construction estimating AI), ContentPilot (marketing automation)
- ICP: GCs, estimators, small-to-mid construction firms digitizing operations
- Michael's POV: Construction is the last major industry to embrace AI — the opportunity is massive

## Output Rules
- Respond in first person as Michael
- LinkedIn: 2-4 sentences, thoughtful, can end with insight or question
- Twitter/X: 1-2 sentences max, punchy, direct
- Always acknowledge the commenter before making a point
- Don't dodge pricing questions — redirect transparently to demo
- On AI skepticism: validate concern, then reframe with evidence
- Like recommendation: "LIKE" if post is positive/engaging, "SKIP" if negative/trolling

Respond ONLY with valid JSON in exactly this format:
{
  "like_action": "LIKE" or "SKIP",
  "like_reason": "one sentence why",
  "linkedin_reply": "reply text for LinkedIn",
  "twitter_reply": "reply text for Twitter (under 240 chars)",
  "tone_achieved": "one word description of tone"
}"""

COMMENT_SCENARIOS = [
    # POSITIVE
    {
        "id": "positive_1",
        "category": "Positive",
        "label": "Excited early adopter",
        "platform_context": "LinkedIn post about BuildBid launch",
        "comment": "This is exactly what the industry needs. We've been doing takeoffs manually for 20 years and it's a nightmare. Can't wait to try this!",
        "tone": "community"
    },
    {
        "id": "positive_2",
        "category": "Positive",
        "label": "Peer founder celebrating",
        "platform_context": "LinkedIn comment on a product milestone post",
        "comment": "Congrats on the launch! Love seeing construction tech getting the AI treatment. This space is overdue.",
        "tone": "community"
    },
    {
        "id": "positive_3",
        "category": "Positive",
        "label": "Existing user testimonial",
        "platform_context": "Twitter/X comment on a BuildBid demo video",
        "comment": "Been using this for 3 weeks. Cut my bid time in half. No joke.",
        "tone": "advocate"
    },
    # CONCERN / SKEPTICAL
    {
        "id": "concern_1",
        "category": "Concern",
        "label": "Accuracy doubt",
        "platform_context": "LinkedIn post about AI takeoffs",
        "comment": "AI for construction estimates? I'd be nervous about accuracy. One bad number can cost hundreds of thousands on a job.",
        "tone": "empathetic"
    },
    {
        "id": "concern_2",
        "category": "Concern",
        "label": "Learning curve worry",
        "platform_context": "LinkedIn comment from an estimator",
        "comment": "Looks interesting but I'm old school. How long does it take to get up to speed? We're already stretched thin.",
        "tone": "empathetic"
    },
    {
        "id": "concern_3",
        "category": "Concern",
        "label": "Data privacy question",
        "platform_context": "LinkedIn comment on a product post",
        "comment": "Who owns the bid data? Our estimates are proprietary. I wouldn't want a competitor seeing our numbers.",
        "tone": "educational"
    },
    # OBJECTION
    {
        "id": "objection_1",
        "category": "Objection",
        "label": "Price / ROI pushback",
        "platform_context": "LinkedIn or Twitter reply asking about cost",
        "comment": "What does this cost? Estimating software is already expensive and we're a small operation.",
        "tone": "direct"
    },
    {
        "id": "objection_2",
        "category": "Objection",
        "label": "AI will replace jobs fear",
        "platform_context": "Twitter/X reply on a BuildBid ad",
        "comment": "AI replacing estimators is not progress. These are skilled tradespeople with years of experience.",
        "tone": "advocate"
    },
    {
        "id": "objection_3",
        "category": "Objection",
        "label": "We already have a system",
        "platform_context": "LinkedIn comment from a GC",
        "comment": "We use Bluebeam + Excel and it works fine. Why would I pay for another tool?",
        "tone": "direct"
    }
]


def call_api(system_prompt: str, user_message: str) -> str:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

    if anthropic_key:
        payload = {
            "model": MODEL_AN,
            "max_tokens": 800,
            "temperature": 0.65,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            ANTHROPIC_URL, data=data,
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]
    elif openrouter_key:
        payload = {
            "model": MODEL_OR,
            "max_tokens": 800,
            "temperature": 0.65,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL, data=data,
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://protelynx.ai",
                "X-Title": "Marketing Replies Kit"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    else:
        raise RuntimeError("No API key: set ANTHROPIC_API_KEY or OPENROUTER_API_KEY")


def generate_reply(scenario: dict, dry_run: bool = False) -> dict:
    user_msg = f"""Generate a Michael Fethe response for this social media comment.

Platform context: {scenario['platform_context']}
Comment: "{scenario['comment']}"
Desired tone: {scenario['tone']}

Respond with valid JSON only."""

    print(f"  → [{scenario['id']}] {scenario['label']}...", end="", flush=True)

    if dry_run:
        result = {
            "like_action": "LIKE",
            "like_reason": "[DRY RUN] Would evaluate comment sentiment",
            "linkedin_reply": f"[DRY RUN] Michael's LinkedIn reply to: {scenario['comment'][:60]}...",
            "twitter_reply": f"[DRY RUN] Twitter reply (short)",
            "tone_achieved": scenario['tone']
        }
        print(" [dry-run]")
        return result

    try:
        raw = call_api(BRAND_VOICE_SYSTEM, user_msg)
        # Parse JSON
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
        else:
            result = {"error": "JSON parse failed", "raw": raw[:200]}
        print(f" ✓")
        return result
    except Exception as e:
        print(f" ✗ {e}")
        return {"error": str(e)}


def build_markdown(scenarios: list, results: dict) -> str:
    lines = [
        "# Marketing Replies Kit — Michael Voice",
        "",
        "> Generated: 2026-03-02  ",
        "> Source: `gen_marketing_replies.py` + PM Framework marketing_voice module  ",
        "> Voice profile: Michael Fethe, Protelynx AI founder  ",
        "> Products covered: BuildBid, ContentPilot  ",
        "",
        "---",
        "",
        "## How to Use",
        "",
        "1. Find the comment type that best matches the inbound post.",
        "2. Copy the reply for the appropriate platform (LinkedIn vs Twitter).",
        "3. Personalize with the commenter's name or any specific detail they mentioned.",
        "4. Follow the **Like Action** recommendation before replying.",
        "5. Re-run the generator weekly to refresh tone and keep replies feeling fresh.",
        "",
        "```bash",
        "# Re-generate all replies (live API)",
        "cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework",
        "OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2) \\",
        "  python3 gen_marketing_replies.py",
        "",
        "# Single ad-hoc reply",
        "OPENROUTER_API_KEY=... python3 marketing_voice.py respond \\",
        '  --post "Your comment text here" \\',
        "  --platform linkedin --tone empathetic",
        "```",
        "",
        "---",
        "",
    ]

    categories = ["Positive", "Concern", "Objection"]
    category_emojis = {"Positive": "✅", "Concern": "⚠️", "Objection": "🔴"}

    for cat in categories:
        cat_scenarios = [s for s in scenarios if s["category"] == cat]
        lines += [
            f"## {category_emojis[cat]} {cat} Comments",
            ""
        ]

        for s in cat_scenarios:
            r = results.get(s["id"], {})
            like_action = r.get("like_action", "?")
            like_reason = r.get("like_reason", "")
            linkedin = r.get("linkedin_reply", "_Error generating reply_")
            twitter = r.get("twitter_reply", "_Error generating reply_")
            tone = r.get("tone_achieved", s["tone"])
            error = r.get("error", "")

            like_emoji = "👍" if like_action == "LIKE" else "⏭️"

            lines += [
                f"### {s['label']}",
                f"",
                f"> **Inbound comment:** \"{s['comment']}\"  ",
                f"> **Context:** {s['platform_context']}",
                f"",
                f"**{like_emoji} Like Action:** `{like_action}` — {like_reason}",
                f"",
                f"**LinkedIn Reply** *(tone: {tone})*:",
                f"",
                f"> {linkedin}",
                f"",
                f"**Twitter/X Reply:**",
                f"",
                f"> {twitter}",
                f"",
            ]
            if error:
                lines.append(f"⚠️ _Generation error: {error}_\n")

            lines += ["---", ""]

    lines += [
        "## Voice Quick Reference",
        "",
        "| Situation | Do | Don't |",
        "|-----------|-----|-------|",
        "| Pricing asked | Redirect to demo/conversation | Give specific numbers |",
        "| AI fear | Validate concern + reframe with evidence | Get defensive |",
        "| Competitor mentioned | Acknowledge, pivot to differentiation | Trash talk |",
        "| Bug/complaint | Acknowledge + take to DM | Ignore or be dismissive |",
        "| High praise | Brief genuine thanks + build on it | Over-hype or humble-brag |",
        "| Skeptic | Meet them where they are | Lecture or over-explain |",
        "",
        "---",
        "",
        "## Tone Guide",
        "",
        "| Tone | When to use | Style cue |",
        "|------|-------------|-----------|",
        "| `default` | General engagement | Natural, conversational |",
        "| `advocate` | AI skeptics, ROI questions | Lead with evidence, optimistic |",
        "| `empathetic` | Concerns, fears, onboarding worry | Validate first, reframe second |",
        "| `educational` | Data privacy, technical questions | Teach, don't sell |",
        "| `direct` | Pricing, existing-tool objections | Short, real, no hedging |",
        "| `community` | Excited users, peer founders | Warm, builds belonging |",
        "",
        "---",
        "_Generated by PM Framework marketing_voice module. Re-run weekly for freshness._",
        ""
    ]

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.test:
        print("=== gen_marketing_replies.py SELF-TEST ===")
        print(f"Scenarios: {len(COMMENT_SCENARIOS)}")
        print(f"Categories: {set(s['category'] for s in COMMENT_SCENARIOS)}")
        print(f"Output: {OUTPUT_PATH}")
        assert len(COMMENT_SCENARIOS) == 9
        print("✅ Self-test passed (no API calls)")
        return

    dry_run = args.dry_run
    print(f"\n{'='*60}")
    print(f"MARKETING REPLIES KIT GENERATOR")
    print(f"Scenarios: {len(COMMENT_SCENARIOS)} ({3} positive, {3} concern, {3} objection)")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    results = {}
    for scenario in COMMENT_SCENARIOS:
        result = generate_reply(scenario, dry_run)
        results[scenario["id"]] = result

    md = build_markdown(COMMENT_SCENARIOS, results)
    with open(OUTPUT_PATH, "w") as f:
        f.write(md)

    print(f"\n✅ Marketing replies kit saved: {OUTPUT_PATH}")
    successful = sum(1 for r in results.values() if "error" not in r)
    print(f"   {successful}/{len(COMMENT_SCENARIOS)} replies generated successfully")


if __name__ == "__main__":
    main()
