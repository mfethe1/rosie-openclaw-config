#!/usr/bin/env python3
"""Regression matrix for memU route aliases + async ingest + strict schema.

Usage:
  python3 memu_server/scripts/regression_matrix.py
"""

from __future__ import annotations

import json
import os
import time
import uuid
import urllib.error
import urllib.request

BASE = os.environ.get("MEMU_URL", "http://localhost:8711").rstrip("/")
TOKEN = os.environ.get("MEMU_API_KEY", "openclaw-memu-local-2026")


def call(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
        body = e.read().decode("utf-8", errors="replace")
        return e.code, json.loads(body) if body else {}


def assert_ok(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}".strip())
    print(f"✅ {name}")


def main() -> None:
    stamp = str(int(time.time()))
    key = f"matrix-{stamp}-{uuid.uuid4().hex[:8]}"

    # Contract discoverability
    status, capabilities = call("GET", "/api/v1/memu/capabilities")
    assert_ok("capabilities", status == 200 and isinstance(capabilities, dict) and capabilities.get("version") == "2.6.0", str(capabilities)[:180])

    # Route matrix: health
    for p in ("/health", "/api/v1/memu/health"):
        status, body = call("GET", p)
        assert_ok(f"health {p}", status == 200 and body.get("status") == "ok", str(body)[:180])

    # Route matrix: write aliases
    payloads = [
        ("/store", {"agent": "regression", "user_id": "regression", "session_id": "s-regression", "category": "general", "key": key + "-direct", "value": "direct route write"}),
        ("/api/v1/memu/store", {"agent_id": "regression", "user_id": "regression", "session_id": "s-regression", "category": "general", "key": key + "-bridge", "content": "bridge route write"}),
        ("/memorize", {"agent_id": "regression", "user_id": "regression", "session_id": "s-regression", "category": "general", "key": key + "-canonical", "content": "canonical route write"}),
    ]
    for path, payload in payloads:
        status, body = call("POST", path, payload)
        assert_ok(f"store {path}", status in (200, 202), str(body)[:180])

    # Route matrix: read aliases
    search_payload = {"agent_id": "regression", "query": key, "limit": 20}
    for p in ("/search", "/retrieve", "/api/v1/memu/search"):
        status, body = call("POST", p, search_payload)
        assert_ok(f"search {p}", status == 200 and body.get("count", 0) >= 1, str(body)[:180])

    # Async ingest matrix
    status, body = call(
        "POST",
        "/api/v1/memu/store",
        {
            "agent_id": "regression",
            "user_id": "regression",
            "session_id": "s-regression",
            "category": "general",
            "key": key + "-async",
            "content": "async route write",
            "async": True,
        },
    )
    assert_ok("async accepted", status == 202, str(body)[:180])
    job_id = body.get("job_id")
    assert_ok("async job id", isinstance(job_id, str) and len(job_id) > 10)

    done = False
    for _ in range(20):
        time.sleep(0.25)
        s, jb = call("GET", f"/api/v1/memu/jobs/{job_id}")
        if s == 200 and jb.get("status") in {"done", "failed"}:
            assert_ok("async job status terminal", True)
            assert_ok("async job done", jb.get("status") == "done", str(jb)[:180])
            done = True
            break
    assert_ok("async job poll", done)

    # Strict schema matrix (only enforce when enabled)
    hs, hb = call("GET", "/api/v1/memu/health")
    strict_enabled = "strict-schema-mode" in (hb.get("features") or [])
    if strict_enabled:
        s1, _ = call("POST", "/api/v1/memu/store", {"agent_id": "regression", "content": "missing strict fields"})
        assert_ok("strict rejects missing user/session", s1 == 400)
        s2, _ = call(
            "POST",
            "/api/v1/memu/store",
            {
                "agent_id": "regression",
                "user_id": "u-regression",
                "session_id": "s-regression",
                "content": "strict accepted",
                "category": "general",
                "key": key + "-strict",
            },
        )
        assert_ok("strict accepts user+session", s2 == 200)
    else:
        print("ℹ️ strict-schema-mode disabled; strict validation checks skipped")

    print("\nPASS: regression matrix complete")


if __name__ == "__main__":
    main()
