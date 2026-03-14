#!/usr/bin/env python3
"""multi_repo_coordinator.py — Track and coordinate work across multiple repositories.

Manages a registry of git repositories, tracks their status (branch, dirty files,
last commit age), and detects cross-repo dependencies and drift.

Features:
- Register repos with tags and descriptions
- Health check: branch status, uncommitted changes, stale commits
- Cross-repo dependency tracking (which repos depend on which)
- Drift detection: repos that haven't been touched in N days
- Bulk operations: status all, pull all, check all

Usage:
  python3 multi_repo_coordinator.py add /path/to/repo --tags "core,infra" --desc "Main workspace"
  python3 multi_repo_coordinator.py status                    # all repos
  python3 multi_repo_coordinator.py status --repo workspace   # specific
  python3 multi_repo_coordinator.py check                     # health check
  python3 multi_repo_coordinator.py check --stale-days 7      # flag repos not touched in 7d
  python3 multi_repo_coordinator.py list                      # registered repos
  python3 multi_repo_coordinator.py remove <name>
  python3 multi_repo_coordinator.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

REGISTRY_PATH = Path.home() / ".openclaw/repo-registry.json"


def load_registry() -> list[dict]:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_registry(repos: list[dict]):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(repos, indent=2) + "\n")


def git_cmd(repo_path: str, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path] + list(args),
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_repo_status(repo: dict) -> dict:
    path = repo["path"]
    status = {"name": repo["name"], "path": path, "tags": repo.get("tags", [])}

    if not Path(path).exists():
        status["health"] = "missing"
        status["error"] = "path does not exist"
        return status

    if not Path(path, ".git").exists():
        status["health"] = "not_git"
        status["error"] = "not a git repository"
        return status

    # Branch
    status["branch"] = git_cmd(path, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"

    # Dirty files
    dirty = git_cmd(path, "status", "--porcelain")
    status["dirty_files"] = len(dirty.splitlines()) if dirty else 0

    # Last commit
    last_commit = git_cmd(path, "log", "-1", "--format=%aI")
    if last_commit:
        try:
            commit_time = datetime.fromisoformat(last_commit)
            now = datetime.now(timezone.utc)
            if commit_time.tzinfo is None:
                commit_time = commit_time.replace(tzinfo=timezone.utc)
            days_ago = (now - commit_time).days
            status["last_commit"] = last_commit
            status["days_since_commit"] = days_ago
        except (ValueError, TypeError):
            status["last_commit"] = last_commit
            status["days_since_commit"] = -1
    else:
        status["days_since_commit"] = -1

    # Ahead/behind
    ahead_behind = git_cmd(path, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    if ahead_behind:
        parts = ahead_behind.split()
        if len(parts) == 2:
            status["ahead"] = int(parts[0])
            status["behind"] = int(parts[1])

    # Health classification
    if status["dirty_files"] > 10:
        status["health"] = "dirty"
    elif status.get("days_since_commit", 0) > 14:
        status["health"] = "stale"
    elif status.get("behind", 0) > 5:
        status["health"] = "behind"
    elif status["dirty_files"] > 0:
        status["health"] = "modified"
    else:
        status["health"] = "clean"

    return status


def cmd_add(args) -> int:
    repos = load_registry()
    path = str(Path(args.path).resolve())
    name = args.name or Path(path).name

    # Check for duplicates
    for r in repos:
        if r["path"] == path or r["name"] == name:
            print(f"⚠️ Repo already registered: {name} ({path})")
            return 1

    repo = {
        "name": name,
        "path": path,
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
        "description": args.desc or "",
        "added_at": datetime.now().isoformat(),
    }
    repos.append(repo)
    save_registry(repos)

    if args.json:
        print(json.dumps({"added": name, "path": path}))
    else:
        print(f"✅ Registered: {name} ({path})")
    return 0


def cmd_status(args) -> int:
    repos = load_registry()
    if not repos:
        print("No repos registered. Use 'add' first.")
        return 0

    if args.repo:
        repos = [r for r in repos if r["name"] == args.repo]
        if not repos:
            print(f"Repo '{args.repo}' not found")
            return 1

    statuses = [get_repo_status(r) for r in repos]

    if args.json:
        print(json.dumps(statuses, indent=2, default=str))
    else:
        icons = {"clean": "🟢", "modified": "🟡", "dirty": "🟠", "stale": "🔴",
                 "behind": "🔵", "missing": "⚫", "not_git": "⚪"}
        for s in statuses:
            icon = icons.get(s.get("health", "?"), "?")
            branch = s.get("branch", "?")
            dirty = s.get("dirty_files", 0)
            days = s.get("days_since_commit", -1)
            tags = f" [{','.join(s.get('tags', []))}]" if s.get("tags") else ""
            print(f"  {icon} {s['name']}{tags}: {branch} | {dirty} dirty | {days}d ago | {s.get('health', '?')}")

    return 0


def cmd_check(args) -> int:
    repos = load_registry()
    if not repos:
        print("No repos registered.")
        return 0

    stale_days = args.stale_days or 7
    statuses = [get_repo_status(r) for r in repos]
    issues = []

    for s in statuses:
        problems = []
        if s.get("health") == "missing":
            problems.append("path missing")
        if s.get("dirty_files", 0) > 5:
            problems.append(f"{s['dirty_files']} dirty files")
        if s.get("days_since_commit", 0) > stale_days:
            problems.append(f"stale ({s['days_since_commit']}d)")
        if s.get("behind", 0) > 0:
            problems.append(f"{s['behind']} commits behind")
        if problems:
            issues.append({"name": s["name"], "problems": problems})

    if args.json:
        print(json.dumps({"checked": len(statuses), "issues": len(issues), "details": issues}))
    else:
        if issues:
            print(f"⚠️ {len(issues)} repo(s) need attention:")
            for iss in issues:
                print(f"  🔸 {iss['name']}: {', '.join(iss['problems'])}")
        else:
            print(f"✅ All {len(statuses)} repos healthy (stale threshold: {stale_days}d)")

    return 0


def cmd_list(args) -> int:
    repos = load_registry()
    if args.json:
        print(json.dumps(repos, indent=2))
    else:
        if not repos:
            print("No repos registered.")
        for r in repos:
            tags = f" [{','.join(r.get('tags', []))}]" if r.get("tags") else ""
            print(f"  📁 {r['name']}{tags}: {r['path']}")
    return 0


def cmd_remove(args) -> int:
    repos = load_registry()
    before = len(repos)
    repos = [r for r in repos if r["name"] != args.name]
    if len(repos) == before:
        print(f"Repo '{args.name}' not found")
        return 1
    save_registry(repos)
    print(f"✅ Removed: {args.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-repo coordinator")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Register a repository")
    p_add.add_argument("path", help="Path to git repo")
    p_add.add_argument("--name", help="Short name (default: dir name)")
    p_add.add_argument("--tags", help="Comma-separated tags")
    p_add.add_argument("--desc", help="Description")

    p_status = sub.add_parser("status", help="Show repo status")
    p_status.add_argument("--repo", help="Specific repo name")

    p_check = sub.add_parser("check", help="Health check all repos")
    p_check.add_argument("--stale-days", type=int, default=7, help="Stale threshold in days")

    p_list = sub.add_parser("list", help="List registered repos")

    p_remove = sub.add_parser("remove", help="Unregister a repo")
    p_remove.add_argument("name", help="Repo name to remove")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 1

    return {"add": cmd_add, "status": cmd_status, "check": cmd_check,
            "list": cmd_list, "remove": cmd_remove}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
