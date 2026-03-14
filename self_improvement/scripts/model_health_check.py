#!/usr/bin/env python3
import json, sys, subprocess
from datetime import datetime

MODELS = ['anthropic/claude-sonnet-4-6', 'anthropic/claude-opus-4-6', 'anthropic/claude-haiku-4-6', 'openai/gpt-4-turbo', 'google/gemini-2.0-pro']

def health_check():
    results = {}
    failures = 0
    for model in MODELS:
        try:
            result = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', f'https://api.example.com/health?model={model}'], capture_output=True, timeout=5)
            status = result.stdout.decode().strip()
            results[model] = 'healthy' if status == '200' else 'unhealthy'
            if status != '200': failures += 1
        except: results[model] = 'unreachable'; failures += 1
    return {'timestamp': datetime.now().isoformat(), 'results': results, 'primary_failures': failures, 'pass': failures < 2}

if __name__ == '__main__':
    check = health_check()
    print(json.dumps(check))
    sys.exit(0 if check['pass'] else 1)
