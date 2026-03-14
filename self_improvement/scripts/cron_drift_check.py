#!/usr/bin/env python3
"""
cron_drift_check.py — Detect crons that are overdue by >1.5x their interval.

Parses `openclaw cron list` table output and flags any cron whose last-run
is more than 1.5x its scheduled interval ago.

Usage: python3 cron_drift_check.py [--json] [--broadcast]
"""

import subprocess
import re
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/Users/harrisonfethe/.openclaw/workspace")
OUTPUTS_DIR = WORKSPACE / "self_improvement" / "outputs"


def is_market_hours_only(schedule_str: str) -> bool:
    """Return True if the cron only runs during market hours (weekday + hour range)."""
    s = schedule_str.strip()
    # Matches patterns like "cron */5 9-16 * * 1-5" or "cron */10 4-9 * * 1-5"
    return bool(re.search(r"\d+-\d+\s+\*\s+\*\s+\d+-\d+", s)) or bool(re.search(r"1-5", s))


def parse_interval(schedule_str: str) -> timedelta | None:
    """Parse schedule string into expected interval timedelta."""
    s = schedule_str.strip()

    # "every Xh" or "every Xm"
    m = re.match(r"every\s+(\d+)([hm])", s)
    if m:
        val, unit = int(m.group(1)), m.group(2)
        if unit == "h":
            return timedelta(hours=val)
        return timedelta(minutes=val)

    # "every Xmin"
    m = re.match(r"every\s+(\d+)\s*min", s)
    if m:
        return timedelta(minutes=int(m.group(1)))

    # cron expression: "cron */X * * * *" (every X minutes)
    m = re.match(r"cron\s+\*/(\d+)\s+", s)
    if m:
        return timedelta(minutes=int(m.group(1)))

    # cron expression: "cron X Y * * *" (specific hour/min = daily)
    m = re.match(r"cron\s+\d+\s+\d+\s+\*\s+\*\s+\*", s)
    if m:
        return timedelta(hours=24)

    # cron: "cron X Y/Z * * *" (every Z hours starting at Y)
    m = re.match(r"cron\s+\d+\s+\*/(\d+)\s+", s)
    if m:
        return timedelta(hours=int(m.group(1)))

    # cron: "cron X Y-Z/W * * *" (every W hours in range Y-Z)
    m = re.match(r"cron\s+\d+\s+\d+-\d+/(\d+)\s+", s)
    if m:
        return timedelta(hours=int(m.group(1)))

    # cron: daily at specific time
    m = re.match(r"cron\s+\d+\s+\d+\s+\*\s+\*\s+", s)
    if m:
        return timedelta(hours=24)

    # cron with weekday filter (1-5): treat as daily for weekday check
    m = re.match(r"cron\s+\d+\s+\d+\s+\*\s+\*\s+\d", s)
    if m:
        return timedelta(hours=24)

    return None


def parse_last_run(last_str: str) -> timedelta | None:
    """Parse 'Xm ago', 'Xh ago', 'Xd ago' into timedelta."""
    s = last_str.strip()
    if s == "-" or not s:
        return None

    m = re.match(r"(\d+)m\s*ago", s)
    if m:
        return timedelta(minutes=int(m.group(1)))

    m = re.match(r"(\d+)h\s*ago", s)
    if m:
        return timedelta(hours=int(m.group(1)))

    m = re.match(r"(\d+)d\s*ago", s)
    if m:
        return timedelta(days=int(m.group(1)))

    m = re.match(r"<1m\s*ago", s)
    if m:
        return timedelta(minutes=0)

    return None


def run():
    import time
    output = ""
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["openclaw", "cron", "list"],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout + result.stderr
            break
        except subprocess.TimeoutExpired as e:
            if attempt == 2:
                print(f"[ERROR] openclaw cron list timed out: {e}")
                return [], []
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] openclaw cron list failed: {e}")
            return [], []

    lines = output.split("\n")

    # Find the header line to get column positions
    header_idx = None
    col_positions = {}
    for i, line in enumerate(lines):
        if line.strip().startswith("ID") and "Name" in line and "Schedule" in line:
            header_idx = i
            # Find column start positions
            for col_name in ["ID", "Name", "Schedule", "Next", "Last", "Status", "Target", "Agent"]:
                pos = line.find(col_name)
                if pos >= 0:
                    col_positions[col_name] = pos
            break

    if header_idx is None or "ID" not in col_positions:
        print("[WARN] Could not find header line in cron list output")
        return [], []

    # Column extraction using positions
    cols = sorted(col_positions.items(), key=lambda x: x[1])

    def extract_col(line: str, col_name: str) -> str:
        """Extract column value using header positions."""
        idx = next((i for i, (n, _) in enumerate(cols) if n == col_name), None)
        if idx is None:
            return ""
        start = cols[idx][1]
        end = cols[idx + 1][1] if idx + 1 < len(cols) else len(line)
        return line[start:end].strip() if start < len(line) else ""

    flagged = []
    all_parsed = []

    for line in lines[header_idx + 1:]:
        # Data rows start with a UUID
        if not re.match(r"[0-9a-f]{8}-", line.strip()):
            continue

        cron_id = extract_col(line, "ID").strip()
        name = extract_col(line, "Name").strip().rstrip(".")
        schedule = extract_col(line, "Schedule").strip().rstrip(".")
        last_str = extract_col(line, "Last").strip()
        status = extract_col(line, "Status").strip()

        if not cron_id:
            continue

        interval = parse_interval(schedule)
        last_ago = parse_last_run(last_str)

        entry = {
            "id": cron_id[:8],
            "name": name[:50],
            "schedule": schedule[:40],
            "last": last_str,
            "status": status,
            "interval_min": interval.total_seconds() / 60 if interval else None,
            "last_ago_min": last_ago.total_seconds() / 60 if last_ago else None,
        }
        all_parsed.append(entry)

        if interval and last_ago:
            ratio = last_ago / interval
            entry["drift_ratio"] = round(ratio, 2)

            # Skip market-hours-only crons when outside market hours (weekdays 9:25-16:05 ET)
            now = datetime.now()
            is_market_time = now.weekday() < 5 and 4 <= now.hour <= 16
            if is_market_hours_only(schedule) and not is_market_time:
                entry["skipped_market_hours"] = True
                continue

            if ratio > 1.5:
                entry["flagged"] = True
                flagged.append(entry)

    return flagged, all_parsed


def main():
    json_mode = "--json" in sys.argv

    flagged, all_parsed = run()

    if json_mode:
        print(json.dumps({"flagged": flagged, "total_parsed": len(all_parsed)}, indent=2))
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if flagged:
        print(f"⚠️  CRON DRIFT DETECTED at {now}")
        print(f"   {len(flagged)} cron(s) overdue by >1.5x their interval:\n")
        for f in flagged:
            print(f"   {f['id']} | {f['name']:50s} | drift={f.get('drift_ratio','?')}x | last={f['last']} | status={f['status']}")
    else:
        print(f"✅ No cron drift detected at {now} ({len(all_parsed)} crons checked)")

    # Write output file
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = OUTPUTS_DIR / f"cron-drift-{date_str}.md"
    with open(out_path, "a") as fp:
        fp.write(f"\n## Drift Check — {now}\n")
        if flagged:
            fp.write(f"**{len(flagged)} crons overdue:**\n")
            for f in flagged:
                fp.write(f"- `{f['id']}` {f['name']} — drift={f.get('drift_ratio','?')}x, last={f['last']}, status={f['status']}\n")
        else:
            fp.write(f"✅ All {len(all_parsed)} crons on schedule.\n")


if __name__ == "__main__":
    main()
