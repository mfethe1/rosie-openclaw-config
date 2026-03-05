from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

app = FastAPI(title="Dexcom CGM Chat Hub")
DATA_PATH = Path(os.getenv("DATA_PATH", "./data/readings.json"))
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_readings() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text())


def _save_readings(rows: list[dict]) -> None:
    DATA_PATH.write_text(json.dumps(rows, indent=2))


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "dexcom-cgm-chat"}


@app.get("/dexcom/callback")
def dexcom_callback(code: str) -> dict:
    # Token exchange intentionally stubbed until credentials are set.
    return {
        "ok": True,
        "message": "Auth code received. Token exchange will run once credentials are configured.",
        "code_preview": f"{code[:6]}..." if code else None,
    }


@app.get("/readings")
def readings() -> dict:
    return {"items": _load_readings()[-50:]}


@app.post("/chat")
def chat(payload: dict) -> dict:
    question = (payload or {}).get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    rows = _load_readings()
    latest = rows[-1] if rows else None
    if not latest:
        return {
            "answer": "No Dexcom readings are loaded yet. Connect OAuth and start sync, then ask again.",
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "answer": (
            f"Latest glucose is {latest.get('value')} mg/dL at {latest.get('timestamp')}. "
            "I can also summarize trend, highs/lows, and overnight patterns once more samples are synced."
        ),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/dev/add-reading")
def dev_add_reading(payload: dict) -> dict:
    value = payload.get("value")
    timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    if value is None:
        raise HTTPException(status_code=400, detail="value is required")

    rows = _load_readings()
    rows.append({"value": value, "timestamp": timestamp})
    _save_readings(rows)
    return {"ok": True, "count": len(rows)}
