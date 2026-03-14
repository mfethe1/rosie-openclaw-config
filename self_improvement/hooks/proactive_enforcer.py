#!/usr/bin/env python3
"""Ensure workflow agent prompts enforce proactive execution behavior."""

from __future__ import annotations

import argparse
from pathlib import Path


BLOCK = """
## Proactive Execution Mandate

- NEVER ask for permission on routine, reversible work.
- If there is a logical next step, take it and report outcomes.
- Do not stop at diagnosis when a safe fix is available.
- If blocked, continue with other unblocked work and report exact blocker.
- Validate with concrete commands before marking work complete.
""".strip()


def target_files(workspace: Path) -> list[Path]:
    files = []
    files.extend(workspace.glob("workspaces/workflows/*/agents/*/AGENTS.md"))
    files.extend(workspace.glob("antfarm/workflows/*/agents/*/AGENTS.md"))
    return sorted({p.resolve() for p in files})


def enforce(path: Path, apply: bool) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    if "## Proactive Execution Mandate" in text:
        return False, "already-present"

    marker = "## What NOT To Do"
    if marker in text:
        updated = text.replace(marker, f"{BLOCK}\n\n{marker}", 1)
    else:
        updated = text.rstrip() + "\n\n" + BLOCK + "\n"

    if apply:
        path.write_text(updated, encoding="utf-8")
    return True, "patched"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patch AGENTS.md files with proactive mandate"
    )
    parser.add_argument(
        "--workspace",
        default="/Users/harrisonfethe/.openclaw",
        help="OpenClaw root directory",
    )
    parser.add_argument(
        "--check", action="store_true", help="Check only, do not modify files"
    )
    args = parser.parse_args()

    root = Path(args.workspace)
    files = target_files(root)

    patched = 0
    for file_path in files:
        changed, status = enforce(file_path, apply=not args.check)
        if changed:
            patched += 1
        print(f"{status}: {file_path}")

    print(
        f"total={len(files)} patched={patched} mode={'check' if args.check else 'apply'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
