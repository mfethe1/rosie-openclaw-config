#!/usr/bin/env python3
"""
Campaign Improvement Loop — weekly analysis of what's working.
Reads post_log + review_log + engagement_report, generates new content
recommendations and replenishes the content queue with better posts.
"""

import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
POST_LOG = BASE_DIR / "post_log.jsonl"
REVIEW_LOG = BASE_DIR / "review_log.jsonl"
QUEUE_FILE = BASE_DIR / "content_queue.json"
ENGAGEMENT_REPORT = BASE_DIR / "engagement_report.md"
CAMPAIGN_NOTES = BASE_DIR / "campaign_notes.md"

def load_env():
    for env_file in [
        Path.home() / ".openclaw/secrets/x-twitter.env",
        Path.home() / ".openclaw/secrets/deploy.env"
    ]:
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip().lstrip("export ")
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ[k] = v.strip('"')

def read_post_performance():
    """Summarize post performance from logs."""
    posts = []
    if POST_LOG.exists():
        with open(POST_LOG) as f:
            for line in f:
                try:
                    posts.append(json.loads(line))
                except:
                    pass

    reviews = []
    if REVIEW_LOG.exists():
        with open(REVIEW_LOG) as f:
            for line in f:
                try:
                    reviews.append(json.loads(line))
                except:
                    pass

    return posts, reviews

def generate_new_posts(performance_summary: str, api_key: str) -> list:
    """Use Claude to generate a new batch of improved posts based on what worked."""
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 3000,
            "messages": [{
                "role": "user",
                "content": f"""You are a B2B SaaS growth marketer for Protelynx.

Products:
- IssuesFlow: AI-powered issue workflow automation for engineering teams. → issuesflow.ai
- Protelynx brand: "AI that replaces busywork" — targeting dev teams at startups/SMBs.

Hard policy:
- Do NOT mention JiraFlow, Content Flow, ContentPilot, jiraflow.io, or contentpilot.ai.
- Only promote products that are currently active and working (IssuesFlow).
PERFORMANCE DATA FROM RECENT POSTS:
{performance_summary}

Generate 8 new X (Twitter) posts optimized for B2B SaaS audience.
Mix of angles:
- 2x product-specific (IssuesFlow)
- 2x thought leadership (AI trends, future of work)
- 2x build-in-public (founder journey, lessons learned)
- 1x social proof / results-focused
- 1x direct CTA / offer post

Format as JSON array:
[
  {{
    "id": <next_id>,
    "text": "full post text with hashtags",
    "tags": ["tag1", "tag2"],
    "angle": "thought-leadership|product|build-in-public|social-proof|cta",
    "posted": false
  }},
  ...
]

Rules:
- Under 280 chars preferred, 500 max
- Strong hook in first line (question, stat, bold claim)
- Max 4 hashtags
- Include URL only when directly relevant
- No emojis overload (1-2 max per post)"""
            }]
        },
        timeout=60
    )

    if resp.status_code != 200:
        print(f"⚠️  Content generation failed: {resp.status_code}")
        return []

    content = resp.json()["content"][0]["text"]
    import re
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    return []

def main():
    load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    posts, reviews = read_post_performance()
    print(f"📊 Analyzing {len(posts)} posts, {len(reviews)} AI reviews...")

    # Build performance summary
    avg_score = 0
    if reviews:
        scores = [r.get("engagement_score", 5) for r in reviews if r.get("engagement_score")]
        avg_score = sum(scores) / len(scores) if scores else 5
    
    engagement_text = ""
    if ENGAGEMENT_REPORT.exists():
        engagement_text = ENGAGEMENT_REPORT.read_text()[:2000]

    performance_summary = f"""
Posts sent: {len(posts)}
AI reviews done: {len(reviews)}
Average AI engagement score: {avg_score:.1f}/10

Recent engagement data:
{engagement_text[:1000] if engagement_text else "No engagement data yet (tokens need refresh)"}

Top performing post angles based on review scores:
{chr(10).join(f"- {r.get('reasoning','')[:100]}" for r in sorted(reviews, key=lambda x: x.get('engagement_score',0), reverse=True)[:3])}
"""

    if not api_key:
        print("⚠️  No Anthropic API key — skipping content generation")
        return

    print("🤖 Generating new optimized posts...")
    new_posts = generate_new_posts(performance_summary, api_key)

    if not new_posts:
        print("⚠️  No new posts generated")
        return

    # Load existing queue and get max ID
    queue = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
    max_id = max((p.get("id", 0) for p in queue), default=0)

    # Renumber and add new posts
    for i, p in enumerate(new_posts):
        p["id"] = max_id + i + 1
        p["generated_at"] = datetime.now(timezone.utc).isoformat()
        p["source"] = "campaign_improve"

    queue.extend(new_posts)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))

    # Write campaign notes
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    note = f"""
## Campaign Review — {ts}
- Posts analyzed: {len(posts)}
- Avg AI quality score: {avg_score:.1f}/10
- New posts added to queue: {len(new_posts)}
- Angles: {', '.join(set(p.get('angle','') for p in new_posts))}

### What's working:
{chr(10).join(f"- {r.get('reasoning','')[:120]}" for r in sorted(reviews, key=lambda x: x.get('engagement_score',0), reverse=True)[:3])}

### New posts added:
{chr(10).join(f"- [{p['id']}] {p['text'][:80]}..." for p in new_posts)}
"""
    with open(CAMPAIGN_NOTES, "a") as f:
        f.write(note)

    print(f"✅ Added {len(new_posts)} new AI-generated posts to queue")
    print(f"📝 Campaign notes updated: {CAMPAIGN_NOTES}")

if __name__ == "__main__":
    main()
