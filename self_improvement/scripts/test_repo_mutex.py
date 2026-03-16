import unittest
import os
import sqlite3
import time
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import sys

# Import the module to test
import repo_mutex

class TestRepoMutex(unittest.TestCase):
    def setUp(self):
        # Use an isolated in-memory DB or temporary file for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        
        # Patch the DB_PATH in repo_mutex
        self.patcher = patch('repo_mutex.DB_PATH', self.temp_db_path)
        self.patcher.start()
        
        repo_mutex.init_db()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_acquire_and_release_lock(self):
        """Test acquiring and properly releasing a lock."""
        repo_path = "/tmp/test_repo"
        with repo_mutex.repo_lock(repo_path, timeout=5):
            # Check lock exists in db
            with sqlite3.connect(self.temp_db_path) as conn:
                cursor = conn.execute('SELECT pid FROM repo_locks WHERE repo_path = ?', (repo_path,))
                row = cursor.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], os.getpid())
                
        # Check lock was released
        with sqlite3.connect(self.temp_db_path) as conn:
            cursor = conn.execute('SELECT pid FROM repo_locks WHERE repo_path = ?', (repo_path,))
            row = cursor.fetchone()
            self.assertIsNone(row)

    def test_timeout_when_locked(self):
        """Test that attempting to lock an already locked repo raises TimeoutError."""
        repo_path = "/tmp/test_repo_locked"
        
        # Manually lock it with another PID
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute('INSERT INTO repo_locks (repo_path, locked_at, pid) VALUES (?, ?, ?)',
                         (repo_path, time.time(), 99999))
            conn.commit()
            
        with self.assertRaises(TimeoutError):
            with repo_mutex.repo_lock(repo_path, timeout=1):
                pass

    def test_stale_lock_override(self):
        """Test that a stale lock (older than 7200s) is overridden."""
        repo_path = "/tmp/test_repo_stale"
        
        # Manually lock it with an old timestamp
        stale_time = time.time() - 8000
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute('INSERT INTO repo_locks (repo_path, locked_at, pid) VALUES (?, ?, ?)',
                         (repo_path, stale_time, 99999))
            conn.commit()
            
        # Should not raise TimeoutError because the lock is stale
        with repo_mutex.repo_lock(repo_path, timeout=1):
            with sqlite3.connect(self.temp_db_path) as conn:
                cursor = conn.execute('SELECT pid FROM repo_locks WHERE repo_path = ?', (repo_path,))
                row = cursor.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], os.getpid())

if __name__ == '__main__':
    unittest.main()
