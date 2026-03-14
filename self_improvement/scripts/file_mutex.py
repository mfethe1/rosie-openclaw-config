#!/usr/bin/env python3
"""file_mutex.py — Atomic file locking utility for OpenClaw SI scripts.

Usage:
  from file_mutex import file_lock, atomic_write_text
  
  with file_lock("shared-state.json"):
      data = json.loads(Path("shared-state.json").read_text())
      data["updated"] = True
      atomic_write_text("shared-state.json", json.dumps(data))

This prevents lost updates when multiple crons (Rosie, Winnie, Mack, Lenny)
try to update shared-state.json at the exact same time.
"""

import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

def get_lock_path(file_path: str | Path) -> Path:
    """Get the path to the lock file for a given file."""
    path = Path(file_path).resolve()
    # Create lock file in the same directory, but hidden
    return path.with_name(f".{path.name}.lock")

@contextmanager
def file_lock(file_path: str | Path, timeout: float = 60.0, delay: float = 0.1) -> Generator[None, None, None]:
    """Acquire an exclusive lock for file_path using fcntl.
    
    Raises TimeoutError if the lock cannot be acquired within the timeout.
    """
    lock_path = get_lock_path(file_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
    
    try:
        while True:
            try:
                # Try to acquire an exclusive, non-blocking lock
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (IOError, OSError):
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock for {file_path} within {timeout}s")
                time.sleep(delay)
                
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except (IOError, OSError):
            pass


def atomic_write_text(file_path: str | Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to file_path atomically using a temp file + rename.

    Writes to a sibling .tmp file first, then renames into place so
    concurrent readers never see a partially-written file.
    Acquires file_lock before writing so concurrent writers are serialized.
    """
    path = Path(file_path)
    tmp_path = path.with_suffix(".tmp")
    with file_lock(path):
        tmp_path.write_text(content, encoding=encoding)
        tmp_path.replace(path)


if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python file_mutex.py <file_path> [content]")
        print("  With no content arg, acquires lock and exits (smoke test).")
        sys.exit(1)

    target = sys.argv[1]
    if len(sys.argv) >= 3:
        atomic_write_text(target, sys.argv[2])
        print(f"OK: wrote {len(sys.argv[2])} bytes to {target}")
    else:
        with file_lock(target):
            print(f"OK: acquired lock for {target}")
