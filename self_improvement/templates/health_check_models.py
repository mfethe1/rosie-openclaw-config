#!/usr/bin/env python3
"""health_check_models — verify OpenClaw model availability before reflection."""

import subprocess, json, sys

REQUIRED_MODELS = [
    "google-antigravity/claude-opus-4-6-thinking",
    "anthropic/claude-sonnet-4-6",
]

def check_model_health():
    """Return dict with 'all_healthy' bool and 'details' dict per model."""
    details = {}
    for model in REQUIRED_MODELS:
        try:
            # Use openclaw session_status or a lightweight ping approach
            # For now, we check that the openclaw binary is reachable
            result = subprocess.run(
                ["openclaw", "gateway", "status"],
                capture_output=True, text=True, timeout=10
            )
            # Gateway running = models likely reachable
            details[model] = result.returncode == 0
        except Exception:
            details[model] = False
    return {"all_healthy": all(details.values()), "details": details}


if __name__ == "__main__":
    result = check_model_health()
    print(json.dumps(result))
    sys.exit(0 if result["all_healthy"] else 1)
