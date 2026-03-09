#!/usr/bin/env python3
import json, glob, re
from pathlib import Path

# Scan fail-reflections for lessons or action items
reflections_log = Path('/Users/harrisonfethe/.openclaw/workspace/memory/fail-reflections.jsonl')
lessons = []
if reflections_log.exists():
    with open(reflections_log, 'r') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            # Find any reflection that might contain a lesson
            if 'probable_cause' in data and data['agent'] == 'lenny':
                lessons.append(data['probable_cause'])

# Check if each lesson is encoded in current schema (mandatory fields, validation)
schema_file = Path('agents/lenny.md')
schema_text = schema_file.read_text() if schema_file.exists() else ""

for lesson in lessons[-3:]: # only check the last 3
    # Extract key phrase
    key = lesson.split()[0:3]
    found = any(k in schema_text for k in key if len(k) > 3)
    if not found:
        print(f'UNENCODED_LESSON: {lesson}')
    else:
        print(f'ENCODED: {lesson[:50]}')
