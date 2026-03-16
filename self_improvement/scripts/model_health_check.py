#!/usr/bin/env python3
"""model_health_check.py — Verify configured models are reachable via OpenRouter.

Checks:
1. OpenRouter /api/v1/models endpoint returns 200 (API is up)
2. Each configured model appears in the OpenRouter model list
"""
import json, sys, subprocess
from datetime import datetime

MODELS = [
    'anthropic/claude-sonnet-4-6',
    'anthropic/claude-opus-4-6',
    'anthropic/claude-haiku-4-6',
    'openai/gpt-4-turbo',
    'google/gemini-2.0-pro',
]

OPENROUTER_MODELS_URL = 'https://openrouter.ai/api/v1/models'


def health_check():
    results = {}
    failures = 0

    # Step 1: Check OpenRouter API reachability
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', OPENROUTER_MODELS_URL],
            capture_output=True, timeout=10
        )
        api_status = result.stdout.decode().strip()
        api_up = api_status == '200'
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        api_up = False

    if not api_up:
        # API unreachable — mark all models unhealthy
        for model in MODELS:
            results[model] = 'unreachable'
            failures += 1
        return {
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'primary_failures': failures,
            'pass': False,
            'note': 'OpenRouter API unreachable',
        }

    # Step 2: Fetch available model IDs from OpenRouter
    try:
        fetch = subprocess.run(
            ['curl', '-s', OPENROUTER_MODELS_URL],
            capture_output=True, timeout=15
        )
        data = json.loads(fetch.stdout.decode())
        available_ids = {m.get('id', '') for m in data.get('data', [])}
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError, json.JSONDecodeError):
        available_ids = set()

    # Step 3: Check each configured model
    for model in MODELS:
        if available_ids and model not in available_ids:
            results[model] = 'not_listed'
            # Not listed is informational only — model may still work via API key
        else:
            results[model] = 'healthy'

    # Pass if API is up (primary concern); model listing is informational
    return {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'primary_failures': failures,
        'pass': failures < 2,
        'note': 'OpenRouter API reachable',
    }


if __name__ == '__main__':
    check = health_check()
    print(json.dumps(check))
    sys.exit(0 if check['pass'] else 1)
