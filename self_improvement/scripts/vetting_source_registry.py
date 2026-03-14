#!/usr/bin/env python3.13
"""Winnie vetting source registry and deduplication."""
import json
from pathlib import Path
from datetime import datetime, timedelta

REGISTRY_FILE = Path('/Users/harrisonfethe/.openclaw/workspace/self_improvement/logs/vetting_sources.json')

def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {'sources': {}, 'last_updated': None}

def should_refresh(source_url, max_age_hours=72):
    """Return True if source hasn't been checked in max_age_hours."""
    reg = load_registry()
    if source_url not in reg['sources']:
        return True
    last_check = datetime.fromisoformat(reg['sources'][source_url]['checked_at'])
    return datetime.now() - last_check > timedelta(hours=max_age_hours)

def mark_processed(source_url, findings):
    """Record source as processed with findings summary."""
    reg = load_registry()
    reg['sources'][source_url] = {
        'checked_at': datetime.now().isoformat(),
        'findings_hash': hash(str(findings)),
        'evidence_type': findings.get('type', 'unknown')
    }
    reg['last_updated'] = datetime.now().isoformat()
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2))

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        url = sys.argv[2] if len(sys.argv) > 2 else ''
        print('REFRESH' if should_refresh(url) else 'SKIP')
