#!/usr/bin/env python3
"""
cron_model_check.py — Cron Model Allowlist Checker
Scans all cron definitions for deprecated/invalid model IDs.
Reports violations and optionally auto-patches to the recommended replacement.

Usage:
  python3 cron_model_check.py              # report only
  python3 cron_model_check.py --fix        # auto-patch deprecated models
  python3 cron_model_check.py --fix --dry  # dry run (show what would change)
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

JOBS_PATH = Path.home() / ".openclaw/cron/jobs.json"

# ── Deprecated model → recommended replacement ────────────────────────────
DEPRECATED = {
    "anthropic/claude-sonnet-4-5":        "anthropic/claude-sonnet-4-6",
    "anthropic/claude-opus-4-5":          "anthropic/claude-opus-4-6",
    "anthropic/claude-haiku-4-5":         "anthropic/claude-haiku-4-5",   # still valid, keep
    "openai-codex/gpt-5.2-codex":         "openai-codex/gpt-5.3-codex",
    "openai-codex/gpt-5.2-codex-spark":   "openai-codex/gpt-5.3-codex-spark",
    "google-antigravity/claude-sonnet-4-6-thinking": "anthropic/claude-sonnet-4-6",
    "google-antigravity/claude-opus-4-5-thinking":   "google-antigravity/claude-opus-4-6-thinking",
    "google-antigravity/claude-sonnet-4-5-thinking": "anthropic/claude-sonnet-4-6",
    # aliases that resolve to unknown models
    "claude-sonnet-4-5":                  "anthropic/claude-sonnet-4-6",
    "claude-opus-4-5":                    "anthropic/claude-opus-4-6",
}

# Models known to be valid
ALLOWLIST = {
    "anthropic/claude-sonnet-4-6",
    "anthropic/claude-opus-4-6",
    "anthropic/claude-haiku-4-5",
    "openai-codex/gpt-5.3-codex",
    "openai-codex/gpt-5.3-codex-spark",
    "google-antigravity/claude-opus-4-6-thinking",
    "google-antigravity/gemini-3-pro-high",
    "google-gemini-cli/gemini-2.5-pro",
    "google-gemini-cli/gemini-2.5-flash",
    # short aliases
    "sonnet", "opus", "haiku",
}


def load_jobs():
    if not JOBS_PATH.exists():
        print(f"❌ cron/jobs.json not found at {JOBS_PATH}")
        sys.exit(1)
    data = json.loads(JOBS_PATH.read_text())
    return data.get("jobs", data) if isinstance(data, dict) else data


def check_model(model: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Returns (is_valid, recommended_replacement_or_None)."""
    if model is None:
        return True, None  # no model set → uses default
    if model in ALLOWLIST:
        return True, None
    replacement = DEPRECATED.get(model)
    return False, replacement or "anthropic/claude-sonnet-4-6"


def run_cron_edit(job_id: str, new_model: str, dry: bool) -> bool:
    if dry:
        print(f"    [DRY] would run: openclaw cron edit {job_id} --model {new_model}")
        return True
    result = subprocess.run(
        ["openclaw", "cron", "edit", job_id, "--model", new_model],
        capture_output=True, text=True
    )
    return result.returncode == 0


def main():
    fix_mode = "--fix" in sys.argv
    dry_run = "--dry" in sys.argv

    jobs = load_jobs()
    violations = []
    ok_count = 0

    for job in jobs:
        if not job.get("enabled", True):
            continue
        model = job.get("payload", {}).get("model")
        valid, replacement = check_model(model)
        if valid:
            ok_count += 1
        else:
            violations.append({
                "id": job["id"],
                "name": job.get("name", "?"),
                "model": model,
                "replacement": replacement,
                "consecutive_errors": job.get("state", {}).get("consecutiveErrors", 0),
            })

    print(f"=== Cron Model Allowlist Check — {len(jobs)} jobs scanned ===")
    print(f"  ✅ Valid: {ok_count}")
    print(f"  ❌ Violations: {len(violations)}")
    print()

    if not violations:
        print("All cron models are on the allowlist. 🎉")
        return 0

    print("Violations:")
    for v in sorted(violations, key=lambda x: x["consecutive_errors"], reverse=True):
        print(f"  [{v['consecutive_errors']} errs] {v['name'][:45]}")
        print(f"    id:          {v['id']}")
        print(f"    model:       {v['model']}")
        print(f"    replacement: {v['replacement']}")
        if fix_mode:
            ok = run_cron_edit(v["id"], v["replacement"], dry_run)
            status = "✅ patched" if ok else "❌ patch failed"
            if dry_run:
                status = "🔵 (dry run)"
            print(f"    action:      {status}")
        print()

    if fix_mode and not dry_run:
        # Re-verify
        jobs2 = load_jobs()
        still_bad = []
        for job in jobs2:
            if not job.get("enabled", True):
                continue
            model = job.get("payload", {}).get("model")
            valid, _ = check_model(model)
            if not valid:
                still_bad.append(job["name"])
        if still_bad:
            print(f"⚠️  Still invalid after patch: {still_bad}")
            return 1
        else:
            print("✅ All patched successfully.")

    return 1 if violations and not fix_mode else 0


if __name__ == "__main__":
    sys.exit(main())
