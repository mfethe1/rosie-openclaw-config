#!/usr/bin/env python3
import json
import sys
import os

REQUIRED_KEYS = {
    "last_run": str,
    "what_changed": str,
    "next_owner": str,
    "blockers": list,
    "hypotheses": list,
    "broadcasts": list,
    "last_updated": str,
    "last_updated_by": str
}

def validate_data(data):
    missing = []
    invalid_type = []

    for key, expected_type in REQUIRED_KEYS.items():
        if key not in data:
            missing.append(key)
        elif data[key] is not None and not isinstance(data[key], expected_type):
            invalid_type.append(f"{key} (expected {expected_type.__name__}, got {type(data[key]).__name__})")

    if missing or invalid_type:
        error_msg = "HARD FAIL: shared-state.json schema validation failed."
        if missing:
            error_msg += f"\nMissing keys: {', '.join(missing)}"
        if invalid_type:
            error_msg += f"\nInvalid types: {', '.join(invalid_type)}"
        return False, error_msg

    return True, "SUCCESS: shared-state.json schema validation passed."

def main():
    state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shared-state.json")
    if not os.path.exists(state_file):
        print(f"HARD FAIL: shared-state.json not found at {state_file}")
        sys.exit(1)

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"HARD FAIL: shared-state.json is malformed JSON. Error: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"HARD FAIL: Could not read shared-state.json. Error: {e}")
        sys.exit(1)

    is_valid, msg = validate_data(data)
    print(msg)
    if not is_valid:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
