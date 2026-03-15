#!/usr/bin/env python3
import json, requests
from datetime import datetime

RESEARCH_SOURCES = {
    'claude_changelog': 'https://anthropic.com/changelog',
    'openai_models': 'https://platform.openai.com/docs/models',
    'google_ai_releases': 'https://ai.google.dev/release-notes',
    'github_trending_ai': 'https://github.com/trending?since=weekly&spoken_language_code=&d=1',
}

def check_freshness():
    results = {'timestamp': datetime.utcnow().isoformat(), 'sources': {}}
    for name, url in RESEARCH_SOURCES.items():
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            results['sources'][name] = {'status': 'ok' if resp.status_code < 400 else 'degraded', 'code': resp.status_code, 'last_checked': datetime.utcnow().isoformat()}
        except requests.RequestException as e:
            results['sources'][name] = {'status': 'unreachable', 'error': str(e)}
    with open('/tmp/winnie_source_freshness.json', 'w') as f:
        json.dump(results, f)
    return results

if __name__ == '__main__':
    check_freshness()
