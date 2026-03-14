#!/usr/bin/env python3
"""Aggregate KPI event records into pass/fail summaries.

Supports:
- JSONL records (one JSON object per line)
- JSON array records
- memu-export style object with `records`, `events`, or `data` arrays
"""

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, Iterable, List, Optional


STATUS_PASS = "pass"
STATUS_FAIL = "fail"


def _parse_dt(value: str) -> Optional[dt.datetime]:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def _extract_records(blob: Any) -> List[Dict[str, Any]]:
    if isinstance(blob, list):
        return [x for x in blob if isinstance(x, dict)]
    if isinstance(blob, dict):
        for key in ("records", "events", "data"):
            val = blob.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
        return [blob]
    return []


def load_records(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        return []

    if raw[0] in "[{":
        try:
            parsed = json.loads(raw)
            return _extract_records(parsed)
        except json.JSONDecodeError:
            # Fallback to JSONL parsing when file starts with "{" but contains many JSON objects.
            pass

    records: List[Dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def normalize_record(rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lane = rec.get("lane") or rec.get("agent") or rec.get("owner") or "unknown"
    kpi = rec.get("kpi") or rec.get("metric") or "unknown_kpi"

    ts_val = rec.get("timestamp") or rec.get("ts") or rec.get("created_at") or rec.get("datetime")
    ts = _parse_dt(str(ts_val)) if ts_val is not None else None

    status = rec.get("status")
    pass_value = rec.get("pass")
    if isinstance(pass_value, bool):
        status_norm = STATUS_PASS if pass_value else STATUS_FAIL
    elif isinstance(status, str):
        status_norm = status.strip().lower()
        if status_norm not in (STATUS_PASS, STATUS_FAIL):
            status_norm = STATUS_FAIL
    else:
        status_norm = STATUS_FAIL

    score = rec.get("score")
    budget = rec.get("budget_usd")
    if budget is None:
        budget = rec.get("spend_usd", rec.get("cost_usd", 0))

    try:
        budget_float = float(budget)
    except (TypeError, ValueError):
        budget_float = 0.0

    return {
        "timestamp": ts,
        "date": ts.date().isoformat() if ts else None,
        "lane": str(lane),
        "kpi": str(kpi),
        "status": status_norm,
        "score": score,
        "budget_usd": budget_float,
    }


def filter_records(records: Iterable[Dict[str, Any]], date: Optional[str], window_days: Optional[int]) -> List[Dict[str, Any]]:
    normalized = [normalize_record(r) for r in records]
    normalized = [r for r in normalized if r is not None]

    if date:
        return [r for r in normalized if r.get("date") == date]

    if window_days and window_days > 0:
        today = dt.date.today()
        start = today - dt.timedelta(days=window_days - 1)

        out: List[Dict[str, Any]] = []
        for r in normalized:
            d = r.get("date")
            if not d:
                continue
            try:
                parsed = dt.date.fromisoformat(d)
            except ValueError:
                continue
            if start <= parsed <= today:
                out.append(r)
        return out

    return normalized


def rollup(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_lane: Dict[str, Dict[str, Any]] = {}

    for rec in records:
        lane = rec["lane"]
        lane_acc = by_lane.setdefault(
            lane,
            {
                "pass_count": 0,
                "fail_count": 0,
                "total": 0,
                "budget_usd": 0.0,
                "kpis": {},
            },
        )
        lane_acc["total"] += 1
        lane_acc["budget_usd"] += rec.get("budget_usd", 0.0)
        if rec["status"] == STATUS_PASS:
            lane_acc["pass_count"] += 1
        else:
            lane_acc["fail_count"] += 1

        kpi = rec["kpi"]
        kpi_acc = lane_acc["kpis"].setdefault(kpi, {"pass": 0, "fail": 0})
        if rec["status"] == STATUS_PASS:
            kpi_acc["pass"] += 1
        else:
            kpi_acc["fail"] += 1

    for lane, lane_acc in by_lane.items():
        lane_acc["status"] = "PASS" if lane_acc["fail_count"] == 0 and lane_acc["total"] > 0 else "FAIL"
        lane_acc["budget_usd"] = round(float(lane_acc["budget_usd"]), 2)

    summary = {
        "record_count": len(records),
        "lanes": len(by_lane),
        "pass_count": sum(v["pass_count"] for v in by_lane.values()),
        "fail_count": sum(v["fail_count"] for v in by_lane.values()),
        "budget_usd": round(sum(v["budget_usd"] for v in by_lane.values()), 2),
    }

    return {"summary": summary, "lanes": by_lane}


class KpiRollupTests(unittest.TestCase):
    def test_jsonl_rollup(self) -> None:
        rows = [
            {"timestamp": "2026-03-02T10:00:00", "lane": "rosie", "kpi": "uptime", "pass": True, "spend_usd": 10},
            {"timestamp": "2026-03-02T11:00:00", "lane": "rosie", "kpi": "mtta", "pass": False, "spend_usd": 5},
        ]
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            for row in rows:
                tmp.write(json.dumps(row) + "\n")
            path = tmp.name
        try:
            records = load_records(path)
            filt = filter_records(records, date="2026-03-02", window_days=None)
            out = rollup(filt)
            self.assertEqual(out["summary"]["record_count"], 2)
            self.assertEqual(out["lanes"]["rosie"]["fail_count"], 1)
        finally:
            os.unlink(path)

    def test_memu_style_payload(self) -> None:
        payload = {
            "records": [
                {"created_at": "2026-03-01T01:00:00Z", "owner": "mack", "metric": "ctr", "status": "pass", "budget_usd": 7}
            ]
        }
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(json.dumps(payload))
            path = tmp.name
        try:
            records = load_records(path)
            filt = filter_records(records, date="2026-03-01", window_days=None)
            out = rollup(filt)
            self.assertEqual(out["summary"]["record_count"], 1)
            self.assertEqual(out["lanes"]["mack"]["status"], "PASS")
        finally:
            os.unlink(path)


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KpiRollupTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate KPI records")
    parser.add_argument("--input", required=False, help="Path to JSONL/JSON input")
    parser.add_argument("--date", help="Filter date YYYY-MM-DD")
    parser.add_argument("--window", type=int, help="Rolling window in days")
    parser.add_argument("--out", help="Write output JSON to file")
    parser.add_argument("--test", action="store_true", help="Run built-in tests")
    args = parser.parse_args()

    if args.test:
        return run_tests()

    if not args.input:
        print(json.dumps({"ok": False, "error": "--input is required unless --test is used"}))
        return 2

    records = load_records(args.input)
    filtered = filter_records(records, args.date, args.window)
    payload = rollup(filtered)
    payload["date"] = args.date
    payload["window_days"] = args.window
    payload["input"] = os.path.abspath(args.input)

    text = json.dumps(payload, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
