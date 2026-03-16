import unittest
import tempfile
import os
import sys

# Ensure scripts dir is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from json_error_filter import filter_errors

class TestJsonErrorFilter(unittest.TestCase):
    def setUp(self):
        self.temp_log = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        
    def tearDown(self):
        self.temp_log.close()
        if os.path.exists(self.temp_log.name):
            os.unlink(self.temp_log.name)

    def write_log(self, lines):
        self.temp_log.write('\n'.join(lines))
        self.temp_log.flush()
        self.temp_log.close()

    def test_filter_errors(self):
        lines = [
            "This is a normal log line.",
            "An error occurred while parsing.",
            "Database connection fail.",
            '{"hasError": false}',
            '{"error_code": 0}',
            "Warning: exception in module X",
            '{"status": "ok", "error": null}'
        ]
        self.write_log(lines)
        errors = filter_errors(self.temp_log.name)
        
        self.assertEqual(len(errors), 3)
        self.assertIn("An error occurred while parsing.", errors)
        self.assertIn("Database connection fail.", errors)
        self.assertIn("Warning: exception in module X", errors)
        
if __name__ == '__main__':
    unittest.main()
