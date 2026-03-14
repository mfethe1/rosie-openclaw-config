#!/usr/bin/env python3
"""
marketing_voice.py — Brand Voice Response Generator
Generates social media responses in Michael's voice.

Usage:
    python3 marketing_voice.py respond --post "Great product! How does pricing work?" --platform linkedin
    python3 marketing_voice.py respond --post "AI will replace jobs" --platform twitter --tone advocate
    python3 marketing_voice.py --test
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# Graceful event_logger import
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from event_logger import log_event
except ImportError:
    def log_event(event_type, data=None, **kwargs):
        pass

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"

BRAND_VOICE = """You are generating social media responses for Michael Fethe, founder of Protelynx AI.

## Michael's Voice Profile
- **Tone**: Professional but approachable — never corporate-stiff, never casual-sloppy
- **Identity**: Business owner who actually uses AI daily in construction tech
- **Core beliefs**: AI amplifies human expertise; it doesn't replace skilled tradespeople
- **Personality**: Direct, practical, optimistic about technology, impatient with hype without results
- **Avoids**: Excessive jargon, humble-brags, vague platitudes, political polarization
- **Leads with**: Real outcomes, practical examples, builder/operator empathy

## Brand Context
- Protelynx AI: AI-powered tools for construction estimating and project management
- Products: BuildBid (construction estimating), ContentPilot (marketing automation)
- ICP: GCs, estimators, small-to-mid construction firms digitizing operations
- Michael's POV: Construction is the last major industry to embrace AI; the opportunity is massive

## Platform-Specific Voice
- **LinkedIn**: Thoughtful, data-backed, 3-5 sentences max, ends with insight or question
- **Twitter/X**: Punchy, 1-2 sentences, direct takes, no hedging
- **Instagram**: Human, visual-adjacent, story-driven, 2-3 sentences
- **Facebook**: Community-friendly, practical tips, slightly longer

## Engagement Rules
- Always acknowledge the person before making a point
- Don't dodge hard questions — give a real answer or redirect with transparency
- On AI skepticism: validate the concern, then reframe with evidence
- On pricing questions: don't give specifics, invite them to a demo/conversation
- Like-worthy posts: acknowledge with action instruction + warm reply
"""

TONE_PROMPTS = {
    "default": "Respond naturally in Michael's voice.",
    "advocate": "Take a strong advocate position for AI in this industry. Lead with evidence and optimism, not defense.",
    "empathetic": "Lead with empathy for the concern raised before pivoting to your perspective.",
    "educational": "Teach first, sell never. Share a concrete insight or data point.",
    "direct": "Be maximally direct. No fluff. Give the real answer in as few words as possible.",
    "community": "Build community connection. Acknowledge shared experience. Invite dialogue.",
}

PLATFORM_CONSTRAINTS = {
    "twitter": {"max_chars": 280, "note": "Keep it under 280 characters. One sharp take."},
    "linkedin": {"max_chars": 700, "note": "Professional context. 3-5 sentences. Can include a question at end."},
    "instagram": {"max_chars": 400, "note": "Human, story-adjacent. 2-3 sentences."},
    "facebook": {"max_chars": 500, "note": "Community tone. Practical and warm."},
}


def call_anthropic(system_prompt: str, user_message: str, temperature: float = 0.6) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    payload = {
        "model": MODEL,
        "max_tokens": 512,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["content"][0]["text"]


def generate_response(post: str, platform: str, tone: str = "default",
                      like: bool = True, variants: int = 1) -> dict:
    platform = platform.lower()
    platform_info = PLATFORM_CONSTRAINTS.get(platform, {"max_chars": 500, "note": "Standard social media."})
    tone_instruction = TONE_PROMPTS.get(tone, TONE_PROMPTS["default"])

    user_message = f"""## Incoming Post/Comment
{post}

## Platform: {platform.upper()}
{platform_info['note']}

## Tone Instruction
{tone_instruction}

## Task
Generate {variants} response variant(s) in Michael's voice.

Output as JSON:
{{
  "should_like": true/false (should Michael like/react to this post?),
  "like_instruction": "Like this post" or "No like needed",
  "like_reason": "Why like or not",
  "responses": [
    {{
      "variant": 1,
      "text": "The response text",
      "char_count": 123,
      "tone_achieved": "description of tone used"
    }}
  ],
  "platform_fit_notes": "Any notes on platform optimization"
}}"""

    system = BRAND_VOICE
    result_text = call_anthropic(system, user_message, temperature=0.65)

    # Parse JSON from response
    try:
        # Find JSON block
        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(result_text[start:end])
        else:
            result = {"raw_response": result_text, "error": "Could not parse JSON"}
    except json.JSONDecodeError:
        result = {"raw_response": result_text, "error": "JSON parse failed"}

    return result


def main():
    parser = argparse.ArgumentParser(description="Brand Voice Response Generator")
    subparsers = parser.add_subparsers(dest="command")

    respond_parser = subparsers.add_parser("respond", help="Generate a response")
    respond_parser.add_argument("--post", required=True, help="The post or comment to respond to")
    respond_parser.add_argument("--platform", default="linkedin",
                                choices=["linkedin", "twitter", "instagram", "facebook"],
                                help="Social media platform")
    respond_parser.add_argument("--tone", default="default",
                                choices=list(TONE_PROMPTS.keys()),
                                help="Response tone")
    respond_parser.add_argument("--variants", type=int, default=1, help="Number of response variants")
    respond_parser.add_argument("--no-like", action="store_true", help="Skip like recommendation")

    parser.add_argument("--test", action="store_true", help="Run self-test")

    args = parser.parse_args()

    if "--test" in sys.argv or (hasattr(args, 'test') and args.test):
        print("=== marketing_voice.py SELF-TEST ===")
        print(f"Model: {MODEL}")
        print(f"Platforms: {list(PLATFORM_CONSTRAINTS.keys())}")
        print(f"Tones: {list(TONE_PROMPTS.keys())}")
        print(f"Brand voice length: {len(BRAND_VOICE)} chars")
        print("✅ Self-test passed (no API calls)")
        return

    if args.command == "respond":
        print(f"Generating {args.variants} response(s) for {args.platform.upper()}...")
        try:
            result = generate_response(
                post=args.post,
                platform=args.platform,
                tone=args.tone,
                like=not args.no_like,
                variants=args.variants
            )

            print("\n" + "="*60)
            print(f"POST: {args.post[:100]}...")
            print("="*60)

            if "error" in result:
                print(f"Parse error: {result['error']}")
                print(result.get("raw_response", ""))
            else:
                print(f"\n👍 Like Action: {result.get('like_instruction', 'N/A')}")
                print(f"   Reason: {result.get('like_reason', 'N/A')}")
                print()

                for resp in result.get("responses", []):
                    print(f"--- Variant {resp.get('variant', 1)} ({resp.get('char_count', '?')} chars) ---")
                    print(resp.get("text", ""))
                    print(f"Tone: {resp.get('tone_achieved', 'N/A')}")
                    print()

                if result.get("platform_fit_notes"):
                    print(f"Platform notes: {result['platform_fit_notes']}")

            log_event("marketing_voice_respond", {
                "platform": args.platform,
                "tone": args.tone,
                "post_preview": args.post[:100]
            })

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    if "--test" in sys.argv:
        print("=== marketing_voice.py SELF-TEST ===")
        print(f"Model: {MODEL}")
        print(f"Platforms: {list(PLATFORM_CONSTRAINTS.keys())}")
        print(f"Tones: {list(TONE_PROMPTS.keys())}")
        print("✅ Self-test passed (no API calls)")
        sys.exit(0)
    main()
