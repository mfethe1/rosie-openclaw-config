import os
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the script's directory to sys.path so we can import it
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from awesome_memory_tracker import extract_papers, normalize_title, load_state, save_state, build_report

class TestAwesomeMemoryTracker(unittest.TestCase):
    def test_normalize_title(self):
        self.assertEqual(normalize_title("  some title [  "), "some title")
        self.assertEqual(normalize_title("title"), "title")
        self.assertEqual(normalize_title(None), "")

    def test_extract_papers(self):
        md = """
Some introductory text.
- [2026/01] MAGMA: some paper [paper]
- [2025/12] Another paper [paper]
- Not a paper line
- [2026/01] MAGMA: some paper [paper]
        """
        papers = extract_papers(md)
        self.assertEqual(papers, ["MAGMA: some paper", "Another paper"])

    @patch("awesome_memory_tracker.STATE_PATH")
    def test_load_state_success(self, mock_path):
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps({"papers": ["A", "B"]})
        state = load_state()
        self.assertEqual(state["papers"], ["A", "B"])

    @patch("awesome_memory_tracker.STATE_PATH")
    def test_load_state_empty(self, mock_path):
        mock_path.exists.return_value = False
        state = load_state()
        self.assertEqual(state["papers"], [])

    @patch("awesome_memory_tracker.STATE_PATH")
    def test_load_state_corrupt(self, mock_path):
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "invalid json"
        state = load_state()
        self.assertEqual(state["papers"], [])

    @patch("awesome_memory_tracker.STATE_PATH")
    def test_save_state(self, mock_path):
        mock_path.parent.mkdir = MagicMock()
        mock_path.write_text = MagicMock()
        save_state({"test": 1})
        mock_path.parent.mkdir.assert_called_once()
        mock_path.write_text.assert_called_once_with('{\n  "test": 1\n}')

    def test_build_report_with_added(self):
        report = build_report(["New Paper 1"], 10, 9)
        self.assertIn("New Papers Since Last Check", report)
        self.assertIn("- New Paper 1", report)
        self.assertIn("- Current papers tracked: 10", report)

    def test_build_report_no_added(self):
        report = build_report([], 10, 10)
        self.assertIn("No New Papers Detected", report)
        self.assertIn("- Current papers tracked: 10", report)

if __name__ == "__main__":
    unittest.main()
