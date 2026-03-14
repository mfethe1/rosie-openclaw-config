#!/usr/bin/env python3
"""
archive_old_outputs.py — Automated archival of cycle outputs.

Archives `self_improvement/outputs/` files older than 7 days into an `archive/` folder,
ensuring the main outputs directory stays clean for the change monitor and daily summary.
"""

import sys
import datetime
from pathlib import Path
import shutil

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
OUTPUTS_DIR = WORKSPACE / "self_improvement" / "outputs"
ARCHIVE_DIR = OUTPUTS_DIR / "archive"

def main():
    if not OUTPUTS_DIR.exists():
        print(f"Outputs directory not found: {OUTPUTS_DIR}")
        return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    now = datetime.datetime.now()
    threshold = now - datetime.timedelta(days=7)
    
    archived_count = 0
    for file_path in OUTPUTS_DIR.glob("*.md"):
        # Ignore subdirectories and the archive dir itself
        if not file_path.is_file():
            continue
            
        mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
        if mtime < threshold:
            dest = ARCHIVE_DIR / file_path.name
            shutil.move(str(file_path), str(dest))
            archived_count += 1
            print(f"Archived: {file_path.name} (mtime: {mtime.strftime('%Y-%m-%d')})")
            
    print(f"Archival complete. {archived_count} files moved to archive.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
