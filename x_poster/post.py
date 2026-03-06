#!/usr/bin/env python3
"""
X (Twitter) Auto-Poster for Protelynx/ContentPilot/JiraFlow
Posts from content_queue.json, rotates through posts, logs results.
"""

import os
import sys
import json
import time
import random
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Setup ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
QUEUE_FILE = BASE_DIR / "content_queue.json"
LOG_FILE = BASE_DIR / "post_log.jsonl"
ENV_FILE = Path.home() / ".openclaw/secrets/x-twitter.env"

FORBIDDEN_TERMS = [
    "jiraflow",
    "jiraflow.io",
    "jiraflow.ai",
    "content flow",
    "contentflow",
    "contentpilot",
    "contentpilot.ai",
]
ALLOWED_PRODUCT_TERMS = [
    "issuesflow",
    "issuesflow.ai",
    "issuesflow.com",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("x_poster")

# ── Load credentials ───────────────────────────────────────────────────────
def load_env():
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k] = v.strip('"')

# ── Load/save queue ────────────────────────────────────────────────────────
def load_queue():
    with open(QUEUE_FILE) as f:
        return json.load(f)

def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def violates_policy(text: str):
    t = (text or "").lower()
    for term in FORBIDDEN_TERMS:
        if term in t:
            return True, f"forbidden term: {term}"
    return False, ""

# ── Refresh OAuth2 token ───────────────────────────────────────────────────
def refresh_oauth2_token():
    """Refresh the OAuth2 user token using the refresh token."""
    import requests, base64
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    refresh_token = os.environ.get("TWITTER_OAUTH2_REFRESH_TOKEN")
    oauth2_client_id = os.environ.get("TWITTER_OAUTH2_CLIENT_ID", api_key)

    if not refresh_token:
        return None, None

    creds = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    resp = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {creds}"
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": oauth2_client_id,
        }
    )
    if resp.status_code == 200:
        data = resp.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token", refresh_token)
        # Update env file
        _update_env("TWITTER_OAUTH2_ACCESS_TOKEN", new_access)
        if new_refresh != refresh_token:
            _update_env("TWITTER_OAUTH2_REFRESH_TOKEN", new_refresh)
        os.environ["TWITTER_OAUTH2_ACCESS_TOKEN"] = new_access
        os.environ["TWITTER_OAUTH2_REFRESH_TOKEN"] = new_refresh
        log.info("OAuth2 token refreshed successfully")
        return new_access, new_refresh
    else:
        log.error(f"Token refresh failed: {resp.status_code} {resp.text[:200]}")
        return None, None

def _update_env(key, value):
    content = ENV_FILE.read_text()
    lines = content.splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f'{key}="{value}"'
            found = True
            break
    if not found:
        lines.append(f'{key}="{value}"')
    ENV_FILE.write_text("\n".join(lines) + "\n")

# ── Post to X ──────────────────────────────────────────────────────────────
def post_tweet(text):
    """Attempt to post using OAuth2 user context, fallback to OAuth1."""
    import requests
    from requests_oauthlib import OAuth1

    # Try OAuth2 user context first
    access_token = os.environ.get("TWITTER_OAUTH2_ACCESS_TOKEN")
    if access_token:
        resp = requests.post(
            "https://api.twitter.com/2/tweets",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"text": text}
        )
        if resp.status_code == 201:
            return resp.json(), "oauth2"
        elif resp.status_code == 401:
            log.warning("OAuth2 token expired, attempting refresh...")
            new_token, _ = refresh_oauth2_token()
            if new_token:
                resp = requests.post(
                    "https://api.twitter.com/2/tweets",
                    headers={
                        "Authorization": f"Bearer {new_token}",
                        "Content-Type": "application/json"
                    },
                    json={"text": text}
                )
                if resp.status_code == 201:
                    return resp.json(), "oauth2-refreshed"
        log.warning(f"OAuth2 post failed: {resp.status_code} {resp.text[:200]}")

    # Fallback: OAuth1
    auth = OAuth1(
        os.environ.get("TWITTER_API_KEY"),
        os.environ.get("TWITTER_API_SECRET"),
        os.environ.get("TWITTER_ACCESS_TOKEN"),
        os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")
    )
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        headers={"Content-Type": "application/json"},
        json={"text": text}
    )
    if resp.status_code == 201:
        return resp.json(), "oauth1"

    raise Exception(f"All auth methods failed: {resp.status_code} {resp.text[:300]}")

