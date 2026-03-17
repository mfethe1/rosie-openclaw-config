import os
import time
import tempfile
import threading
import json
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import file_mutex

class TestFileMutex(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.test_file = self.temp_path / "test_state.json"
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_lock_acquisition(self):
        """Test that file_lock can be acquired and released cleanly."""
        with file_mutex.file_lock(self.test_file):
            lock_path = file_mutex.get_lock_path(self.test_file)
            self.assertTrue(lock_path.exists())
            
    def test_file_lock_timeout(self):
        """Test that file_lock raises TimeoutError if lock is held."""
        def hold_lock():
            with file_mutex.file_lock(self.test_file):
                time.sleep(0.5)

        thread = threading.Thread(target=hold_lock)
        thread.start()
        
        # Wait for thread to acquire lock
        time.sleep(0.1)
        
        with self.assertRaises(TimeoutError):
            with file_mutex.file_lock(self.test_file, timeout=0.1, delay=0.05):
                pass
                
        thread.join()

    def test_atomic_write_text(self):
        """Test atomic write creates the file correctly."""
        content = json.dumps({"test": "data"})
        file_mutex.atomic_write_text(self.test_file, content)
        
        self.assertTrue(self.test_file.exists())
        self.assertEqual(self.test_file.read_text(), content)

    def test_concurrent_atomic_writes(self):
        """Test that multiple threads writing don't corrupt the file."""
        # Initialize the file
        initial_data = {"count": 0}
        file_mutex.atomic_write_text(self.test_file, json.dumps(initial_data))
        
        def worker():
            with file_mutex.file_lock(self.test_file):
                data = json.loads(self.test_file.read_text())
                data["count"] += 1
                # Must use atomic_write_text to avoid reading empty mid-write
                file_mutex.atomic_write_text(self.test_file, json.dumps(data))

        # Run 10 threads concurrently
        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        final_data = json.loads(self.test_file.read_text())
        self.assertEqual(final_data["count"], 10)

if __name__ == "__main__":
    unittest.main()
