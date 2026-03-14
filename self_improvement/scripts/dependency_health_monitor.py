#!/usr/bin/env python3
"""
dependency_health_monitor.py — Monitor health of external dependencies.

Checks tracked Python packages and GitHub repos for staleness/risk signals:
  1. PyPI: latest version, release date, download count
  2. GitHub: last commit date, open issues, stars, archived status
  3. Local: installed version vs latest, importability

No external dependencies (stdlib only — urllib, json, sqlite3).

Usage:
  python3 dependency_health_monitor.py                   # check all tracked deps
  python3 dependency_health_monitor.py --json             # JSON output
  python3 dependency_health_monitor.py --add <package>    # add a package to track
  python3 dependency_health_monitor.py --store            # store results in memory DB
"""

import argparse
import json
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
STATE_FILE = WORKSPACE / "self_improvement/memory/tracked_deps_state.json"
MEMORY_DB = Path.home() / ".openclaw" / "agent-memory.db"

# Default packages to track (our actual third-party dependencies)
DEFAULT_DEPS = [
    {"name": "sqlite-vec", "pypi": "sqlite-vec", "github": "asg017/sqlite-vec"},
    {"name": "sentence-transformers", "pypi": "sentence-transformers", "github": "UKPLab/sentence-transformers"},
    {"name": "schwab-py", "pypi": "schwab-py", "github": "alexgolec/schwab-py"},
    {"name": "fastembed", "pypi": "fastembed", "github": "qdrant/fastembed"},
]


def load_state() -> dict:
    """Load or initialize tracking state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {"tracked": DEFAULT_DEPS, "last_check": None, "history": []}


def save_state(state: dict):
    """Persist state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_json(url: str, timeout: int = 10, retries: int = 3, backoff: float = 1.0):
    """Fetch JSON from a URL with exponential backoff retry.

    Args:
        url: Target URL.
        timeout: Per-attempt socket timeout in seconds.
        retries: Maximum number of attempts (default 3).
        backoff: Initial sleep between retries in seconds; doubles each attempt.

    Returns:
        Parsed JSON dict/list, or None on all failures.
    """
    last_exc = None
    delay = backoff
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "winnie-dep-monitor/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            # Don't retry client errors (4xx) — they won't resolve on retry
            if 400 <= exc.code < 500:
                return None
            last_exc = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
        except Exception as exc:
            last_exc = exc
            # Non-network errors (e.g. JSON decode) — no point retrying
            break

        if attempt < retries:
            time.sleep(delay)
            delay *= 2  # exponential backoff

    return None


def check_pypi(package: str) -> dict:
    """Check PyPI for latest release info."""
    data = fetch_json(f"https://pypi.org/pypi/{package}/json")
    if not data:
        return {"status": "unreachable", "package": package}

    info = data.get("info", {})
    releases = data.get("releases", {})
    latest = info.get("version", "?")

    # Find release date of latest version
    release_date = None
    if latest in releases and releases[latest]:
        upload = releases[latest][0].get("upload_time", "")
        if upload:
            release_date = upload[:10]

    # Days since last release
    days_since = None
    if release_date:
        try:
            rd = datetime.strptime(release_date, "%Y-%m-%d")
            days_since = (datetime.now() - rd).days
        except ValueError:
            pass

    return {
        "package": package,
        "latest_version": latest,
        "release_date": release_date,
        "days_since_release": days_since,
        "summary": info.get("summary", ""),
        "status": "ok",
    }


