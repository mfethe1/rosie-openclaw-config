import json
import os
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from si_benchmark_gate import check_memu, freshness_check, newest_output

class TestSIBenchmarkGate(unittest.TestCase):
    @patch("si_benchmark_gate.urllib.request.urlopen")
    def test_check_memu_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = check_memu("http://dummy_url", 1.0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["status_field"], "ok")
        self.assertIn("latency_ms", result)

    @patch("si_benchmark_gate.urllib.request.urlopen")
    def test_check_memu_failure_status(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.read.return_value = json.dumps({"status": "error"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = check_memu("http://dummy_url", 1.0)
        self.assertFalse(result["ok"])

    @patch("si_benchmark_gate.urllib.request.urlopen")
    def test_check_memu_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        result = check_memu("http://dummy_url", 1.0)
        self.assertFalse(result["ok"])
        self.assertIn("error", result)
        self.assertIn("Connection refused", result["error"])

    def test_freshness_check_pass(self):
        now = time.time()
        ts = now - 3600 # 1 hour ago
        result = freshness_check("test_pass", ts, 2.0, "source.md")
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["age_hours"], 1.0, places=1)

    def test_freshness_check_fail(self):
        now = time.time()
        ts = now - (3600 * 3) # 3 hours ago
        result = freshness_check("test_fail", ts, 2.0, "source.md")
        self.assertFalse(result["ok"])
        self.assertAlmostEqual(result["age_hours"], 3.0, places=1)

    def test_freshness_check_missing(self):
        result = freshness_check("test_missing", None, 2.0, "source.md")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing")

    def test_newest_output_with_tmpdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_dir = Path(tmpdir)
            p1 = outputs_dir / "2026-03-15-10-mack.md"
            p1.write_text("old")
            os.utime(p1, (100, 100))

            p2 = outputs_dir / "2026-03-15-12-mack.md"
            p2.write_text("new")
            os.utime(p2, (200, 200))

            newest_file, newest_ts = newest_output(outputs_dir)
            self.assertEqual(newest_file.name, "2026-03-15-12-mack.md")
            self.assertEqual(newest_ts, 200.0)

if __name__ == "__main__":
    unittest.main()
