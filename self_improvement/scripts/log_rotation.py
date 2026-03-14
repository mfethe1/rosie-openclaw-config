#!/usr/bin/env python3
"""log_rotation.py

Rotates large .jsonl or .log files in the workspace to prevent disk exhaustion.
Threshold: 10MB. Keeps 1 compressed archive (.gz) of the previous rotation.
"""

import os
import gzip
import shutil
import glob
import argparse
from pathlib import Path

MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB default

def rotate_file(filepath: Path, max_size: int = MAX_SIZE_BYTES, dry_run: bool = False):
    if not filepath.exists() or filepath.stat().st_size < max_size:
        return
    
    archive_path = filepath.with_name(filepath.name + ".1.gz")
    print(f"Rotating {filepath} ({(filepath.stat().st_size/1024/1024):.2f} MB) -> {archive_path}")
    
    if dry_run:
        return

    with open(filepath, 'rb') as f_in:
        with gzip.open(archive_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # Truncate original file instead of deleting to preserve file descriptors if tailing
    with open(filepath, 'w') as f:
        pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print what would be rotated")
    ap.add_argument("--size-mb", type=float, default=10.0, help="Rotation threshold in MB")
    args = ap.parse_args()

    max_size = int(args.size_mb * 1024 * 1024)
    workspace = Path(__file__).resolve().parent.parent.parent

    # Patterns to watch for rotation
    patterns = [
        "self_improvement/memory/*.jsonl",
        "self_improvement/outputs/*.jsonl",
        "self_improvement/logs/*.log",
        "memu_server/*.jsonl"
    ]
    
    for pattern in patterns:
        for match in glob.glob(str(workspace / pattern)):
            rotate_file(Path(match), max_size, args.dry_run)

if __name__ == "__main__":
    main()