# ── Pick next post ─────────────────────────────────────────────────────────
def pick_next(queue, tag_filter=None):
    """Pick next valid unposted item. Auto-block policy violations."""
    candidates = [p for p in queue if not p.get("posted") and not p.get("blocked")]
    if not candidates:
        # Reset only non-blocked posts for next cycle
        log.info("All eligible posts used — resetting queue for next cycle")
        for p in queue:
            if not p.get("blocked"):
                p["posted"] = False
        candidates = [p for p in queue if not p.get("posted") and not p.get("blocked")]

    if tag_filter:
        filtered = [p for p in candidates if tag_filter in p.get("tags", [])]
        if filtered:
            candidates = filtered

    for p in candidates:
        violates, reason = violates_policy(p.get("text", ""))
        if violates:
            p["blocked"] = True
            p["blocked_reason"] = reason
            p["blocked_at"] = datetime.now(timezone.utc).isoformat()
            log.warning(f"Blocking post [{p.get('id')}] due to policy: {reason}")
            continue
        return p

    save_queue(queue)
    raise RuntimeError("No policy-compliant posts available in queue")

# ── Log result ─────────────────────────────────────────────────────────────
def log_result(post, result, auth_method, error=None):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "post_id": post["id"],
        "tags": post.get("tags", []),
        "tweet_id": result.get("data", {}).get("id") if result else None,
        "auth": auth_method,
        "error": error,
        "text_preview": post["text"][:80]
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

# ── Main ───────────────────────────────────────────────────────────────────
def ai_review_post(text: str) -> str:
    """Run AI review on post text, return improved version."""
    import subprocess
    reviewer = Path(__file__).parent / "ai_review.py"
    if not reviewer.exists():
        return text
    try:
        result = subprocess.run(
            [sys.executable, str(reviewer), text],
            capture_output=True, text=True, timeout=45
        )
        tmp = Path("/tmp/x_next_post.txt")
        if tmp.exists():
            improved = tmp.read_text().strip()
            tmp.unlink()
            if improved and len(improved) > 10:
                log.info(f"AI review complete — improved from {len(text)} to {len(improved)} chars")
                return improved
    except Exception as e:
        log.warning(f"AI review skipped: {e}")
    return text


def main():
    load_env()
    queue = load_queue()

    tag_filter = sys.argv[1] if len(sys.argv) > 1 else None
    post = pick_next(queue, tag_filter)

    log.info(f"Reviewing + posting: [{post['id']}] {post['text'][:60]}...")

    # ── AI improvement step (runs before every post) ──────────────────────
    original_text = post["text"]
    final_text = ai_review_post(original_text)

    violates, reason = violates_policy(final_text)
    if violates:
        post["blocked"] = True
        post["blocked_reason"] = f"AI output violation: {reason}"
        post["blocked_at"] = datetime.now(timezone.utc).isoformat()
        save_queue(queue)
        print(f"❌ Post blocked by policy: {reason}")
        sys.exit(1)

    try:
        result, auth_method = post_tweet(final_text)
        tweet_id = result.get("data", {}).get("id")
        post["posted"] = True
        post["tweet_id"] = tweet_id
        post["posted_at"] = datetime.now(timezone.utc).isoformat()
        save_queue(queue)
        entry = log_result(post, result, auth_method)
        print(f"✅ Posted tweet {tweet_id} via {auth_method}")
        print(f"   https://x.com/i/web/status/{tweet_id}")
    except Exception as e:
        entry = log_result(post, None, "none", error=str(e))
        print(f"❌ Post failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
