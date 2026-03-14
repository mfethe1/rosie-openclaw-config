#!/usr/bin/env python3
"""Lint agent skill counts and KPI contract links.

Rules:
- Fail if any agent has fewer than 7 skills.
- Fail if any agent has more than 10 skills.
- Fail if any agent is missing a KPI contract link or the linked file does not exist.
"""

import argparse
import json
import os
import sys
import tempfile
import unittest
from typing import Dict, List, Tuple


DEFAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_CATALOG = os.path.join(DEFAULT_ROOT, "agent_catalog.json")


def load_catalog(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def lint_catalog(catalog: Dict, base_dir: str) -> Tuple[List[Dict], List[Dict]]:
    errors: List[Dict] = []
    results: List[Dict] = []

    agents = catalog.get("agents", [])
    for agent in agents:
        lane = agent.get("lane", "<unknown>")
        skills = agent.get("skills", [])
        skill_count = len(skills) if isinstance(skills, list) else 0
        contract = agent.get("kpi_contract")

        lane_errors: List[str] = []
        if skill_count < 7:
            lane_errors.append("skill_count_below_7")
        if skill_count > 10:
            lane_errors.append("skill_count_exceeds_10")

        if not contract:
            lane_errors.append("missing_kpi_contract_link")
            contract_exists = False
            contract_path = None
        else:
            contract_path = os.path.join(base_dir, contract)
            contract_exists = os.path.exists(contract_path)
            if not contract_exists:
                lane_errors.append("kpi_contract_not_found")

        record = {
            "lane": lane,
            "skill_count": skill_count,
            "kpi_contract": contract,
            "kpi_contract_exists": contract_exists,
            "errors": lane_errors,
        }
        results.append(record)

        for err in lane_errors:
            errors.append({"lane": lane, "error": err})

    return results, errors


class SkillCountLintTests(unittest.TestCase):
    def test_passing_catalog(self) -> None:
        catalog = {
            "agents": [
                {
                    "lane": "core",
                    "skills": ["a", "b", "c", "d", "e", "f", "g"],
                    "kpi_contract": "kpi_contracts/rosie.json",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            kpidir = os.path.join(tmp, "kpi_contracts")
            os.makedirs(kpidir)
            with open(os.path.join(kpidir, "rosie.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            results, errors = lint_catalog(catalog, tmp)
        self.assertEqual(len(errors), 0)
        self.assertEqual(results[0]["skill_count"], 7)

    def test_too_many_skills_and_missing_contract(self) -> None:
        catalog = {
            "agents": [
                {
                    "lane": "core",
                    "skills": [str(i) for i in range(11)],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            _, errors = lint_catalog(catalog, tmp)
        codes = sorted([e["error"] for e in errors])
        self.assertIn("skill_count_exceeds_10", codes)
        self.assertIn("missing_kpi_contract_link", codes)

    def test_too_few_skills(self) -> None:
        catalog = {
            "agents": [
                {
                    "lane": "core",
                    "skills": ["a", "b", "c"],
                    "kpi_contract": "kpi_contracts/rosie.json",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            kpidir = os.path.join(tmp, "kpi_contracts")
            os.makedirs(kpidir)
            with open(os.path.join(kpidir, "rosie.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            _, errors = lint_catalog(catalog, tmp)
        codes = sorted([e["error"] for e in errors])
        self.assertIn("skill_count_below_7", codes)


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SkillCountLintTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint agent skill counts and KPI links")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, help="Path to agent catalog JSON")
    parser.add_argument("--test", action="store_true", help="Run built-in tests")
    args = parser.parse_args()

    if args.test:
        return run_tests()

    catalog_path = os.path.abspath(args.catalog)
    base_dir = os.path.dirname(catalog_path)

    try:
        catalog = load_catalog(catalog_path)
    except Exception as exc:  # pragma: no cover
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

    results, errors = lint_catalog(catalog, base_dir)
    output = {
        "ok": len(errors) == 0,
        "catalog": catalog_path,
        "checked_agents": len(results),
        "results": results,
        "errors": errors,
    }
    print(json.dumps(output, indent=2))
    return 0 if len(errors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