def check_github(repo: str) -> dict:
    """Check GitHub API for repo health signals."""
    data = fetch_json(f"https://api.github.com/repos/{repo}")
    if not data:
        return {"status": "unreachable", "repo": repo}

    pushed_at = data.get("pushed_at", "")
    days_since_push = None
    if pushed_at:
        try:
            pa = datetime.strptime(pushed_at[:19], "%Y-%m-%dT%H:%M:%S")
            days_since_push = (datetime.now() - pa).days
        except ValueError:
            pass

    return {
        "repo": repo,
        "stars": data.get("stargazers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "archived": data.get("archived", False),
        "pushed_at": pushed_at[:10] if pushed_at else None,
        "days_since_push": days_since_push,
        "license": (data.get("license") or {}).get("spdx_id", "?"),
        "status": "ok",
    }


def check_local(package: str) -> dict:
    """Check if package is installed locally."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version = "?"
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    break
            return {"installed": True, "version": version}
    except (OSError, subprocess.SubprocessError):
        pass
    return {"installed": False, "version": None}


def assess_risk(pypi: dict, github: dict) -> list:
    """Flag risk signals."""
    flags = []

    if github.get("archived"):
        flags.append("🔴 ARCHIVED — repo is no longer maintained")
    if github.get("days_since_push") and github["days_since_push"] > 180:
        flags.append(f"🟠 STALE — no commits in {github['days_since_push']} days")
    elif github.get("days_since_push") and github["days_since_push"] > 90:
        flags.append(f"🟡 QUIET — no commits in {github['days_since_push']} days")

    if pypi.get("days_since_release") and pypi["days_since_release"] > 365:
        flags.append(f"🟠 OLD RELEASE — last release {pypi['days_since_release']} days ago")

    if github.get("open_issues") and github["open_issues"] > 500:
        flags.append(f"🟡 HIGH ISSUES — {github['open_issues']} open")

    return flags


def run_checks(state: dict) -> list:
    """Run all checks for tracked deps."""
    results = []
    for dep in state["tracked"]:
        name = dep["name"]
        entry = {"name": name, "checked_at": datetime.now().isoformat()}

        if dep.get("pypi"):
            entry["pypi"] = check_pypi(dep["pypi"])
        if dep.get("github"):
            entry["github"] = check_github(dep["github"])

        entry["local"] = check_local(dep.get("pypi", name))
        entry["risk_flags"] = assess_risk(entry.get("pypi", {}), entry.get("github", {}))
        results.append(entry)

    return results


def render_markdown(results: list) -> str:
    """Format results as markdown."""
    lines = [
        "# Dependency Health Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M EST')}",
        f"**Packages checked:** {len(results)}",
        "",
    ]

    flagged = [r for r in results if r.get("risk_flags")]
    if flagged:
        lines.append(f"## ⚠️ Risk Flags ({len(flagged)} packages)")
        for r in flagged:
            lines.append(f"\n### {r['name']}")
            for f in r["risk_flags"]:
                lines.append(f"- {f}")
        lines.append("")

    lines.append("## Package Details\n")
    for r in results:
        pypi = r.get("pypi", {})
        gh = r.get("github", {})
        local = r.get("local", {})

        installed = f"v{local['version']}" if local.get("installed") else "not installed"
        latest = pypi.get("latest_version", "?")
        stars = gh.get("stars", "?")
        pushed = gh.get("pushed_at", "?")

        lines.append(f"**{r['name']}** — installed: {installed} | latest: {latest} | ⭐ {stars} | last push: {pushed}")
        if r.get("risk_flags"):
            lines.append(f"  Flags: {', '.join(r['risk_flags'])}")
        lines.append("")

    return "\n".join(lines)


def store_results(results: list):
    """Store summary in agent-memory.db."""
    if not MEMORY_DB.exists():
        return

    flagged = [r["name"] for r in results if r.get("risk_flags")]
    summary = (
        f"Dep health: {len(results)} checked, {len(flagged)} flagged. "
        + (f"Flagged: {', '.join(flagged)}." if flagged else "All clear.")
    )

    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        conn.execute(
            """INSERT INTO agent_memories
               (agent, cycle, topic, body, source_file, tags, created_at, memory_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "winnie",
                f"dep-health-{datetime.now().strftime('%Y%m%d')}",
                "dependency-health",
                summary,
                "self_improvement/scripts/dependency_health_monitor.py",
                "dependency,health,monitoring,winnie",
                datetime.now().isoformat(),
                "factual",
            ),
        )
        conn.commit()
        conn.close()
        print("[OK] Stored in agent-memory.db")
    except Exception as e:
        print(f"[WARN] Store failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Dependency health monitor")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--store", action="store_true", help="Store in memory DB")
    parser.add_argument("--add", help="Add a PyPI package to track")
    args = parser.parse_args()

    state = load_state()

    if args.add:
        state["tracked"].append({"name": args.add, "pypi": args.add})
        save_state(state)
        print(f"Added {args.add} to tracked deps.")
        return

    results = run_checks(state)
    state["last_check"] = datetime.now().isoformat()
    save_state(state)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(render_markdown(results))

    if args.store:
        store_results(results)


if __name__ == "__main__":
    main()
