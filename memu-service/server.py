#!/usr/bin/env python3
"""
memU API Server - Lightweight local deployment for team agent memory.
Uses conversation file storage for persistence and adds semantic capabilities.
Endpoints include:
- POST /memorize, POST /retrieve, POST /store, POST /search, GET /health
- POST /semantic-search (new)
- POST /consolidate (new)
- POST /tasks, GET /tasks, PATCH /tasks/{id} (new)
"""

import json
import math
import os
import sys
import uuid
import traceback
import threading
import hashlib
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

# Ensure we can import memu
VENV_SITE = Path(__file__).parent.parent / "memu-venv/lib/python3.13/site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from fastapi import Security, Depends
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name='Authorization', auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    expected = os.getenv('MEMU_API_KEY', 'openclaw-memu-local-2026')
    if not api_key:
        raise HTTPException(status_code=401, detail='Unauthorized: missing')
    token = api_key.replace('Bearer ', '')
    if token != expected:
        raise HTTPException(status_code=403, detail='Unauthorized: invalid-token')
    return token


# --- Optional imports for semantic features ---
try:
    import numpy as np
except Exception:  # pragma: no cover - numpy may be installed at runtime
    np = None

# sentence-transformers is optional at import; installed in deployment env per task notes.
try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional until dependency available
    SentenceTransformer = None

