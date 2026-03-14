#!/usr/bin/env python3
"""Select specialized agent profile by directory (init-deep style).

Rules:
- longest-prefix-wins mapping from directory_agent_map.json
- validates selected agent has 7-10 skills
"""

import argparse
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
MAP_FILE = BASE / "directory_agent_map.json"
CATALOG_FILE = BASE / "agent_catalog.json"


def load_json(p: pathlib.Path):
    return json.loads(p.read_text())


def resolve_agent(cwd: str, mapping: dict) -> str:
    cwd_p = pathlib.Path(cwd).resolve()
    matches = []
    for m in mapping.get("mappings", []):
        mp = pathlib.Path(m["path"]).resolve()
        try:
            cwd_p.relative_to(mp)
            matches.append((len(str(mp)), m["agent"], m.get("reason", ""), str(mp)))
        except Exception:
            continue
    if not matches:
        return mapping.get("default_agent", "core-platform"), "default", ""
    matches.sort(reverse=True)
    _, agent, reason, matched = matches[0]
    return agent, matched, reason


def get_agent_profile(agent_lane: str, catalog: dict):
    for a in catalog.get("agents", []):
        if a.get("lane") == agent_lane:
            return a
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=str(pathlib.Path.cwd()))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.test:
        mapping = {
            "default_agent": "core-platform",
            "mappings": [{"path": "/tmp/a", "agent": "seo"}, {"path": "/tmp", "agent": "marketing"}],
        }
        agent, matched, _ = resolve_agent("/tmp/a/b", mapping)
        assert agent == "seo"
        assert matched.endswith("/tmp/a")
        print("ok")
        return 0

    mapping = load_json(MAP_FILE)
    catalog = load_json(CATALOG_FILE)

    lane, matched, reason = resolve_agent(args.cwd, mapping)
    profile = get_agent_profile(lane, catalog)
    if not profile:
        print(json.dumps({"ok": False, "error": f"No profile for lane={lane}"}))
        return 2

    skills = profile.get("skills", [])
    if not (7 <= len(skills) <= 10):
        print(json.dumps({"ok": False, "error": f"skills count out of range for {lane}", "count": len(skills)}))
        return 3

    out = {
        "ok": True,
        "cwd": str(pathlib.Path(args.cwd).resolve()),
        "lane": lane,
        "matched_prefix": matched,
        "reason": reason,
        "owner": profile.get("owner"),
        "skills": skills,
        "kpi_contract": profile.get("kpi_contract"),
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"lane={lane} owner={out['owner']} matched={matched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
