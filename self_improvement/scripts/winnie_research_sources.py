#!/usr/bin/env python3
import json, requests, time
from datetime import datetime, timedelta

SOURCES = {
  'anthropic_models': 'https://api.anthropic.com/models',
  'openai_models': 'https://api.openai.com/v1/models',
  'gemini_docs': 'https://ai.google.dev/models',
  'huggingface_trending': 'https://huggingface.co/api/models?sort=trending'
}

def check_source_freshness():
  results = {}
  for name, url in SOURCES.items():
    try:
      r = requests.head(url, timeout=5)
      results[name] = {'status': r.status_code, 'checked_at': datetime.utcnow().isoformat(), 'healthy': r.status_code < 400}
    except requests.RequestException as e:
      results[name] = {'status': 'error', 'error': str(e), 'healthy': False}
  
  alert_threshold = datetime.utcnow() - timedelta(days=7)
  with open('/Users/harrisonfethe/.openclaw/workspace/source_freshness.json', 'w') as f:
    json.dump(results, f, indent=2)
  
  unhealthy = [k for k,v in results.items() if not v['healthy']]
  if unhealthy:
    print(f'ALERT: {len(unhealthy)} sources unhealthy: {unhealthy}')
  return results

if __name__ == '__main__':
  check_source_freshness()