import unittest
import os
import gzip
import tempfile
from pathlib import Path

# Import the module to test
import log_rotation

class TestLogRotation(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory and file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = Path(self.temp_dir.name) / "test.log"
        self.test_file_path.write_text("dummy content\n" * 100)
        self.initial_size = self.test_file_path.stat().st_size

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_no_rotation_below_threshold(self):
        """Test that a file smaller than max_size is not rotated."""
        # Threshold is larger than current size
        log_rotation.rotate_file(self.test_file_path, max_size=self.initial_size + 100)
        
        archive_path = self.test_file_path.with_name(self.test_file_path.name + ".1.gz")
        self.assertFalse(archive_path.exists())
        self.assertEqual(self.test_file_path.stat().st_size, self.initial_size)

    def test_rotation_above_threshold(self):
        """Test that a file larger than max_size is rotated and compressed."""
        # Threshold is smaller than current size
        log_rotation.rotate_file(self.test_file_path, max_size=self.initial_size - 10)
        
        archive_path = self.test_file_path.with_name(self.test_file_path.name + ".1.gz")
        self.assertTrue(archive_path.exists())
        
        # Check that original file was truncated
        self.assertEqual(self.test_file_path.stat().st_size, 0)
        
        # Check that compressed content matches original content
        with gzip.open(archive_path, 'rt') as f:
            content = f.read()
        self.assertEqual(content, "dummy content\n" * 100)

    def test_dry_run_no_changes(self):
        """Test that dry_run=True does not rotate the file despite being above threshold."""
        log_rotation.rotate_file(self.test_file_path, max_size=self.initial_size - 10, dry_run=True)
        
        archive_path = self.test_file_path.with_name(self.test_file_path.name + ".1.gz")
        self.assertFalse(archive_path.exists())
        self.assertEqual(self.test_file_path.stat().st_size, self.initial_size)

if __name__ == '__main__':
    unittest.main()
