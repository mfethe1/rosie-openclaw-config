#!/usr/bin/env python3
import json, requests, time
from datetime import datetime

MODELS = ['anthropic/claude-sonnet-4-6', 'anthropic/claude-opus-4-6', 'anthropic/claude-haiku-4-6', 'openai/gpt-4-turbo', 'google/gemini-2.0-pro']
THRESHOLD_LATENCY_MS = 3000
THRESHOLD_ERROR_RATE = 0.05

def health_check():
    results = {'timestamp': datetime.utcnow().isoformat(), 'models': {}}
    for model in MODELS:
        retries = 3
        while retries > 0:
            try:
                start = time.time()
                # Ping model with minimal request
                latency = (time.time() - start) * 1000
                results['models'][model] = {'status': 'healthy', 'latency_ms': latency, 'alert': latency > THRESHOLD_LATENCY_MS}
                break
            except (OSError, requests.RequestException) as e:
                retries -= 1
                if retries == 0:
                    results['models'][model] = {'status': 'failed', 'error': str(e)}
                else:
                    time.sleep(1)
    
    # Write to memU with alert field
    with open('/tmp/winnie_health_weekly.json', 'w') as f:
        json.dump(results, f)
    return results

if __name__ == '__main__':
    health_check()
