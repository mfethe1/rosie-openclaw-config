import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Generator

DB_PATH = os.path.expanduser('~/.openclaw/workspace/repo_mutex.db')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS repo_locks (
                repo_path TEXT PRIMARY KEY,
                locked_at REAL,
                pid INTEGER
            )
        ''')
        conn.commit()

@contextmanager
def repo_lock(repo_path: str, timeout: int = 60) -> Generator[None, None, None]:
    init_db()
    start_time = time.time()
    
    while True:
        try:
            with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
                conn.isolation_level = 'EXCLUSIVE'
                conn.execute('BEGIN EXCLUSIVE')
                cursor = conn.execute('SELECT locked_at, pid FROM repo_locks WHERE repo_path = ?', (repo_path,))
                row = cursor.fetchone()
                
                if row:
                    locked_at, pid = row
                    if time.time() - locked_at > 7200:
                        pass # Stale
                    else:
                        conn.rollback()
                        if time.time() - start_time > timeout:
                            raise TimeoutError(f"Could not acquire lock for repo {repo_path}")
                        time.sleep(1)
                        continue
                        
                conn.execute('INSERT OR REPLACE INTO repo_locks (repo_path, locked_at, pid) VALUES (?, ?, ?)',
                             (repo_path, time.time(), os.getpid()))
                conn.commit()
                break
        except sqlite3.OperationalError:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Could not acquire SQLite exclusive lock for {repo_path}")
            time.sleep(1)

    try:
        yield
    finally:
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            conn.execute('DELETE FROM repo_locks WHERE repo_path = ? AND pid = ?', (repo_path, os.getpid()))
            conn.commit()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        repo = sys.argv[1]
        print(f"Acquiring lock for {repo}...")
        with repo_lock(repo, timeout=5):
            print(f"Lock acquired. Working on {repo}...")
            time.sleep(2)
        print("Lock released.")