# --- Config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
STORAGE_DIR = Path(os.getenv("MEMU_STORAGE_DIR", str(Path(__file__).parent / "data")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.getenv("MEMU_PORT", "12345"))
EMBEDDING_MODEL_NAME = os.getenv("MEMU_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DEDUP_THRESHOLD = float(os.getenv("MEMU_DEDUP_SIMILARITY", "0.85"))
CONSOLIDATE_THRESHOLD = float(os.getenv("MEMU_CONSOLIDATE_SIMILARITY", "0.90"))
MEMU_STORE_TTL_DAYS = os.getenv("MEMU_STORE_TTL_DAYS")
MEMU_TASK_TTL_DAYS = os.getenv("MEMU_TASK_TTL_DAYS", "14")


def _parse_env_float(value: Optional[str], default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


MEMU_GATEWAY_TTL_DAYS = _parse_env_float(os.getenv("MEMU_GATEWAY_TTL_DAYS"), 7.0)
MEMU_GATEWAY_WAL_TTL_DAYS = _parse_env_float(os.getenv("MEMU_GATEWAY_WAL_TTL_DAYS"), 14.0)

# --- Gateway durability ---
GATEWAYS_WAL_PATH = STORAGE_DIR / ".gateways.wal.jsonl"

STORAGE_LOCK = threading.Lock()

# --- memU Service ---
from memu.app import MemoryService

llm_config = {}
if OPENAI_API_KEY:
    llm_config = {
        "default": {
            "provider": "openai",
            "api_key": OPENAI_API_KEY,
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "model": os.getenv("MEMU_LLM_MODEL", "gpt-4o-mini"),
        }
    }

service = MemoryService(
    llm_profiles=llm_config or None,
    database_config={"metadata_store": {"provider": "inmemory"}},
)

# --- FastAPI App ---
app = FastAPI(title="memU Local Server", version="1.2.0")


# --- Request Models ---
class StoreRequest(BaseModel):
    """Store a memory item (simple key-value with optional metadata)."""

    key: str
    value: str
    agent: Optional[str] = None
    category: Optional[str] = None
    gateway_id: Optional[str] = None
    metadata: Optional[dict] = None
    dedup: bool = True
    idempotency_key: Optional[str] = None


class RegisterGatewayRequest(BaseModel):
    """Register a gateway with the memU server."""

    gateway_id: str
    hostname: str
    tailscale_ip: Optional[str] = None
    agents: Optional[list[str]] = None
    version: Optional[str] = None
    request_id: Optional[str] = None


class HeartbeatRequest(BaseModel):
    """Gateway heartbeat to signal it's still alive."""

    gateway_id: str
    status: Optional[str] = "healthy"
    agents: Optional[list[str]] = None
    uptime_seconds: Optional[int] = None
    request_id: Optional[str] = None


class SearchRequest(BaseModel):
    """Search stored memories."""

    query: str
    agent: Optional[str] = None
    limit: Optional[int] = 10


class SemanticSearchRequest(BaseModel):
    """Search stored memories by semantic similarity."""

    query: str
    agent: Optional[str] = None
    limit: Optional[int] = 10
    include_archived: bool = False


class ConsolidateRequest(BaseModel):
    """Consolidate related memories into summary records."""

    similarity_threshold: Optional[float] = None
    min_cluster_size: Optional[int] = 2
    include_archived: bool = False


class TaskCreateRequest(BaseModel):
    """Create a memory task for a specific agent."""

    title: str
    description: Optional[str] = None
    assigned_to: str
    priority: str = "medium"
    status: str = "pending"


class TaskUpdateRequest(BaseModel):
    """Update a task status."""

    status: str


class MemorizeRequest(BaseModel):
    """Full memU memorize (conversation-style)."""

    content: list[dict[str, Any]]
    agent: Optional[str] = None


class RetrieveRequest(BaseModel):
    """Full memU retrieve endpoint."""

    query: str
    agent: Optional[str] = None


# --- Simple file-backed stores ---
STORE_FILE = STORAGE_DIR / "store.json"
TASKS_FILE = STORAGE_DIR / "tasks.json"


def _parse_ttl_days(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _store_ttl_seconds() -> Optional[float]:
    ttl_days = _parse_ttl_days(MEMU_STORE_TTL_DAYS)
    return ttl_days * 86400 if ttl_days and ttl_days > 0 else None


def _task_ttl_seconds() -> float:
    ttl_days = _parse_ttl_days(MEMU_TASK_TTL_DAYS)
    return ttl_days * 86400 if ttl_days and ttl_days > 0 else 14 * 86400


def _safe_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_expired(ts: Optional[str], ttl_seconds: Optional[float]) -> bool:
    if ttl_seconds is None:
        return False
    parsed = _parse_iso(ts or "")
    if not parsed:
        return False
    return (_safe_now() - parsed).total_seconds() > ttl_seconds


def _load_json(file_path: Path) -> dict:
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
    return {}


def _safe_fsync(fd):
    try:
        os.fsync(fd)
    except OSError:
        pass


def _atomic_save(file_path: Path, data: dict):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=file_path.parent, suffix=".tmp") as fh:
        json.dump(data, fh, indent=2, default=str)
        fh.flush()
        _safe_fsync(fh.fileno())
        tmp = Path(fh.name)
    tmp.replace(file_path)
    # Ensure replace metadata is durable on POSIX-ish filesystems.
    dir_fd = os.open(file_path.parent, os.O_RDONLY)
    try:
        _safe_fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _iter_jsonl_records(path: Path):
    """Read JSONL records, repairing a final partial line when present."""
    if not path.exists():
        return []

    # Repair partial trailing record if the process crashed mid-write.
    try:
        data = path.read_bytes()
        if data and not data.endswith(b"\n"):
            last_nl = data.rfind(b"\n")
            with open(path, "rb+") as f:
                if last_nl == -1:
                    f.truncate(0)
                else:
                    f.truncate(last_nl + 1)
            if not data[: last_nl + 1].strip():
                return []
            out = []
            for raw_line in data[: last_nl + 1].splitlines():
                if not raw_line.strip():
                    continue
                rec = _safe_parse_jsonl_line(raw_line)
                if rec is not None:
                    out.append(rec)
            return out
    except Exception:
        # Fall through to strict read; malformed tails may still happen while iterating lines.
        pass

    out = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            rec = _safe_parse_jsonl_line(raw)
            if rec is not None:
                out.append(rec)
    return out


def _safe_parse_jsonl_line(raw: str):
    """Parse one JSONL line while tolerating non-critical corruption."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _wal_payload_checksum(payload: dict) -> str:
    normalized = dict(payload)
    normalized.pop("checksum", None)
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _fsync_parent_dir(path: Path):
    parent = path if path.is_dir() else path.parent
    fd = os.open(parent, os.O_RDONLY)
    try:
        _safe_fsync(fd)
    finally:
        os.close(fd)


def _prune_expired_entries(data: dict, ttl_seconds: Optional[float], *, reason: str) -> tuple[dict, bool]:
    if not ttl_seconds:
        return data, False
    changed = False
    pruned = {}
    for entry_id, entry in data.items():
        if not isinstance(entry, dict):
            changed = True
            continue
        ts = entry.get("created_at")
        if _is_expired(ts, ttl_seconds):
            entry["status"] = "expired"
            entry["archived"] = True
            entry["archived_at"] = _safe_now().isoformat()
            entry["archived_reason"] = reason
            # keep for postmortem but remove from active set by skipping
            changed = True
            continue
        pruned[entry_id] = entry
    return pruned, changed


def _load_store() -> dict:
    data = _load_json(STORE_FILE)
    ttl_seconds = _store_ttl_seconds()
    if ttl_seconds is None:
        return data
    pruned, changed = _prune_expired_entries(data, ttl_seconds, reason="ttl-expired")
    if changed:
        _atomic_save(STORE_FILE, pruned)
    return pruned


def _save_store(data: dict):
    _atomic_save(STORE_FILE, data)


def _load_tasks() -> dict:
    data = _load_json(TASKS_FILE)
    ttl_seconds = _task_ttl_seconds()
    pruned, changed = _prune_expired_entries(data, ttl_seconds, reason="task-ttl-expired")
    if changed:
        _atomic_save(TASKS_FILE, pruned)
    return pruned


def _save_tasks(data: dict):
    _atomic_save(TASKS_FILE, data)


# --- Gateway file-backed store ---
GATEWAYS_FILE = STORAGE_DIR / "gateways.json"


def _gateway_request_digest(payload: dict) -> str:
    normalized = {
        "payload": payload,
    }
    raw = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _gateway_ttl_seconds() -> float:
    return max(0.0, MEMU_GATEWAY_TTL_DAYS * 86400.0)


def _is_stale_gateway(entry: dict, now: datetime) -> bool:
    parsed = _parse_iso(entry.get("last_heartbeat", "") or "")
    if not parsed:
        return False
    return (now - parsed).total_seconds() > _gateway_ttl_seconds()


def _collect_stale_gateways(gateways: dict) -> dict:
    if _gateway_ttl_seconds() <= 0:
        return gateways, False
    now = _safe_now()
    active = {}
    changed = False
    removed = 0
    for gateway_id, entry in gateways.items():
        if not isinstance(entry, dict):
            changed = True
            continue
        if _is_stale_gateway(entry, now):
            # TTL/GC: drop entries that have been stale for more than the gateway TTL window.
            changed = True
            removed += 1
            continue
        active[gateway_id] = entry
    return active, changed or removed > 0


def _load_gateways() -> dict:
    data = _load_json(GATEWAYS_FILE)
    gc_data, changed = _collect_stale_gateways(data)
    if changed:
        _atomic_save(GATEWAYS_FILE, gc_data)
    return gc_data


def _wal_append_gateway_op(payload: dict) -> None:
    GATEWAYS_WAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamped = dict(payload)
    stamped.setdefault("checksum", _wal_payload_checksum(stamped))
    line = json.dumps(stamped, separators=(",", ":"))
    with open(GATEWAYS_WAL_PATH, "a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")
        f.flush()
        _safe_fsync(f.fileno())
    _fsync_parent_dir(GATEWAYS_WAL_PATH)


def _save_gateways(data: dict, *, repair_tail: bool = False):
    _atomic_save(GATEWAYS_FILE, data)
    if repair_tail:
        _compact_gateway_wal()


def _load_gateway_op_payload(req, op_kind: str) -> tuple[dict, str]:
    req_payload = req.dict()
    payload = {
        "kind": op_kind,
        "gateway_id": req.gateway_id,
        "ts": _safe_now().isoformat(),
    }
    req_id = req_payload.get("request_id")
    req_digest = _gateway_request_digest(req_payload)
    if op_kind == "register-gateway":
        payload.update({
            "hostname": req_payload.get("hostname"),
            "tailscale_ip": req_payload.get("tailscale_ip"),
            "agents": req_payload.get("agents") or [],
            "version": req_payload.get("version"),
            "request_id": req_id,
            "request_digest": req_digest,
        })
    else:
        payload.update({
            "status": req_payload.get("status") or "healthy",
            "agents": req_payload.get("agents"),
            "uptime_seconds": req_payload.get("uptime_seconds"),
            "request_id": req_id,
            "request_digest": req_digest,
        })
    return payload, req_digest


def _apply_gateway_op(gateways: dict, op: dict) -> dict:
    """Apply one gateway WAL operation to in-memory map."""
    kind = op.get("kind")
    gw_id = op.get("gateway_id")
    if not gw_id:
        return gateways
    now = op.get("ts") or _safe_now().isoformat()
    if kind == "register-gateway":
        existing = gateways.get(gw_id, {})
        entry = {
            "gateway_id": gw_id,
            "hostname": op.get("hostname") or existing.get("hostname", ""),
            "tailscale_ip": op.get("tailscale_ip") or existing.get("tailscale_ip"),
            "agents": op.get("agents") if op.get("agents") is not None else existing.get("agents", []),
            "version": op.get("version") or existing.get("version"),
            "registered_at": existing.get("registered_at") if existing else now,
            "last_heartbeat": now,
            "status": "healthy",
            "last_request_id": op.get("request_id"),
            "last_request_digest": op.get("request_digest"),
            "request_seq": existing.get("request_seq", 0) + 1,
        }
        gateways[gw_id] = entry
        return gateways

    if kind == "heartbeat":
        if gw_id not in gateways:
            return gateways
        gw = dict(gateways[gw_id])
        if op.get("status"):
            gw["status"] = op.get("status")
        if op.get("agents") is not None:
            gw["agents"] = op.get("agents")
        if op.get("uptime_seconds") is not None:
            gw["uptime_seconds"] = op.get("uptime_seconds")
        gw["last_heartbeat"] = now
        if op.get("request_id"):
            gw["last_request_id"] = op.get("request_id")
            gw["last_request_digest"] = op.get("request_digest")
        gw["request_seq"] = gw.get("request_seq", 0) + 1
        gateways[gw_id] = gw
        return gateways

    return gateways


def _compact_gateway_wal():
    if not GATEWAYS_WAL_PATH.exists():
        return
    now = _safe_now()
    cutoff = now - timedelta(days=MEMU_GATEWAY_WAL_TTL_DAYS)
    pending = {}
    applied = set()
    records = [
        rec for rec in _iter_jsonl_records(GATEWAYS_WAL_PATH)
        if isinstance(rec, dict)
    ]

    for rec in records:
        op_id = rec.get("op_id")
        if not op_id:
            continue
        rec_ts = _parse_iso(rec.get("ts", ""))
        if rec_ts and rec_ts < cutoff:
            continue
        kind = rec.get("kind")
        if kind == "gateway.applied":
            applied.add(op_id)
        elif kind in {"register-gateway", "heartbeat"} and rec.get("state") == "pending":
            pending[op_id] = rec

    retained = []
    for rec in records:
        op_id = rec.get("op_id")
        kind = rec.get("kind")
        rec_ts = _parse_iso(rec.get("ts", ""))
        if not op_id or (rec_ts and rec_ts < cutoff):
            continue
        if kind in {"register-gateway", "heartbeat"} and rec.get("state") == "pending" and op_id in applied:
            continue
        if kind == "gateway.applied" and op_id not in pending:
            continue
        retained.append(rec)

    if retained:
        tmp = GATEWAYS_WAL_PATH.with_suffix(".jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for rec in retained:
                f.write(json.dumps(rec, separators=(",", ":")))
                f.write("\n")
            f.flush()
            _safe_fsync(f.fileno())
        tmp.replace(GATEWAYS_WAL_PATH)
        _fsync_parent_dir(GATEWAYS_WAL_PATH)
    else:
        GATEWAYS_WAL_PATH.unlink(missing_ok=True)


def _recover_gateway_wal() -> dict:
    records = list(_iter_jsonl_records(GATEWAYS_WAL_PATH))
    if not records:
        return _load_json(GATEWAYS_FILE)

    gateways = _load_json(GATEWAYS_FILE)
    applied = set()
    pending: dict[str, dict] = {}

    for rec in records:
        if not isinstance(rec, dict):
            continue
        op_id = rec.get("op_id")
        if not op_id:
            continue

        # Skip records with checksum mismatch (possible partial/corrupted writes).
        recv_checksum = rec.get("checksum")
        if recv_checksum and recv_checksum != _wal_payload_checksum({k: v for k, v in rec.items() if k != "checksum"}):
            continue

        if rec.get("kind") == "gateway.applied":
            applied.add(op_id)
            continue
        if rec.get("state") != "pending":
            continue
        pending[op_id] = rec

    for op_id, rec in sorted(pending.items(), key=lambda item: item[1].get("ts", "")):
        if op_id in applied:
            continue
        _apply_gateway_op(gateways, rec)
        _wal_append_gateway_op({
            "op_id": op_id,
            "kind": "gateway.applied",
            "state": "done",
            "ts": _safe_now().isoformat(),
            "gateway_id": rec.get("gateway_id"),
        })

    if pending:
        _atomic_save(GATEWAYS_FILE, gateways)
    _compact_gateway_wal()
    return gateways



# Replay and repair pending gateway writes before serving requests.
with STORAGE_LOCK:
    _RECOVERED_GATEWAYS = _recover_gateway_wal()
    if _RECOVERED_GATEWAYS:
        _atomic_save(GATEWAYS_FILE, _RECOVERED_GATEWAYS)


# --- Embedding helpers ---
_embedder = None

# Ollama embedding config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
_USE_OLLAMA = os.getenv("MEMU_EMBEDDING_BACKEND", "ollama").lower() == "ollama"

import urllib.request
import urllib.error


def _ollama_embed(text: str) -> Optional[list[float]]:
    """Get embeddings from Ollama API (nomic-embed-text: 768-dim)."""
    try:
        payload = json.dumps({"model": OLLAMA_EMBED_MODEL, "input": text}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            embeddings = data.get("embeddings", [[]])
            if embeddings and len(embeddings[0]) > 0:
                return embeddings[0]
    except Exception:
        pass
    return None


def _ollama_available() -> bool:
    """Check if Ollama is running and has the embedding model."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            return OLLAMA_EMBED_MODEL in models
    except Exception:
        return False


def _embedding_ready() -> bool:
    if _USE_OLLAMA and _ollama_available():
        return True
    return bool(np is not None and SentenceTransformer is not None)


def _get_embedder():
    global _embedder
    if _USE_OLLAMA and _ollama_available():
        return None  # Ollama doesn't need a local embedder object
    if not (np is not None and SentenceTransformer is not None):
        raise RuntimeError("Embedding engine unavailable. Install sentence-transformers and numpy, or start Ollama.")
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedder


def _text_for_memory(entry: dict) -> str:
    parts = [entry.get("key", ""), entry.get("value", "")]
    return "\n".join([p for p in parts if p])


def _to_vector(entry_or_text) -> list[float] | None:
    """Return an embedding list for a text blob or None on failure.
    Tries Ollama first (nomic-embed-text, 768-dim), falls back to sentence-transformers.
    """
    text = None
    if isinstance(entry_or_text, str):
        text = entry_or_text
    elif isinstance(entry_or_text, dict):
        text = _text_for_memory(entry_or_text)
    if not text:
        return None

    # Try Ollama first
    if _USE_OLLAMA:
        vec = _ollama_embed(text)
        if vec:
            return _normalize_vec(vec)

    # Fallback to sentence-transformers
    try:
        embedder = _get_embedder()
        if embedder is not None:
            vec = embedder.encode(text, convert_to_numpy=True)
            arr = vec.astype(float).tolist()
            return _normalize_vec(arr)
    except Exception:
        pass
    return None


def _content_signature(entry: dict) -> str:
    if not entry:
        return ""
    raw = f"{entry.get('key', '')}|{entry.get('value', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_vec(vec) -> list[float]:
    arr = np.array(vec, dtype=float)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr.tolist()
    return (arr / norm).tolist()


def _cosine_similarity(a, b) -> float:
    if np is None:
        raise RuntimeError("numpy not available")
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _iter_active_memories(store_data: dict):
    for entry_id, entry in store_data.items():
        if entry.get("archived"):
            continue
        yield entry_id, entry


def _find_best_match(store_data: dict, query_vector: list[float]) -> tuple[Optional[str], Optional[dict], float]:
    """Find closest non-archived memory by cosine similarity."""
    best_id = None
    best_entry = None
    best_score = -1.0

    for candidate_id, candidate in _iter_active_memories(store_data):
        candidate_vec = candidate.get("embedding")
        if not candidate_vec:
            continue
        try:
            score = _cosine_similarity(query_vector, candidate_vec)
        except Exception:
            continue
        if score > best_score:
            best_score = score
            best_id = candidate_id
            best_entry = candidate

    if best_score <= 0:
        return None, None, float(best_score)
    return best_id, best_entry, float(best_score)


def _recency_factor(entry: dict, half_life_hours: float = 168.0) -> float:
    """Exponential decay factor based on entry age. Default half-life = 7 days (168h).
    Returns a value in (0, 1] where 1.0 = just stored, 0.5 = 7 days old, etc."""
    stored_at_str = (
        entry.get("created_at")
        or entry.get("stored_at")
        or entry.get("updated_at")
        or entry.get("timestamp")
        or ""
    )
    try:
        stored_at = datetime.fromisoformat(stored_at_str)
        if stored_at.tzinfo is None:
            stored_at = stored_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - stored_at).total_seconds() / 3600.0
        decay_lambda = math.log(2) / half_life_hours
        return math.exp(-decay_lambda * max(age_hours, 0))
    except Exception:
        return 0.5  # safe fallback


def _use_count_boost(entry: dict) -> float:
    """Logarithmic boost for frequently-accessed entries (range 1.0–1.6x)."""
    use_count = entry.get("use_count", 0) or entry.get("access_count", 0) or 0
    if isinstance(use_count, str):
        try:
            use_count = int(use_count)
        except ValueError:
            use_count = 0
    return 1.0 + 0.2 * math.log1p(max(use_count, 0))


def _list_similar(store_data: dict, query_vector: list[float], limit: int = 10, include_archived: bool = False):
    results = []
    for candidate_id, candidate in store_data.items():
        if not include_archived and candidate.get("archived"):
            continue
        candidate_vec = candidate.get("embedding")
        if not candidate_vec:
            continue
        try:
            cosine_score = _cosine_similarity(query_vector, candidate_vec)
        except Exception:
            continue
        recency = _recency_factor(candidate)
        use_boost = _use_count_boost(candidate)
        final_score = cosine_score * recency * use_boost
        results.append({
            **candidate,
            "id": candidate_id,
            "_score": final_score,
            "_cosine_raw": round(cosine_score, 6),
            "_recency_factor": round(recency, 4),
            "_use_boost": round(use_boost, 4),
            "_scoring": "cosine+recency+use",
        })

    results.sort(key=lambda x: x.get("_score", 0.0), reverse=True)
    return results[:limit]


def _build_task_summary(tasks: list[dict], include_status: Optional[str], agent: Optional[str]):
    out = tasks
    if agent:
        out = [t for t in out if t.get("assigned_to") == agent]
    if include_status:
        out = [t for t in out if t.get("status") == include_status]
    return out


# --- Endpoints ---

@app.get("/api/v1/memu", dependencies=[Depends(get_api_key)])
@app.get("/", dependencies=[Depends(get_api_key)])
async def root():
    return {"service": "memU Local Server", "status": "running", "version": "1.2.0"}



@app.get("/api/v1/memu/capabilities", dependencies=[Depends(get_api_key)])
@app.get("/capabilities", dependencies=[Depends(get_api_key)])
async def get_capabilities():
    return {
        "service": "memU legacy",
        "version": "1.2.0",
        "canonical_base": "/api/v1/memu",
        "canonical_endpoints": {
            "store": "/store",
            "search": "/search",
            "semantic_search": "/semantic-search",
            "list": "/tasks",
            "update": "/tasks/{id}",
            "delete": "/delete",
            "restore": "/restore",
            "rollback": "/rollback",
            "history": "/history",
            "audit": "/audit",
            "events": "/events",
            "health": "/health",
            "feature_flags": "/feature-flags",
        },
        "capability": {
            "strict_schema_enabled": False,
            "legacy_aliases_enabled": True,
            "legacy_aliases": ["/store", "/search", "/health"],
            "async_ingest_enabled": False,
            "audit_events_enabled": False,
            "rollback_enabled": False,
            "soft_delete_restore_enabled": False,
            "freshness_fusion_enabled": False,
        },
        "auth": {
            "scope_model": ["read", "write"],
            "read_endpoints": ["/search", "/health", "/semantic-search", "/capabilities"],
            "write_endpoints": ["/store", "/tasks", "/memorize", "/consolidate"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/v1/memu/health", dependencies=[Depends(get_api_key)])
@app.get("/health", dependencies=[Depends(get_api_key)])
async def health():
    gateways = _load_gateways()
    active_gateways = [
        g for g in gateways.values()
        if isinstance(g, dict) and g.get("status") != "stale"
    ]
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "store_entries": len(_load_store()),
        "tasks_entries": len(_load_tasks()),
        "llm_configured": bool(OPENAI_API_KEY),
        "embeddings_enabled": bool(_embedding_ready()),
        "embedding_model": OLLAMA_EMBED_MODEL if (_USE_OLLAMA and _ollama_available()) else EMBEDDING_MODEL_NAME,
        "embedding_backend": "ollama" if (_USE_OLLAMA and _ollama_available()) else "sentence-transformers",
        "gateway_count": len(active_gateways),
        "gateway_wal": str(GATEWAYS_WAL_PATH),
        "gateway_wal_exists": GATEWAYS_WAL_PATH.exists(),
    }


@app.post("/api/v1/memu/store", dependencies=[Depends(get_api_key)])
@app.post("/store", dependencies=[Depends(get_api_key)])
async def store(req: StoreRequest):
    """Store a key-value memory entry with optional semantic deduplication."""
    now_iso = _safe_now().isoformat()
    if not req.key or not req.key.strip():
        raise HTTPException(status_code=400, detail="Field 'key' is required")
    if not req.value or not req.value.strip():
        raise HTTPException(status_code=400, detail="Field 'value' is required")
    if req.idempotency_key:
        with STORAGE_LOCK:
            existing_store = _load_store()
            normalized = req.idempotency_key.strip()
            for existing_id, existing in existing_store.items():
                metadata = existing.get("metadata", {}) or {}
                if metadata.get("idempotency_key") == normalized and existing.get("key") == req.key:
                    return JSONResponse(content={
                        "status": "success",
                        "action": "idempotent",
                        "id": existing_id,
                        "message": "Idempotent replay detected",
                    })

    with STORAGE_LOCK:
        store_data = _load_store()
        entry = {
            "id": str(uuid.uuid4())[:8],
            "key": req.key,
            "value": req.value,
            "agent": req.agent,
            "category": req.category,
            "gateway_id": req.gateway_id,
            "metadata": {**(req.metadata or {}), "idempotency_key": req.idempotency_key} if req.idempotency_key else (req.metadata or {}),
            "created_at": now_iso,
            "updated_at": now_iso,
            "archived": False,
            "status": "active",
        }

        query_embedding = _to_vector({"key": req.key, "value": req.value}) if req.dedup and _embedding_ready() else None

        merged = False
        merged_with = None
        merge_score = None

        if req.dedup and query_embedding is not None:
            best_id, best_entry, score = _find_best_match(store_data, query_embedding)
            if best_id and best_entry and score >= DEDUP_THRESHOLD:
                # Merge/update the nearest existing memory and return it instead of creating a duplicate.
                merged = True
                merged_with = best_id
                merge_score = score
                merged_entry = best_entry.copy()
                merged_entry["value"] = f"{merged_entry.get('value', '')}\n\n[Duplicate merged at {now_iso}]: {req.value}".strip()
                merged_entry["agent"] = req.agent or merged_entry.get("agent")
                merged_entry["gateway_id"] = req.gateway_id or merged_entry.get("gateway_id")
                if req.category:
                    merged_entry["category"] = req.category
                if req.metadata:
                    
                    md = merged_entry.get("metadata", {}) or {}
                    md.update(req.metadata)
                    merged_entry["metadata"] = md
                history = merged_entry.setdefault("metadata", {}).get("merge_history", [])
                history.append({
                    "merged_from": req.key,
                    "merged_at": now_iso,
                    "source_value": req.value,
                    "similarity": score,
                    "source_agent": req.agent,
                    "source_gateway_id": req.gateway_id,
                    "status": "merged",
                })
                merged_entry["metadata"]["merge_history"] = history
                merged_entry["metadata"]["duplicate_count"] = int(merged_entry["metadata"].get("duplicate_count", 1)) + 1
                merged_entry["updated_at"] = now_iso
                merged_entry["embedding"] = query_embedding
                store_data[best_id] = merged_entry

        if not merged:
            if query_embedding is not None:
                entry["embedding"] = query_embedding
            store_data[entry["id"]] = entry

        _save_store(store_data)

    message = "Merged with existing memory" if merged else f"Stored entry '{req.key}' with id {entry['id']}"

    return JSONResponse(content={
        "status": "success",
        "action": "merged" if merged else "stored",
        "dedup_enabled": req.dedup,
        "id": merged_with if merged else entry["id"],
        "similarity": merge_score,
        "message": message,
    })


@app.post("/api/v1/memu/search", dependencies=[Depends(get_api_key)])
@app.post("/search", dependencies=[Depends(get_api_key)])
async def search(req: SearchRequest):
    """Search stored memories by key/value text match. No LLM required."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must be non-empty")
    with STORAGE_LOCK:
        store_data = _load_store()
    query_lower = req.query.lower()
    results = []
    for entry in store_data.values():
        if entry.get("archived"):
            continue
        score = 0
        if query_lower in entry.get("key", "").lower():
            score += 2
        if query_lower in entry.get("value", "").lower():
            score += 1
        if req.agent and entry.get("agent") == req.agent:
            score += 1
        if score > 0:
            results.append({**entry, "_score": score})

    results.sort(key=lambda x: x["_score"], reverse=True)
    results = results[: req.limit or 10]

    return JSONResponse(content={
        "status": "success",
        "count": len(results),
        "results": results,
    })


@app.post("/api/v1/memu/semantic-search", dependencies=[Depends(get_api_key)])
@app.post("/semantic-search", dependencies=[Depends(get_api_key)])
async def semantic_search(req: SemanticSearchRequest):
    """Search stored memories by semantic similarity using embeddings."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must be non-empty")
    if not _embedding_ready():
        raise HTTPException(status_code=503, detail="Embeddings unavailable. Install sentence-transformers and numpy.")

    query_vec = _to_vector(req.query)
    if query_vec is None:
        raise HTTPException(status_code=500, detail="Failed to embed query")

    with STORAGE_LOCK:
        store_data = _load_store()

    results = _list_similar(store_data, query_vec, req.limit or 10, req.include_archived)

    if req.agent:
        results = [r for r in results if r.get("agent") == req.agent]

    # Fallback: if no embeddings attached, still provide plain text score fallback using same shape.
    if not results:
        query_lower = req.query.lower()
        legacy = []
        for entry_id, entry in store_data.items():
            if not req.include_archived and entry.get("archived"):
                continue
            if req.agent and entry.get("agent") != req.agent:
                continue
            score = 0
            if query_lower in entry.get("key", "").lower():
                score += 2
            if query_lower in entry.get("value", "").lower():
                score += 1
            if score > 0:
                legacy.append({**entry, "id": entry_id, "_score": score})
        legacy.sort(key=lambda x: x["_score"], reverse=True)
        results = legacy[: req.limit or 10]

    return JSONResponse(content={
        "status": "success",
        "count": len(results),
        "results": results,
        "query_embedding_ready": bool(query_vec),
        "model": EMBEDDING_MODEL_NAME,
    })


@app.post("/api/v1/memu/consolidate", dependencies=[Depends(get_api_key)])
@app.post("/consolidate", dependencies=[Depends(get_api_key)])
async def consolidate(req: ConsolidateRequest):
    """Consolidate semantically similar memories into summary records and archive originals."""
    threshold = req.similarity_threshold if req.similarity_threshold is not None else CONSOLIDATE_THRESHOLD
    min_cluster_size = max(2, req.min_cluster_size or 2)

    if not _embedding_ready():
        raise HTTPException(status_code=503, detail="Embeddings unavailable. Install sentence-transformers and numpy.")

    with STORAGE_LOCK:
        store_data = _load_store()

        # active + embedded only
        candidate_ids = [
            entry_id
            for entry_id, entry in store_data.items()
            if (req.include_archived or not entry.get("archived")) and entry.get("embedding")
        ]

        visited = set()
        clusters = []

        def _neighbors(seed_id: str) -> list[str]:
            neighbors = []
            seed_vec = store_data[seed_id].get("embedding")
            if not seed_vec:
                return []
            for candidate_id in candidate_ids:
                if candidate_id == seed_id or candidate_id in visited:
                    continue
                cand_vec = store_data[candidate_id].get("embedding")
                if not cand_vec:
                    continue
                sim = _cosine_similarity(seed_vec, cand_vec)
                if sim >= threshold:
                    neighbors.append(candidate_id)
            return neighbors

        for entry_id in candidate_ids:
            if entry_id in visited:
                continue
            queue = [entry_id]
            cluster = []
            visited.add(entry_id)

            while queue:
                current = queue.pop(0)
                cluster.append(current)
                for n_id in _neighbors(current):
                    if n_id not in visited:
                        visited.add(n_id)
                        queue.append(n_id)

            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)

        created = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for cluster in clusters:
            cluster_entries = [store_data[cid] for cid in cluster]
            avg_embedding = None
            if np is not None:
                vecs = [np.array(store_data[cid]["embedding"], dtype=float) for cid in cluster if store_data[cid].get("embedding")]
                if vecs:
                    avg_embedding = np.mean(np.vstack(vecs), axis=0).astype(float).tolist()

            summary_lines = []
            for idx, cid in enumerate(cluster, 1):
                item = store_data[cid]
                summary_lines.append(
                    f"{idx}. key='{item.get('key', '')}', value='{item.get('value', '')[:140]}', created_at={item.get('created_at', '')}"
                )

            summary_entry = {
                "id": str(uuid.uuid4())[:8],
                "key": f"consolidated:{now_iso}",
                "value": f"Consolidated {len(cluster)} memories:\n" + "\n".join(summary_lines),
                "agent": "system",
                "category": "consolidated",
                "gateway_id": None,
                "metadata": {
                    "cluster_size": len(cluster),
                    "merged_ids": cluster,
                    "similarity_threshold": threshold,
                },
                "created_at": now_iso,
                "updated_at": now_iso,
                "archived": False,
                "status": "active",
                "source": "consolidation",
                "embedding": _normalize_vec(avg_embedding) if avg_embedding else None,
            }

            # Archive source entries.
            for cid in cluster:
                source = store_data[cid]
                source["archived"] = True
                source["status"] = "archived"
                source["archived_at"] = now_iso
                source["archived_into"] = summary_entry["id"]
                source["updated_at"] = now_iso
                store_data[cid] = source

            store_data[summary_entry["id"]] = summary_entry
            created.append(summary_entry["id"])

        _save_store(store_data)

    return JSONResponse(content={
        "status": "success",
        "clusters": len(created),
        "summary_ids": created,
        "message": f"Consolidated {len(created)} memory clusters",
    })


@app.post("/api/v1/memu/tasks", dependencies=[Depends(get_api_key)])
@app.post("/tasks", dependencies=[Depends(get_api_key)])
async def create_task(req: TaskCreateRequest):
    """Create a task delegation entry."""
    if req.status not in {"pending", "claimed", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status. Use: pending, claimed, done")

    now_iso = datetime.now(timezone.utc).isoformat()
    task_id = str(uuid.uuid4())[:8]

    with STORAGE_LOCK:
        tasks = _load_tasks()
        tasks[task_id] = {
            "id": task_id,
            "title": req.title,
            "description": req.description,
            "assigned_to": req.assigned_to,
            "priority": req.priority,
            "status": req.status,
            "created_at": now_iso,
            "updated_at": now_iso,
            "history": [],
        }
        _save_tasks(tasks)

    return JSONResponse(content={
        "status": "success",
        "id": task_id,
        "message": f"Task '{req.title}' created and assigned to {req.assigned_to}",
    })


@app.get("/api/v1/memu/tasks", dependencies=[Depends(get_api_key)])
@app.get("/tasks", dependencies=[Depends(get_api_key)])
async def list_tasks(agent: Optional[str] = None, status: Optional[str] = None):
    """List tasks, optionally filtered by agent and status."""
    tasks = _load_tasks()
    task_list = [t for t in tasks.values() if True]
    task_list = _build_task_summary(task_list, status, agent)
    task_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return JSONResponse(content={
        "status": "success",
        "count": len(task_list),
        "tasks": task_list,
    })


@app.patch("/api/v1/memu/tasks/{task_id}", dependencies=[Depends(get_api_key)])
@app.patch("/tasks/{task_id}", dependencies=[Depends(get_api_key)])
async def update_task(task_id: str, req: TaskUpdateRequest):
    """Update task status."""
    next_status = req.status
    if next_status not in {"pending", "claimed", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status. Use: pending, claimed, done")

    with STORAGE_LOCK:
        tasks = _load_tasks()
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

        task = tasks[task_id]
        current = task.get("status")

        order = {"pending": 0, "claimed": 1, "done": 2}
        if order[next_status] < order.get(current, 0):
            raise HTTPException(status_code=400, detail=f"Invalid transition from {current} to {next_status}")

        task["status"] = next_status
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        task.setdefault("history", []).append({
            "from": current,
            "to": next_status,
            "changed_at": task["updated_at"],
        })
        tasks[task_id] = task
        _save_tasks(tasks)

    return JSONResponse(content={
        "status": "success",
        "id": task_id,
        "message": f"Task '{task_id}' status changed from {current} to {next_status}",
        "status_value": next_status,
    })


@app.post("/api/v1/memu/register-gateway", dependencies=[Depends(get_api_key)])
@app.post("/register-gateway", dependencies=[Depends(get_api_key)])
async def register_gateway(req: RegisterGatewayRequest):
    """Register a new gateway or update an existing one."""
    op_id = str(uuid.uuid4())
    payload, request_digest = _load_gateway_op_payload(req, "register-gateway")
    payload["op_id"] = op_id
    payload["state"] = "pending"
    payload["request_digest"] = request_digest
    now = payload.get("ts")

    with STORAGE_LOCK:
        gateways = _load_gateways()
        existing = gateways.get(req.gateway_id)

        if req.request_id and existing:
            last_id = existing.get("last_request_id")
            last_digest = existing.get("last_request_digest")
            if last_id == req.request_id and last_digest == request_digest:
                action = "idempotent"
                return JSONResponse(content={
                    "status": "success",
                    "action": action,
                    "gateway_id": req.gateway_id,
                    "message": f"Gateway '{req.gateway_id}' request_id replayed",
                    "request_id": req.request_id,
                    "request_seq": existing.get("request_seq", 0),
                    "last_request_id": existing.get("last_request_id"),
                    "op_id": "noop",
                })
            if last_id == req.request_id and last_digest != request_digest:
                raise HTTPException(
                    status_code=409,
                    detail="request_id reused with different payload",
                )

        _wal_append_gateway_op(payload)

        entry = {
            "gateway_id": req.gateway_id,
            "hostname": req.hostname,
            "tailscale_ip": req.tailscale_ip,
            "agents": req.agents or [],
            "version": req.version,
            "registered_at": existing["registered_at"] if existing else now,
            "last_heartbeat": now,
            "status": "healthy",
            "last_request_id": req.request_id,
            "last_request_digest": request_digest,
            "request_seq": (existing.get("request_seq", 0) + 1) if existing else 1,
        }
        gateways[req.gateway_id] = entry
        _save_gateways(gateways)

        _wal_append_gateway_op({
            "op_id": op_id,
            "kind": "gateway.applied",
            "state": "done",
            "ts": datetime.now(timezone.utc).isoformat(),
            "gateway_id": req.gateway_id,
        })

        _compact_gateway_wal()

    action = "updated" if existing else "registered"
    return JSONResponse(content={
        "status": "success",
        "action": action,
        "gateway_id": req.gateway_id,
        "message": f"Gateway '{req.gateway_id}' {action} successfully",
        "request_id": req.request_id,
        "request_seq": gateways[req.gateway_id].get("request_seq", 1),
        "op_id": op_id,
    })


@app.get("/api/v1/memu/gateways", dependencies=[Depends(get_api_key)])
@app.get("/gateways", dependencies=[Depends(get_api_key)])
async def list_gateways():
    """List all registered gateways with their heartbeat status."""
    with STORAGE_LOCK:
        gateways = _load_gateways()
        # Hide stale entries from normal listing while preserving audit metadata in store.
        now = _safe_now()
        gateway_list = [
            gateway
            for gateway in gateways.values()
            if isinstance(gateway, dict) and gateway.get("status") != "stale"
            and not _is_stale_gateway(gateway, now)
        ]
    return JSONResponse(content={
        "status": "success",
        "count": len(gateway_list),
        "gateways": gateway_list,
    })


@app.post("/api/v1/memu/heartbeat", dependencies=[Depends(get_api_key)])
@app.post("/heartbeat", dependencies=[Depends(get_api_key)])
async def heartbeat(req: HeartbeatRequest):
    """Receive a heartbeat from a gateway."""
    if req.status is not None:
        req.status = req.status.strip().lower() if req.status.strip() else "healthy"
    payload, request_digest = _load_gateway_op_payload(req, "heartbeat")
    op_id = str(uuid.uuid4())
    payload.update({
        "op_id": op_id,
        "state": "pending",
        "request_digest": request_digest,
    })
    now = datetime.now(timezone.utc).isoformat()

    with STORAGE_LOCK:
        gateways = _load_gateways()
        if req.gateway_id not in gateways:
            raise HTTPException(
                status_code=404,
                detail=f"Gateway '{req.gateway_id}' not registered. Use POST /register-gateway first.",
            )

        gw = gateways[req.gateway_id]
        if req.request_id and gw.get("last_request_id") == req.request_id and gw.get("last_request_digest") == request_digest:
            return JSONResponse(content={
                "status": "success",
                "action": "idempotent",
                "gateway_id": req.gateway_id,
                "message": f"Heartbeat for '{req.gateway_id}' request_id replayed",
                "request_id": req.request_id,
                "last_heartbeat": gw.get("last_heartbeat"),
                "op_id": "noop",
            })

        if req.request_id and gw.get("last_request_id") == req.request_id and gw.get("last_request_digest") != request_digest:
            raise HTTPException(
                status_code=409,
                detail="request_id reused with different payload",
            )

        _wal_append_gateway_op(payload)

        gw["last_heartbeat"] = now
        gw["status"] = req.status or "healthy"
        if req.agents is not None:
            gw["agents"] = req.agents
        if req.uptime_seconds is not None:
            gw["uptime_seconds"] = req.uptime_seconds
        gw["request_seq"] = gw.get("request_seq", 0) + 1
        gw["last_request_id"] = req.request_id
        gw["last_request_digest"] = request_digest
        gateways[req.gateway_id] = gw
        _save_gateways(gateways)

        _wal_append_gateway_op({
            "op_id": op_id,
            "kind": "gateway.applied",
            "state": "done",
            "ts": now,
            "gateway_id": req.gateway_id,
        })
        _compact_gateway_wal()

    return JSONResponse(content={
        "status": "success",
        "gateway_id": req.gateway_id,
        "last_heartbeat": now,
        "message": f"Heartbeat received for '{req.gateway_id}'",
        "request_id": req.request_id,
        "request_seq": gateways[req.gateway_id].get("request_seq", 1),
        "op_id": op_id,
    })


@app.get("/api/v1/memu/gateways/{gateway_id}/memories", dependencies=[Depends(get_api_key)])
@app.get("/gateways/{gateway_id}/memories", dependencies=[Depends(get_api_key)])
async def gateway_memories(gateway_id: str):
    """Get all memories stored by a specific gateway."""
    with STORAGE_LOCK:
        gateways = _load_gateways()
        if gateway_id not in gateways:
            raise HTTPException(
                status_code=404,
                detail=f"Gateway '{gateway_id}' not found.",
            )
    if _is_stale_gateway(gateways[gateway_id], _safe_now()):
        raise HTTPException(status_code=410, detail=f"Gateway '{gateway_id}' is stale")

    store_data = _load_store()
    results = [
        entry
        for entry in store_data.values()
        if entry.get("gateway_id") == gateway_id
    ]
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return JSONResponse(content={
        "status": "success",
        "gateway_id": gateway_id,
        "count": len(results),
        "memories": results,
    })


@app.post("/api/v1/memu/memorize", dependencies=[Depends(get_api_key)])
@app.post("/memorize", dependencies=[Depends(get_api_key)])
async def memorize(req: MemorizeRequest):
    """Full memU memorize endpoint (requires LLM)."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="LLM not configured. Set OPENAI_API_KEY.")
    try:
        file_path = STORAGE_DIR / f"conversation-{uuid.uuid4().hex}.json"
        payload = {
            "content": req.content,
            "agent": req.agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        file_path.write_text(json.dumps(payload, ensure_ascii=False))
        result = await service.memorize(resource_url=str(file_path), modality="conversation")
        return JSONResponse(content={"status": "success", "result": result})
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/memu/retrieve", dependencies=[Depends(get_api_key)])
@app.post("/retrieve", dependencies=[Depends(get_api_key)])
async def retrieve(req: RetrieveRequest):
    """Full memU retrieve endpoint (requires LLM)."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="LLM not configured. Set OPENAI_API_KEY.")
    try:
        result = await service.retrieve([req.query])
        return JSONResponse(content={"status": "success", "result": result})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    print(f"🧠 memU Local Server starting on port {PORT}")
    print(f"   Storage: {STORAGE_DIR}")
    print(f"   LLM: {'configured' if OPENAI_API_KEY else 'NOT configured (store/search still work)'}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
