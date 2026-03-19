import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d026_hashline_audit

class TestD026HashlineAudit(unittest.TestCase):
    @patch('d026_hashline_audit.subprocess.run')
    def test_run_cmd_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success_output"
        mock_run.return_value = mock_result
        
        output = d026_hashline_audit.run_cmd("some command")
        self.assertEqual(output, "success_output")
        mock_run.assert_called_once()

    @patch('d026_hashline_audit.sys.exit')
    @patch('d026_hashline_audit.subprocess.run')
    def test_run_cmd_failure(self, mock_run, mock_exit):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error_message"
        mock_run.return_value = mock_result
        
        d026_hashline_audit.run_cmd("failing command")
        mock_exit.assert_called_once_with(1)

    @patch('d026_hashline_audit.run_cmd')
    def test_main_no_matches(self, mock_run_cmd):
        mock_run_cmd.return_value = json.dumps({"jobs": []})
        
        captured_out = StringIO()
        sys.stdout = captured_out
        try:
            d026_hashline_audit.main()
        finally:
            sys.stdout = sys.__stdout__
            
        self.assertIn("Jobs scanned: 0, Matches: 0, Updated: 0", captured_out.getvalue())
        mock_run_cmd.assert_called_once_with("openclaw cron list --json --all")

    @patch('d026_hashline_audit.run_cmd')
    def test_main_with_matches_and_updates(self, mock_run_cmd):
        mock_run_cmd.side_effect = [
            json.dumps({"jobs": [
                {
                    "id": "job1",
                    "name": "Test Job",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Use hashline_edit for this."
                    }
                }
            ]}),
            "update_success"
        ]
        
        captured_out = StringIO()
        sys.stdout = captured_out
        try:
            d026_hashline_audit.main()
        finally:
            sys.stdout = sys.__stdout__
            
        output = captured_out.getvalue()
        self.assertIn("Match found in job: job1 (Test Job)", output)
        self.assertIn("Missing hashline_edit flag. Setting it...", output)
        self.assertIn("Jobs scanned: 1, Matches: 1, Updated: 1", output)
        self.assertEqual(mock_run_cmd.call_count, 2)

    @patch('d026_hashline_audit.sys.exit')
    @patch('d026_hashline_audit.run_cmd')
    def test_main_json_parse_error(self, mock_run_cmd, mock_exit):
        mock_exit.side_effect = SystemExit
        mock_run_cmd.return_value = "invalid json"
        
        with self.assertRaises(SystemExit):
            d026_hashline_audit.main()
        mock_exit.assert_called_once_with(1)

if __name__ == '__main__':
    unittest.main()
