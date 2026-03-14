#!/usr/bin/env python3
"""Validate required sections in an intent packet markdown file."""

import argparse
import json
import os
import re
import sys
import tempfile
import unittest
from typing import Dict, List


REQUIRED_SECTIONS = [
    "objective",
    "repo map",
    "docs & references",
    "constraints",
    "definition of done",
    "test plan",
    "rollback plan",
    "budget guard",
    "owner sign-off",
]


def _normalize_heading(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"^[0-9]+\)\s*", "", s)
    s = re.sub(r"^[0-9]+\.\s*", "", s)
    s = re.sub(r"\s*\*\(required\)\*\s*$", "", s)
    s = re.sub(r"\s*\(required\)\s*$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" :-")


def extract_headings(markdown_text: str) -> List[str]:
    headings: List[str] = []
    for line in markdown_text.splitlines():
        line = line.strip()
        if line.startswith("##"):
            raw = line.lstrip("#").strip()
            headings.append(_normalize_heading(raw))
    return headings


def validate_packet(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    headings = extract_headings(text)

    def _has_section(required: str) -> bool:
        for found in headings:
            if required == found or required in found or found in required:
                return True
        return False

    missing = [sec for sec in REQUIRED_SECTIONS if not _has_section(sec)]

    return {
        "ok": len(missing) == 0,
        "packet": os.path.abspath(path),
        "required_sections": REQUIRED_SECTIONS,
        "found_sections": headings,
        "missing_sections": missing,
    }


class IntentPacketGateTests(unittest.TestCase):
    def test_complete_packet(self) -> None:
        content = "\n".join(
            [
                "## 1) Objective *(required)*",
                "## 2) Repo Map *(required)*",
                "## 3) Docs & References *(required)*",
                "## 4) Constraints *(required)*",
                "## 5) Definition of Done (DoD) *(required)*",
                "## 6) Test Plan *(required)*",
                "## 7) Rollback Plan *(required)*",
                "## 8) Budget Guard *(required)*",
                "## 9) Owner Sign-off *(required)*",
            ]
        )
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            path = tmp.name
        try:
            result = validate_packet(path)
            self.assertTrue(result["ok"])
            self.assertEqual(result["missing_sections"], [])
        finally:
            os.unlink(path)

    def test_missing_sections(self) -> None:
        content = "## 1) Objective\n## 2) Repo Map\n"
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            path = tmp.name
        try:
            result = validate_packet(path)
            self.assertFalse(result["ok"])
            self.assertIn("constraints", result["missing_sections"])
        finally:
            os.unlink(path)


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IntentPacketGateTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate required sections in intent packets")
    parser.add_argument("--packet", help="Path to markdown intent packet")
    parser.add_argument("--test", action="store_true", help="Run built-in tests")
    args = parser.parse_args()

    if args.test:
        return run_tests()

    if not args.packet:
        print(json.dumps({"ok": False, "error": "--packet is required unless --test is used"}))
        return 2

    result = validate_packet(args.packet)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
