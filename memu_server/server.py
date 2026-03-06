#!/usr/bin/env python3
"""
memU Bridge Server — Local REST API for multi-agent memory
Endpoints:
  POST /api/v1/memu/store           → store a memory entry (idempotent, content-hash dedup)
  POST /api/v1/memu/search          → search memory entries (FTS + TF-IDF)
  POST /api/v1/memu/semantic-search → semantic search (TF-IDF ranked)
  POST /api/v1/memu/log_event       → log an agent event
  GET  /api/v1/memu/health          → health check + DB stats
  GET  /api/v1/memu/pulse           → recent events stream
  GET  /api/v1/memu/list            → list all entries for a user/agent

Storage: SQLite + Legacy JSON-L migration
Port: 8711
Auth: Bearer token in Authorization header (see config below)
"""

import json
import math
import os
import re
import sys
import uuid
import hashlib
import logging
import threading
import sqlite3
import time
import atexit
from datetime import datetime, timedelta, timezone
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Any, Optional

# ── Config ──────────────────────────────────────────────────────────────────
PORT = int(os.environ.get("MEMU_PORT", "8711"))
MEMORY_DIR = Path(os.environ.get("MEMU_MEMORY_DIR", "/Users/harrisonfethe/.openclaw/workspace/memory"))
MEMU_DATA_DIR = MEMORY_DIR / "memu_store"
MEMU_DB_PATH = MEMU_DATA_DIR / "memu.db"
MEMU_TTL_DAYS = int(os.environ.get("MEMU_TTL_DAYS", "180"))
MEMU_BIND_HOST = os.environ.get("MEMU_BIND_HOST", "127.0.0.1")
SECURITY_AUDIT_MARKER = MEMU_DATA_DIR / "last_security_audit.json"
API_KEY = os.environ.get("MEMU_API_KEY", "openclaw-memu-local-2026")
# Optional explicit token allowlists for least-privilege access control
WRITE_TOKENS = {t.strip() for t in os.environ.get("MEMU_WRITE_API_KEYS", "").split(",") if t.strip()}
READ_TOKENS = {t.strip() for t in os.environ.get("MEMU_READONLY_API_KEYS", "").split(",") if t.strip()}
if API_KEY:
    WRITE_TOKENS.add(API_KEY)
GROUP_ALLOWLIST = {u.strip() for u in os.environ.get("MEMU_GROUP_ALLOWLIST", "").split(",") if u.strip()}
PRIVATE_PAIRING_CODE = os.environ.get("MEMU_PRIVATE_PAIRING_CODE", "")
PRIVATE_REQUIRE_IDENTITY = os.environ.get("MEMU_PRIVATE_REQUIRE_IDENTITY", "1") == "1"
GROUP_REQUIRE_ALLOWLIST = os.environ.get("MEMU_GROUP_REQUIRE_ALLOWLIST", "1") == "1"
SEMANTIC_SCANNER_MODEL = os.environ.get("MEMU_SEMANTIC_SCANNER_MODEL", "gpt-4o-mini")
MEMU_COMPRESSION_ANTHROPIC_MODEL = os.environ.get("MEMU_COMPRESSION_ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
LOG_LEVEL = os.environ.get("MEMU_LOG_LEVEL", "INFO")
MEMU_ASYNC_INGEST_ENABLED = os.environ.get("MEMU_ASYNC_INGEST_ENABLED", "1") == "1"
MEMU_STRICT_SCHEMA_MODE = os.environ.get("MEMU_STRICT_SCHEMA_MODE", "1") == "1"
MEMU_TYPED_CATEGORIES = {
    "reflection", "lesson", "event", "task", "decision", "note", "eval", "conversation",
    "working", "procedural", "factual", "experiential", "general"
}

log = logging.getLogger("memu")
log.setLevel(getattr(logging, LOG_LEVEL))
log.propagate = False  # prevent double-write via root logger

# Avoid duplicate log lines when module is reloaded/restarted in-process.
if not log.handlers:
    _fmt = logging.Formatter("%(asctime)s [memU] %(levelname)s %(message)s")
    _sh = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(_fmt)
    _fh = logging.FileHandler(MEMORY_DIR / "memu_server.log", mode="a")
    _fh.setFormatter(_fmt)
    log.addHandler(_sh)
    log.addHandler(_fh)

MEMU_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Optional LLM compression (P-001) + auto tags (P-002) ────────────────────
DOTENV_PATH = Path("/Volumes/EDrive/Projects/Options_probability/.env")


def _load_env_from_file(path: Path) -> None:
    """Best-effort .env loader (KEY=VALUE lines). Does not override existing env."""
    try:
        if not path.exists():
            return
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception as e:
        log.warning(f"dotenv load skipped: {path} ({e})")


_load_env_from_file(DOTENV_PATH)


# If high-risk inputs are accepted for storage/analysis, they are retained with risk tags.
HIGH_RISK_MARKER_PREFIX = "[RISK]"


INJECTION_PATTERNS = [
    re.compile(r"\bSystem:\s*", re.IGNORECASE),
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"act\s+as\b", re.IGNORECASE),
    re.compile(r"^\s*you\s+are\s+", re.IGNORECASE),
    re.compile(r"<\s*script|javascript:", re.IGNORECASE),
    re.compile(r"\bdelete\s+all\b", re.IGNORECASE),
]


SECRET_PATTERNS = [
    re.compile(r"(?i)(?:api[_-]?key|apikey|token|secret)[\s:=]+[a-z0-9._-]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.=]{10,}"),
    re.compile(r"[Pp]assword\s*[:=]\s*[^\s]{4,}"),
    re.compile(r"(?i)[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"\b\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b"),
    re.compile(r"\b\+?1?[2-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{4}\b"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


# ----------------- Security helpers -----------------
def _split_tokens(value: str) -> set[str]:
    return {v.strip() for v in value.split(",") if v.strip()}


def _sanitize_text(text: str) -> tuple[str, list[str]]:
    text = text or ""
    flags: list[str] = []
    for pat in INJECTION_PATTERNS:
        if pat.search(text):
            flags.append(f"regex:{pat.pattern}")
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            flags.append(f"secret:{pat.pattern}")
    return text, flags


def _is_high_risk_source(body: dict) -> bool:
    source = (body.get("source") or body.get("source_type") or "").lower()
    if source in {"email", "url", "ingestion", "web", "webhook"}:
        return True
    content = (body.get("content") or "").lower()
    return content.startswith("http://") or content.startswith("https://")


def _semantic_scan_for_injection(content: str, context: str = "") -> str | None:
    # Optional second-stage check. If LLM unavailable, degrade to deterministic only.
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    prompt = (
        "Classify content for prompt-injection attempts. "
        f"Context={context}. "
        "Return strict JSON: {\"risk\": \"low|medium|high\", \"reason\": \"...\"}. "
        f"Content:\n{content[:4000]}"
    )
    try:
        payload = {
            "model": SEMANTIC_SCANNER_MODEL,
            "temperature": 0.1,
            "max_tokens": 120,
            "messages": [
                {"role": "system", "content": "You are a cybersecurity classifier. Keep answers strict JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
        data = _http_json(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}", "Content-Type": "application/json"},
            payload=payload,
            timeout=10,
        )
        out = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = json.loads(out)
        risk = str(parsed.get("risk", "")).lower()
        if risk in {"high", "medium", "low"}:
            return risk
    except Exception:
        return None
    return None


def _redact_text(value: str) -> str:
    redacted = str(value)
    for pat in SECRET_PATTERNS:
        redacted = pat.sub("[REDACTED]", redacted)
    return redacted


def _redact_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _redact_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_payload(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_redact_payload(v) for v in obj)
    if isinstance(obj, str):
        return _redact_text(obj)
    return obj


_SESSION_KEYS = ("session_id", "thread_id", "conversation_id")


def _extract_session_value(body: dict) -> str:
    for key in _SESSION_KEYS:
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    metadata = body.get("metadata")
    if isinstance(metadata, dict):
        for key in _SESSION_KEYS:
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _validate_store_schema(body: dict, strict: bool = False) -> tuple[bool, str]:
    user_id = body.get("user_id")
    if user_id is not None and (not isinstance(user_id, str) or not user_id.strip()):
        return False, "Invalid schema: user_id must be a non-empty string"

    session_value = _extract_session_value(body)
    category = str(body.get("category", "general")).strip().lower()
    key = str(body.get("key", "")).strip()
    content = str(body.get("content", "")).strip()

    if strict:
        if not isinstance(user_id, str) or not user_id.strip():
            return False, "Strict schema: user_id is required"
        if not session_value:
            return False, "Strict schema: one of session_id/thread_id/conversation_id is required"
        if category not in MEMU_TYPED_CATEGORIES:
            return False, f"Strict schema: category must be one of {sorted(MEMU_TYPED_CATEGORIES)}"
        if not key:
            return False, "Strict schema: key is required"
        if len(content) < 8:
            return False, "Strict schema: content must be at least 8 characters"

    if session_value and len(session_value) > 256:
        return False, "Invalid schema: session identifier too long"

    return True, "ok"


def _validate_search_schema(body: dict, strict: bool = False) -> tuple[bool, str]:
    if not strict:
        return True, "ok"
    user_id = body.get("user_id")
    if user_id is not None and (not isinstance(user_id, str) or not user_id.strip()):
        return False, "Strict schema: user_id must be a non-empty string when provided"
    if "session_id" in body and (not isinstance(body.get("session_id"), str) or not body.get("session_id").strip()):
        return False, "Strict schema: session_id must be a non-empty string when provided"
    return True, "ok"


def _weekly_security_health_ok(days: int = 7) -> tuple[bool, str]:
    if not SECURITY_AUDIT_MARKER.exists():
        return False, "missing_weekly_audit_marker"
    try:
        age_seconds = (datetime.now(timezone.utc) - datetime.fromtimestamp(SECURITY_AUDIT_MARKER.stat().st_mtime, tz=timezone.utc)).total_seconds()
        if age_seconds > days * 86400:
            return False, f"last_audit_too_old_{int(age_seconds//86400)}d"
    except Exception as exc:
        return False, f"marker_read_error: {exc}"
    return True, SECURITY_AUDIT_MARKER.read_text(encoding="utf-8", errors="replace").strip()

def _parse_authorization(header: str) -> str:
    if header.startswith("Bearer "):
        return header.split(" ", 1)[1].strip()
    return ""


def _check_token_scope(token: str) -> str | None:
    if token in WRITE_TOKENS:
        return "write"
    if token in READ_TOKENS:
        return "read"
    if token == API_KEY:
        return "write"
    return None


def _validate_actor_access(headers, body: dict) -> tuple[bool, str]:
    actor_type = (headers.get("X-Actor-Type") or body.get("actor_type") or "").lower()
    actor_id = headers.get("X-User-Id") or body.get("user_id") or body.get("actor_id") or ""

    if actor_type == "private":
        if PRIVATE_REQUIRE_IDENTITY:
            code = headers.get("X-Pairing-Code") or body.get("pairing_code")
            if not PRIVATE_PAIRING_CODE:
                return False, "Private pairing code not configured."
            if not code or str(code) != PRIVATE_PAIRING_CODE:
                return False, "Private identity verification failed."

    if actor_type == "group":
        if GROUP_REQUIRE_ALLOWLIST and GROUP_ALLOWLIST:
            if not actor_id:
                return False, "Group actor id required for group policy."
            if actor_id not in GROUP_ALLOWLIST:
                return False, "Group actor not allowlisted."

    return True, "ok"


def _http_json(url: str, headers: dict, payload: dict, timeout: int = 25) -> dict:
    import urllib.request
    import urllib.error

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        raise RuntimeError(f"HTTP {e.code} from {url}: {raw[:500]}")


_COMPRESSION_SYSTEM = (
    "You compress user-provided notes into discrete memory facts. "
    "Output MUST be 2–5 bullet-less lines. Each line is a self-contained fact. "
    "Use explicit entities and timestamps when present. Avoid pronouns. "
    "No preamble, no numbering, no extra formatting."
)


def compress_stage1(content: str) -> tuple[str, bool, str | None]:
    """Return (compressed, generated, provider). Best-effort; never raises."""
    text = content or ""
    if len(text) <= 300:
        return text, False, None

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        return text, False, None

    prompt = (
        "Compress the following content into 2–5 lines of self-contained facts.\n\n"
        f"CONTENT:\n{text}\n"
    )

    # Prefer Anthropic (haiku) when available, else OpenAI.
    if anthropic_key:
        try:
            resp = _http_json(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                },
                payload={
                    "model": MEMU_COMPRESSION_ANTHROPIC_MODEL,
                    "max_tokens": 400,
                    "temperature": 0.2,
                    "system": _COMPRESSION_SYSTEM,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            # Anthropic returns list blocks in content
            blocks = resp.get("content", [])
            out = "\n".join([b.get("text", "") for b in blocks if isinstance(b, dict)]).strip()
            if out:
                return out, True, "anthropic"
        except Exception as e:
            log.warning(f"compression failed (anthropic): {e}")

    if openai_key:
        try:
            resp = _http_json(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}"},
                payload={
                    "model": "gpt-4o-mini",
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": _COMPRESSION_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            out = (
                (resp.get("choices") or [{}])[0]
                .get("message", {})
                .get("content", "")
            ).strip()
            if out:
                return out, True, "openai"
        except Exception as e:
            log.warning(f"compression failed (openai): {e}")

    return text, False, None


_STOPWORDS = {
    "a","an","and","are","as","at","be","but","by","for","from","has","have","he","her","hers",
    "him","his","i","if","in","into","is","it","its","me","my","not","of","on","or","our","ours",
    "she","so","that","the","their","theirs","them","then","there","these","they","this","those","to",
    "too","us","was","we","were","what","when","where","which","who","why","will","with","you","your",
    "yours","been","can","could","would","should","may","might","must","do","does","did","doing","done",
}


def extract_auto_tags(text: str, max_tags: int = 5) -> list:
    """Simple keyword extraction from compressed content (no LLM)."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", (text or "").lower())
    freq = {}
    for w in words:
        if w in _STOPWORDS:
            continue
        if w.isdigit():
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
    tags = [w for w, _ in ranked[:max_tags]]
    return tags

# ── Storage helpers (SQLite-backed, atomic, idempotent, crash-safe) ──────────

# GC interval: run TTL sweep every 6 hours during uptime
_GC_INTERVAL_SECONDS = 6 * 3600
# WAL checkpoint interval: every 5 minutes (prevents WAL bloat)
_WAL_CHECKPOINT_INTERVAL = 5 * 60
# Event log rotation: max 10 MB, keep 1 rotated file
_EVENT_LOG_MAX_BYTES = 10 * 1024 * 1024


def _content_hash(content: str, agent_id: str, key: str) -> str:
    """Deterministic content hash for implicit idempotency when no explicit key is provided."""
    blob = f"{agent_id}:{key}:{content}".encode("utf-8")
    return f"ch-{hashlib.sha256(blob).hexdigest()[:24]}"


class MemUStore:
    """Hardened SQLite memory store with:
    - Connection pooling (thread-local)
    - Atomic transactions via explicit BEGIN/COMMIT
    - Content-hash idempotency fallback when no explicit idempotency_key
    - Periodic WAL checkpointing to prevent file bloat
    - Periodic TTL garbage collection
    - Startup integrity check + crash recovery
    - Graceful shutdown with final checkpoint
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._local = threading.local()  # thread-local connection pool
        self._last_gc = 0.0
        self._last_gc_deleted = 0
        self._last_checkpoint = 0.0
        self._startup_integrity_check()
        self._init_db()
        self._migrate_if_needed()
        self._collect_garbage(force=True)
        self._wal_checkpoint()
        atexit.register(self._shutdown)

    def _get_conn(self) -> sqlite3.Connection:
        """Return a thread-local connection (reused within the same thread).
        If the connection is stale or broken, close it and create a fresh one.
        """
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                # Quick liveness test — catches "closed database" etc.
                conn.execute("SELECT 1;")
            except Exception:
                log.warning("Thread-local DB connection stale — reconnecting.")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
                self._local.conn = None
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=15)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
            conn.execute("PRAGMA wal_autocheckpoint=1000;")
            self._local.conn = conn
        return conn

    def _conn(self):
        """Legacy compat — now delegates to thread-local pool."""
        return self._get_conn()

    def _startup_integrity_check(self):
        """Run integrity check at startup; if corrupt, attempt recovery from WAL."""
        if not self.db_path.exists():
            return  # fresh DB, nothing to check
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=15)
            result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
            if result != "ok":
                log.error(f"INTEGRITY CHECK FAILED: {result}")
                log.info("Attempting WAL recovery via checkpoint...")
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    result2 = conn.execute("PRAGMA integrity_check;").fetchone()[0]
                    if result2 == "ok":
                        log.info("WAL recovery succeeded — DB integrity restored.")
                    else:
                        log.error(f"WAL recovery failed: {result2}. Manual intervention needed.")
                except Exception as e2:
                    log.error(f"WAL recovery error: {e2}")
            else:
                log.info("Startup integrity check: OK")
            conn.close()
        except Exception as e:
            log.error(f"Startup integrity check error: {e}")

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                user_id TEXT,
                idempotency_key TEXT UNIQUE,
                key TEXT,
                content TEXT,
                compressed_content TEXT,
                category TEXT,
                tags TEXT, -- JSON
                auto_tags TEXT, -- JSON
                metadata TEXT, -- JSON
                compression TEXT, -- JSON
                stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_stored_at ON memories(stored_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_idem_key ON memories(idempotency_key);")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_audit (
                id TEXT PRIMARY KEY,
                memory_id TEXT,
                action TEXT,
                actor TEXT,
                patch_json TEXT,
                before_json TEXT,
                after_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_audit_memory_id ON memory_audit(memory_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_audit_created_at ON memory_audit(created_at);")
        # Ensure quality_score / use_count / outcome columns exist (added by smoke_test)
        for col_def in [
            ("quality_score", "REAL DEFAULT 0.5"),
            ("use_count", "INT DEFAULT 0"),
            ("outcome", "TEXT"),
            ("expires_at", "TIMESTAMP"),  # explicit per-entry TTL
            ("updated_at", "TIMESTAMP"),
            ("is_deleted", "INT DEFAULT 0"),
            ("deleted_at", "TIMESTAMP"),
        ]:
            try:
                conn.execute(f"ALTER TABLE memories ADD COLUMN {col_def[0]} {col_def[1]};")
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_deleted ON memories(is_deleted);")
        conn.commit()

    def _migrate_if_needed(self):
        """Import legacy JSONL data into SQLite if the table is empty."""
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count > 0:
            return

        jsonl_files = sorted(MEMU_DATA_DIR.glob("*.jsonl"))
        if not jsonl_files:
            return

        log.info(f"Migrating legacy JSONL data to SQLite ({len(jsonl_files)} files)...")
        imported = 0
        for fpath in jsonl_files:
            if fpath.name == "events.jsonl" or fpath.name.endswith(".wal.jsonl"):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            self._insert_entry_raw(conn, entry)
                            imported += 1
                        except Exception:
                            continue
            except Exception as e:
                log.warning(f"Migration error reading {fpath}: {e}")

        if imported:
            conn.commit()
            log.info(f"Migration complete: {imported} entries imported.")

    def _insert_entry_raw(self, conn: sqlite3.Connection, entry: dict):
        """Low-level insert using an existing connection (no commit — caller commits).
        INSERT OR IGNORE ensures idempotency via unique idempotency_key.
        """
        idem_key = entry.get("idempotency_key") or entry.get("request_id")
        # Fallback to content hash if no explicit idempotency key
        if not idem_key:
            idem_key = _content_hash(
                entry.get("content", ""),
                entry.get("agent_id", "shared"),
                entry.get("key", ""),
            )
        conn.execute("""
            INSERT OR IGNORE INTO memories (
                id, agent_id, user_id, idempotency_key, key, content,
                compressed_content, category, tags, auto_tags, metadata, compression,
                stored_at, expires_at, updated_at, is_deleted, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get("id") or str(uuid.uuid4()),
            entry.get("agent_id", "shared"),
            entry.get("user_id", "shared"),
            idem_key,
            entry.get("key", ""),
            entry.get("content", ""),
            entry.get("compressed_content", ""),
            entry.get("category", "general"),
            json.dumps(entry.get("tags", [])),
            json.dumps(entry.get("auto_tags", [])),
            json.dumps(entry.get("metadata", {})),
            json.dumps(entry.get("compression", {})),
            entry.get("stored_at", datetime.now(timezone.utc).isoformat()),
            entry.get("expires_at"),  # None = no explicit expiry
            entry.get("updated_at", entry.get("stored_at", datetime.now(timezone.utc).isoformat())),
            int(entry.get("is_deleted", 0) or 0),
            entry.get("deleted_at"),
        ))

    def _collect_garbage(self, force: bool = False):
        """TTL sweep: delete entries past global TTL *or* explicit expires_at.
        Runs at most every _GC_INTERVAL_SECONDS unless force=True.
        """
        now = time.monotonic()
        if not force and (now - self._last_gc) < _GC_INTERVAL_SECONDS:
            return
        self._last_gc = now
        now_iso = datetime.now(timezone.utc).isoformat()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=MEMU_TTL_DAYS)).isoformat()
        try:
            conn = self._get_conn()
            # Delete entries past global TTL OR past explicit expires_at
            res = conn.execute(
                "DELETE FROM memories WHERE stored_at < ? OR (expires_at IS NOT NULL AND expires_at < ?)",
                (cutoff, now_iso),
            )
            deleted = res.rowcount
            conn.commit()
            self._last_gc_deleted = deleted
            if deleted:
                log.info(f"GC removed {deleted} expired memU entries (TTL={MEMU_TTL_DAYS}d + explicit expires_at)")
        except Exception as e:
            log.warning(f"GC error: {e}")

    def _wal_checkpoint(self, force: bool = False):
        """Run WAL checkpoint to prevent unbounded WAL growth.

        Uses PASSIVE normally (non-blocking).  Escalates to TRUNCATE when
        the WAL exceeds 1 MB to reclaim disk space.
        """
        now = time.monotonic()
        if not force and (now - self._last_checkpoint) < _WAL_CHECKPOINT_INTERVAL:
            return
        self._last_checkpoint = now
        try:
            wal_path = Path(str(self.db_path) + "-wal")
            wal_bytes = wal_path.stat().st_size if wal_path.exists() else 0
            # Escalate to TRUNCATE if WAL exceeds 1 MB
            mode = "TRUNCATE" if wal_bytes > 1_048_576 else "PASSIVE"
            conn = self._get_conn()
            result = conn.execute(f"PRAGMA wal_checkpoint({mode});").fetchone()
            log.debug(f"WAL checkpoint({mode}): busy={result[0]} log={result[1]} checkpointed={result[2]} wal_bytes={wal_bytes}")
        except Exception as e:
            log.warning(f"WAL checkpoint error: {e}")

    def _periodic_maintenance(self):
        """Called after every write — runs GC and checkpoint if intervals have elapsed."""
        self._collect_garbage(force=False)
        self._wal_checkpoint()

    def _shutdown(self):
        """Graceful shutdown: final WAL checkpoint + close thread-local connections."""
        log.info("memU store shutting down — final checkpoint...")
        try:
            # Close any thread-local connection first
            local_conn = getattr(self._local, "conn", None)
            if local_conn:
                try:
                    local_conn.close()
                except Exception:
                    pass
                self._local.conn = None
            # Open a fresh connection just for the final checkpoint
            conn = sqlite3.connect(str(self.db_path), timeout=5)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.close()
            log.info("Final WAL checkpoint complete.")
        except Exception as e:
            log.warning(f"Shutdown checkpoint error: {e}")

    def store(self, payload: dict) -> tuple[dict, bool]:
        """Atomic store with idempotency. Returns (entry_dict, was_replay).

        Uses BEGIN IMMEDIATE to avoid SQLITE_BUSY between the idempotency
        check and the INSERT.  Rolls back on any failure so partial state
        never persists.  Periodic maintenance (GC / WAL checkpoint) runs
        *outside* the lock to avoid blocking concurrent writers.
        """
        agent_id = payload.get("agent_id", "shared")
        content = payload.get("content", "")
        key_field = payload.get("key", "")
        idem_key = payload.get("idempotency_key") or payload.get("request_id")

        # Content-hash fallback for implicit idempotency
        if not idem_key:
            idem_key = _content_hash(content, agent_id, key_field)

        # --- Pre-compute compression outside the lock (may call LLM) ---
        compressed, generated, provider = compress_stage1(content)
        auto_tags = extract_auto_tags(compressed) if generated else []

        with self.lock:
            conn = self._get_conn()
            try:
                # BEGIN IMMEDIATE acquires a reserved lock immediately,
                # preventing SQLITE_BUSY between check and insert.
                conn.execute("BEGIN IMMEDIATE;")

                # Check for existing entry with this idempotency key
                row = conn.execute(
                    "SELECT * FROM memories WHERE idempotency_key = ?", (idem_key,)
                ).fetchone()
                if row:
                    conn.execute("ROLLBACK;")
                    return self._row_to_dict(row), True

                # Resolve explicit expires_at (absolute ISO or relative like "+3h")
                raw_expires = payload.get("expires_at")
                expires_at = None
                if raw_expires:
                    if isinstance(raw_expires, str) and raw_expires.startswith("+"):
                        try:
                            val = raw_expires[1:]
                            if val.endswith("h"):
                                expires_at = (datetime.now(timezone.utc) + timedelta(hours=float(val[:-1]))).isoformat()
                            elif val.endswith("d"):
                                expires_at = (datetime.now(timezone.utc) + timedelta(days=float(val[:-1]))).isoformat()
                            elif val.endswith("m"):
                                expires_at = (datetime.now(timezone.utc) + timedelta(minutes=float(val[:-1]))).isoformat()
                        except Exception:
                            pass
                    else:
                        expires_at = str(raw_expires)

                entry = {
                    "id": str(uuid.uuid4()),
                    "agent_id": agent_id,
                    "user_id": payload.get("user_id", agent_id),
                    "idempotency_key": idem_key,
                    "key": key_field,
                    "content": content,
                    "compressed_content": compressed if compressed is not None else content,
                    "category": payload.get("category", "general"),
                    "tags": payload.get("tags", []),
                    "auto_tags": auto_tags,
                    "metadata": payload.get("metadata", {}),
                    "compression": {
                        "enabled": bool(provider),
                        "generated": bool(generated),
                        "provider": provider,
                    },
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": expires_at,
                }

                self._insert_entry_raw(conn, entry)
                conn.execute("COMMIT;")

            except Exception as e:
                # Roll back on ANY failure — never leave partial state
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                log.error(f"STORE FAILED (rolling back): {e}")
                raise

            log.info(f"STORE id={entry['id']} agent={agent_id} idem={idem_key[:20]} key={entry['key'][:60]!r}")

        # Audit + maintenance outside the lock (non-blocking)
        try:
            self._audit(entry["id"], "create", actor=agent_id, patch={}, before={}, after=entry)
        except Exception:
            pass

        try:
            self._periodic_maintenance()
        except Exception:
            pass

        return entry, False

    def search(self, query: str, agent_id: str = None, limit: int = 20) -> list:
        terms = [t.strip().lower() for t in re.split(r"\s+", query or "") if t.strip()]
        if not terms:
            return []

        # Require each term to match at least one searchable field (AND across terms).
        sql = "SELECT * FROM memories WHERE "
        params: list[Any] = []
        term_clauses = []
        for term in terms:
            like_term = f"%{term}%"
            term_clauses.append("(key LIKE ? OR content LIKE ? OR compressed_content LIKE ? OR category LIKE ?)")
            params.extend([like_term, like_term, like_term, like_term])

        sql += " AND ".join(term_clauses)
        sql += " AND COALESCE(is_deleted, 0) = 0"

        if agent_id and agent_id != "all":
            sql += " AND agent_id = ?"
            params.append(agent_id)

        sql += " ORDER BY stored_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_recent(self, agent_id: str = None, limit: int = 50) -> list:
        sql = "SELECT * FROM memories WHERE COALESCE(is_deleted, 0) = 0"
        params = []
        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        sql += " ORDER BY stored_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        for key in ["tags", "auto_tags", "metadata", "compression"]:
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError) as e:
                    log.warning(f"Corrupt JSON in column '{key}' for id={d.get('id', '?')}: {e}")
                    # Return safe defaults so callers don't crash
                    d[key] = [] if key in ("tags", "auto_tags") else {}
        return d



    def get_by_id(self, entry_id: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (entry_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def _audit(self, memory_id: str, action: str, actor: str | None = None, patch: dict | None = None,
               before: dict | None = None, after: dict | None = None) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO memory_audit (id, memory_id, action, actor, patch_json, before_json, after_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                memory_id,
                action,
                actor or "system",
                json.dumps(patch or {}),
                json.dumps(before or {}),
                json.dumps(after or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

    def update(self, entry_id: str, patch: dict, actor: str | None = None) -> dict | None:
        allowed = {"key", "content", "category", "tags", "metadata", "expires_at"}
        fields = {k: v for k, v in patch.items() if k in allowed}
        before = self.get_by_id(entry_id)
        if not before:
            return None
        if not fields:
            return before

        set_parts = []
        params: list[Any] = []
        for key, value in fields.items():
            if key in {"tags", "metadata"}:
                value = json.dumps(value if value is not None else ([] if key == "tags" else {}))
            set_parts.append(f"{key} = ?")
            params.append(value)

        now_iso = datetime.now(timezone.utc).isoformat()
        set_parts.append("updated_at = ?")
        params.append(now_iso)
        params.append(entry_id)

        conn = self._get_conn()
        conn.execute(f"UPDATE memories SET {', '.join(set_parts)} WHERE id = ?", params)
        conn.commit()
        after = self.get_by_id(entry_id)
        if after:
            self._audit(entry_id, "update", actor=actor, patch=fields, before=before, after=after)
        return after

    def delete(self, entry_id: str, actor: str | None = None, hard: bool = False) -> bool:
        before = self.get_by_id(entry_id)
        if not before:
            return False
        conn = self._get_conn()
        if hard:
            res = conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            conn.commit()
            if res.rowcount > 0:
                self._audit(entry_id, "delete-hard", actor=actor, patch={"hard": True}, before=before, after={})
            return res.rowcount > 0
        now_iso = datetime.now(timezone.utc).isoformat()
        res = conn.execute(
            "UPDATE memories SET is_deleted = 1, deleted_at = ?, updated_at = ? WHERE id = ?",
            (now_iso, now_iso, entry_id),
        )
        conn.commit()
        if res.rowcount > 0:
            after = self.get_by_id(entry_id)
            self._audit(entry_id, "delete-soft", actor=actor, patch={"hard": False}, before=before, after=after or {})
        return res.rowcount > 0

    def restore(self, entry_id: str, actor: str | None = None) -> dict | None:
        before = self.get_by_id(entry_id)
        if not before:
            return None
        conn = self._get_conn()
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE memories SET is_deleted = 0, deleted_at = NULL, updated_at = ? WHERE id = ?",
            (now_iso, entry_id),
        )
        conn.commit()
        after = self.get_by_id(entry_id)
        if after:
            self._audit(entry_id, "restore", actor=actor, patch={}, before=before, after=after)
        return after

    def history(self, agent_id: str | None = None, key: str | None = None, limit: int = 50) -> list:
        sql = "SELECT * FROM memories WHERE 1=1"
        params: list[Any] = []
        if agent_id and agent_id != "all":
            sql += " AND agent_id = ?"
            params.append(agent_id)
        if key:
            sql += " AND key LIKE ?"
            params.append(f"%{key}%")
        sql += " ORDER BY COALESCE(updated_at, stored_at) DESC LIMIT ?"
        params.append(limit)
        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def audit_trail(self, memory_id: str, limit: int = 50) -> list:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM memory_audit WHERE memory_id = ? ORDER BY created_at DESC LIMIT ?",
            (memory_id, limit),
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            for k in ("patch_json", "before_json", "after_json"):
                try:
                    d[k] = json.loads(d.get(k) or "{}")
                except Exception:
                    d[k] = {}
            out.append(d)
        return out
    def get_all(self, agent_id: str = None) -> list:
        sql = "SELECT * FROM memories WHERE COALESCE(is_deleted, 0) = 0"
        params = []
        if agent_id and agent_id != "all":
            sql += " AND agent_id = ?"
            params.append(agent_id)

        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]


_STORE = MemUStore(MEMU_DB_PATH)

_ASYNC_JOBS: dict[str, dict] = {}
_ASYNC_JOBS_LOCK = threading.Lock()


def _create_async_job(payload: dict) -> str:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _ASYNC_JOBS_LOCK:
        _ASYNC_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "result": None,
            "error": None,
        }

    def _runner() -> None:
        with _ASYNC_JOBS_LOCK:
            _ASYNC_JOBS[job_id]["status"] = "running"
            _ASYNC_JOBS[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            result = store_entry(payload)
            with _ASYNC_JOBS_LOCK:
                _ASYNC_JOBS[job_id]["status"] = "done"
                _ASYNC_JOBS[job_id]["result"] = result
                _ASYNC_JOBS[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            with _ASYNC_JOBS_LOCK:
                _ASYNC_JOBS[job_id]["status"] = "failed"
                _ASYNC_JOBS[job_id]["error"] = str(exc)
                _ASYNC_JOBS[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    threading.Thread(target=_runner, daemon=True).start()
    return job_id


def _get_async_job(job_id: str) -> Optional[dict]:
    with _ASYNC_JOBS_LOCK:
        job = _ASYNC_JOBS.get(job_id)
        return dict(job) if job else None


def store_entry(payload: dict) -> dict:
    """Store a memory entry. Returns stored record and idempotency flag."""
    entry, replayed = _STORE.store(payload)
    entry = dict(entry)
    entry["_resumed"] = bool(replayed)
    return entry

def search_entries(query: str, agent_id: str = None, limit: int = 20) -> list:
    return _STORE.search(query, agent_id, limit)

def list_entries(agent_id: str = None, limit: int = 50) -> list:
    return _STORE.list_recent(agent_id, limit)

def update_entry(entry_id: str, patch: dict, actor: str | None = None) -> dict | None:
    return _STORE.update(entry_id, patch, actor=actor)

def delete_entry(entry_id: str, actor: str | None = None, hard: bool = False) -> bool:
    return _STORE.delete(entry_id, actor=actor, hard=hard)

def restore_entry(entry_id: str, actor: str | None = None) -> dict | None:
    return _STORE.restore(entry_id, actor=actor)

def history_entries(agent_id: str | None = None, key: str | None = None, limit: int = 50) -> list:
    return _STORE.history(agent_id=agent_id, key=key, limit=limit)

def audit_entries(memory_id: str, limit: int = 50) -> list:
    return _STORE.audit_trail(memory_id=memory_id, limit=limit)

def fused_search(query: str, agent_id: str = None, limit: int = 20) -> list:
    lexical = search_entries(query=query, agent_id=agent_id, limit=max(limit * 2, limit))
    semantic = tfidf_search(query=query, agent_id=agent_id, limit=max(limit * 2, limit))

    rank: dict[str, dict] = {}
    k = 60.0
    for i, row in enumerate(lexical):
        rid = row.get("id")
        if not rid:
            continue
        rank.setdefault(rid, {"row": row, "score": 0.0, "sources": set()})
        rank[rid]["score"] += 1.0 / (k + i + 1)
        rank[rid]["sources"].add("lexical")
    for i, row in enumerate(semantic):
        rid = row.get("id")
        if not rid:
            continue
        rank.setdefault(rid, {"row": row, "score": 0.0, "sources": set()})
        rank[rid]["score"] += 1.0 / (k + i + 1)
        rank[rid]["sources"].add("semantic")

    fused = []
    for item in rank.values():
        out = dict(item["row"])
        out["_fusion_score"] = round(item["score"], 6)
        out["_sources"] = sorted(item["sources"])
        out["_search_type"] = "hybrid-rrf"
        fused.append(out)
    fused.sort(key=lambda x: x.get("_fusion_score", 0), reverse=True)
    return fused[:limit]

# ── TF-IDF Semantic Search ────────────────────────────────────────────────────

def _tokenize(text: str) -> list:
    """Lowercase + split on non-alphanumeric boundaries."""
    return re.findall(r'[a-z0-9]+', text.lower())

def _entry_to_text(entry: dict) -> str:
    """Flatten entry fields into a single searchable text blob."""
    parts = [
        entry.get("key", ""),
        entry.get("content", ""),
        entry.get("category", ""),
        " ".join(entry.get("tags", [])),
    ]
    meta = entry.get("metadata", {})
    if isinstance(meta, dict):
        parts.append(meta.get("context_summary", ""))
        parts.append(meta.get("compressed_content", ""))
    return " ".join(p for p in parts if p)

def _recency_factor(stored_at_str: str, half_life_hours: float = 168.0) -> float:
    """Exponential decay factor based on age. half_life_hours=168 means 7 days."""
    try:
        stored_at = datetime.fromisoformat(stored_at_str)
        if stored_at.tzinfo is None:
            stored_at = stored_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - stored_at).total_seconds() / 3600.0
        decay_lambda = math.log(2) / half_life_hours
        return math.exp(-decay_lambda * max(age_hours, 0))
    except Exception:
        return 0.5  # safe fallback for unparseable timestamps


def _use_count_boost(entry: dict) -> float:
    """Logarithmic boost for entries that have been accessed more (1.0–1.6x)."""
    use_count = 0
    if isinstance(entry.get("use_count"), (int, float)):
        use_count = int(entry["use_count"])
    elif isinstance(entry.get("metadata"), dict):
        use_count = int(entry["metadata"].get("use_count", 0))
    return 1.0 + 0.2 * math.log1p(use_count)


def tfidf_search(query: str, agent_id: str = None, limit: int = 20) -> list:
    corpus = _STORE.get_all(agent_id=agent_id)
    if not corpus:
        return []

    query_terms = _tokenize(query)
    if not query_terms:
        return []

    # Tokenize each document once
    doc_tokens = [_tokenize(_entry_to_text(e)) for e in corpus]
    N = len(corpus)

    # IDF per unique query term (smoothed to avoid zero-division)
    idf = {}
    for term in set(query_terms):
        df = sum(1 for tokens in doc_tokens if term in tokens)
        idf[term] = math.log((N + 1) / (df + 1)) + 1.0

    # Score each document — TF-IDF × recency decay × use-count boost
    scored = []
    for entry, tokens in zip(corpus, doc_tokens):
        if not tokens:
            continue
        token_count = len(tokens)
        tfidf_score = 0.0
        for term in query_terms:
            tf = tokens.count(term) / token_count
            tfidf_score += tf * idf.get(term, 0.0)
        if tfidf_score > 0.0:
            recency = _recency_factor(entry.get("stored_at", ""))
            use_boost = _use_count_boost(entry)
            final_score = tfidf_score * recency * use_boost
            entry_copy = dict(entry)
            entry_copy["_score"] = round(final_score, 6)
            entry_copy["_tfidf_raw"] = round(tfidf_score, 6)
            entry_copy["_recency_factor"] = round(recency, 4)
            entry_copy["_use_boost"] = round(use_boost, 4)
            entry_copy["_search_type"] = "tfidf+recency+use"
            scored.append(entry_copy)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    log.info(f"TFIDF+recency query={query!r} corpus={N} hits={len(scored)} top_score={scored[0]['_score'] if scored else 0}")
    return scored[:limit]


# ── HTTP Handler ─────────────────────────────────────────────────────────────
class MemUHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default access log (we use our own)

    def send_json(self, status: int, body: dict):
        safe_body = _redact_payload(body)
        data = json.dumps(safe_body, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def check_auth(self, path: str, body: dict | None = None) -> tuple[bool, str, str]:
        write_paths = {"/api/v1/memu/store", "/api/v1/memu/log_event", "/api/v1/memu/update", "/api/v1/memu/delete", "/api/v1/memu/restore"}
        read_paths = {"/api/v1/memu/search", "/api/v1/memu/semantic-search", "/api/v1/memu/list", "/api/v1/memu/pulse", "/api/v1/memu/health", "/api/v1/memu/history", "/api/v1/memu/audit"}
        auth = self.headers.get("Authorization", "")
        token = _parse_authorization(auth) if auth else ""

        # Also allow api_key query param
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if not token and "api_key" in params and params["api_key"]:
            token = params["api_key"][0]

        # Keep health probe unauthenticated for local liveness checks (HEARTBEAT.md contract)
        if path == "/api/v1/memu/health" and not token:
            return True, "ok", "none"
            
        # Add canonical/direct aliases to auth checks
        if path in {"/memorize", "/memories", "/store"}:
            path = "/api/v1/memu/store"
        if path in {"/retrieve", "/search"}:
            path = "/api/v1/memu/search"
        if path == "/health":
            path = "/api/v1/memu/health"

        if not token:
            return False, "missing", "none"

        scope = _check_token_scope(token)
        if not scope:
            return False, "invalid-token", "none"

        if path in write_paths and scope != "write":
            return False, "read-only-token", scope
        if (path in read_paths or path.startswith("/api/v1/memu/jobs/")) and scope not in {"read", "write"}:
            return False, "invalid-scope", "none"

        allowed, reason = _validate_actor_access(self.headers, body or {})
        if not allowed:
            return False, reason, scope

        return True, "ok", scope

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Resolve canonical/direct aliases
        if path == "/health":
            path = "/api/v1/memu/health"
        elif path == "/memories":
            path = "/api/v1/memu/list"
        elif path == "/history":
            path = "/api/v1/memu/history"
        elif path == "/audit":
            path = "/api/v1/memu/audit"
        elif path.startswith("/jobs/"):
            path = "/api/v1/memu/jobs/" + path.split("/jobs/", 1)[1]

        ok, reason, _ = self.check_auth(path)
        if not ok:
            self.send_json(401 if reason in {"missing", "invalid-token", "invalid-scope", "read-only-token"} else 403, {"error": f"Unauthorized: {reason}"})
            return

        if path == "/api/v1/memu/health":
            # Compute WAL size for monitoring
            wal_path = Path(str(MEMU_DB_PATH) + "-wal")
            wal_bytes = wal_path.stat().st_size if wal_path.exists() else 0
            db_bytes = MEMU_DB_PATH.stat().st_size if MEMU_DB_PATH.exists() else 0
            # Proactive: trigger checkpoint if WAL > 512 KB on health probe
            if wal_bytes > 524_288:
                try:
                    _STORE._wal_checkpoint(force=True)
                    wal_bytes = wal_path.stat().st_size if wal_path.exists() else 0
                except Exception:
                    pass
            # Fetch row count + GC stats
            try:
                conn = _STORE._get_conn()
                row_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                expired_count = 0
                now_iso = datetime.now(timezone.utc).isoformat()
                cutoff = (datetime.now(timezone.utc) - timedelta(days=MEMU_TTL_DAYS)).isoformat()
                expired_count = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE stored_at < ? OR (expires_at IS NOT NULL AND expires_at < ?)",
                    (cutoff, now_iso),
                ).fetchone()[0]
            except Exception:
                row_count = -1
                expired_count = 0

            security_ok, security_note = _weekly_security_health_ok(days=7)
            self.send_json(200, {
                "status": "ok",
                "service": "memU bridge",
                "version": "2.4.0",
                "features": [
                    "sqlite-storage", "like-and-tfidf-search", "tfidf-semantic-search",
                    "recency-decay", "use-count-boost", "idempotency",
                    "content-hash-dedup", "event-stream",
                    "wal-auto-checkpoint", "wal-threshold-escalation",
                    "periodic-gc", "crash-recovery",
                    "atomic-event-log", "thread-local-conn-pool",
                    "begin-immediate", "explicit-rollback",
                    "health-triggered-checkpoint",
                    "expires-at-ttl", "event-log-rotation",
                    "connection-recovery",
                    "lifecycle-endpoints",
                    "soft-delete-restore",
                    "audit-trail",
                    "typed-schema-validation",
                    "hybrid-search-fusion",
                    "async-ingestion" if MEMU_ASYNC_INGEST_ENABLED else "async-ingestion-disabled",
                    "strict-schema-mode" if MEMU_STRICT_SCHEMA_MODE else "strict-schema-mode-disabled",
                ],
                "db_path": str(MEMU_DB_PATH),
                "db_bytes": db_bytes,
                "wal_bytes": wal_bytes,
                "row_count": row_count,
                "pending_gc": expired_count,
                "ttl_days": MEMU_TTL_DAYS,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "weekly_security_ok": security_ok,
                "security_audit": security_note,
            })
            return

        if path.startswith("/api/v1/memu/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            job = _get_async_job(job_id)
            if not job:
                self.send_json(404, {"error": "Unknown job_id", "job_id": job_id})
                return
            self.send_json(200, job)
            return

        if path == "/api/v1/memu/pulse":
            ledger_path = MEMU_DATA_DIR / "events.jsonl"
            events = []
            if ledger_path.exists():
                try:
                    with open(ledger_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        limit = int(params.get("limit", [20])[0])
                        for line in lines[-limit:]:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                events.append(json.loads(line))
                            except json.JSONDecodeError:
                                # Skip truncated/corrupt lines (crash recovery)
                                log.debug(f"Skipping corrupt event line: {line[:80]}")
                except Exception as e:
                    log.warning(f"Error reading pulse: {e}")
            self.send_json(200, {"events": events})
            return

        if path == "/api/v1/memu/list":
            # already authorized by endpoint-level auth above
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            agent_id = params.get("agent_id", [None])[0]
            limit = int(params.get("limit", [50])[0])
            entries = list_entries(agent_id=agent_id, limit=limit)
            self.send_json(200, {"entries": entries, "count": len(entries)})
            return

        if path == "/api/v1/memu/history":
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            agent_id = params.get("agent_id", [None])[0]
            key = params.get("key", [None])[0]
            limit = int(params.get("limit", [50])[0])
            entries = history_entries(agent_id=agent_id, key=key, limit=limit)
            self.send_json(200, {"entries": entries, "count": len(entries)})
            return

        if path == "/api/v1/memu/audit":
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            memory_id = params.get("memory_id", [""])[0]
            if not memory_id:
                self.send_json(400, {"error": "Missing required query param: memory_id"})
                return
            limit = int(params.get("limit", [50])[0])
            entries = audit_entries(memory_id=memory_id, limit=limit)
            self.send_json(200, {"entries": entries, "count": len(entries), "memory_id": memory_id})
            return

        self.send_json(404, {"error": f"Unknown endpoint: {path}"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self.read_body()

        # Resolve canonical/direct aliases
        if path in {"/memorize", "/memories", "/store"}:
            path = "/api/v1/memu/store"
        if path in {"/retrieve", "/search"}:
            path = "/api/v1/memu/search"
        if path == "/restore":
            path = "/api/v1/memu/restore"

        ok, reason, _ = self.check_auth(path, body=body)
        if not ok:
            self.send_json(401 if reason in {"missing", "invalid-token", "invalid-scope", "read-only-token"} else 403, {"error": f"Unauthorized: {reason}"})
            return


        if path == "/api/v1/memu/log_event":
            # Immutable event stream — atomic append with fsync + rotation
            if not body.get("event_type") or not body.get("agent_id"):
                self.send_json(400, {"error": "Missing event_type or agent_id"})
                return
            
            evt = body.copy()
            evt["id"] = str(uuid.uuid4())
            if not evt.get("timestamp"):
                evt["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            ledger_path = MEMU_DATA_DIR / "events.jsonl"
            line = json.dumps(evt, ensure_ascii=False) + "\n"
            try:
                # Rotate if file exceeds max size
                if ledger_path.exists() and ledger_path.stat().st_size > _EVENT_LOG_MAX_BYTES:
                    rotated = MEMU_DATA_DIR / "events.jsonl.1"
                    try:
                        if rotated.exists():
                            rotated.unlink()
                        ledger_path.rename(rotated)
                        log.info(f"Event log rotated ({_EVENT_LOG_MAX_BYTES} bytes threshold)")
                    except Exception as e:
                        log.warning(f"Event log rotation failed: {e}")

                fd = os.open(str(ledger_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                try:
                    os.write(fd, line.encode("utf-8"))
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError as e:
                log.error(f"Event log write failed: {e}")
                self.send_json(500, {"error": f"Event write failed: {e}"})
                return
            
            self.send_json(200, {"status": "logged", "event_id": evt["id"], "timestamp": evt["timestamp"]})
            return

        if path == "/api/v1/memu/store":
            # Direct-contract compatibility: map /memories payload shape
            if not body.get("content") and body.get("value"):
                body = dict(body)
                body["content"] = body.get("value")
            if not body.get("agent_id") and body.get("agent"):
                body = dict(body)
                body["agent_id"] = body.get("agent")

            # Canonical alias compatibility: accept /memorize payloads with messages[]
            if not body.get("content") and isinstance(body.get("messages"), list):
                parts = []
                for m in body.get("messages", []):
                    if not isinstance(m, dict):
                        continue
                    c = m.get("content")
                    if isinstance(c, dict):
                        c = c.get("text") or c.get("value") or ""
                    if c:
                        role = m.get("role") or "msg"
                        parts.append(f"{role}: {str(c)}")
                if parts:
                    body = dict(body)
                    body["content"] = "\n".join(parts)
                    body.setdefault("category", "conversation")

            # Normalize required typed fields before strict schema validation
            if not body.get("user_id"):
                body = dict(body)
                body["user_id"] = body.get("agent_id") or body.get("agent") or "shared"
            if not _extract_session_value(body):
                body = dict(body)
                body["session_id"] = str(body.get("key") or body.get("idempotency_key") or "default-session")[:128]

            is_valid, schema_reason = _validate_store_schema(body, strict=MEMU_STRICT_SCHEMA_MODE)
            if not is_valid:
                self.send_json(400, {"error": schema_reason})
                return

            if not body.get("content") and not body.get("key"):
                self.send_json(400, {"error": "Missing required field: content or key"})
                return
            content = str(body.get("content") or "")
            _, flags = _sanitize_text(content)
            semantic_risk = _semantic_scan_for_injection(content, context="store")
            if semantic_risk == "high" and _is_high_risk_source(body):
                self.send_json(403, {"error": "Blocked due to injection risk in high-risk source", "risk": semantic_risk, "signals": flags})
                return
            if flags:
                body = dict(body)
                body["content"] = f"{HIGH_RISK_MARKER_PREFIX} {flags[0]} {content}"
                body["security_risk"] = {
                    "deterministic_flags": flags,
                    "semantic_risk": semantic_risk,
                }
            elif semantic_risk:
                # Keep soft-risk signals in metadata only to avoid polluting stored content
                # for benign writes (previous behavior prefixed nearly all content with [RISK]).
                body = dict(body)
                body.setdefault("security_risk", {"semantic_risk": semantic_risk, "deterministic_flags": flags})

            prefer_header = (self.headers.get("Prefer") or "").lower()
            wants_async = bool(body.get("async")) or "respond-async" in prefer_header
            if wants_async:
                if not MEMU_ASYNC_INGEST_ENABLED:
                    self.send_json(400, {"error": "Async ingestion mode is disabled"})
                    return
                job_id = _create_async_job(dict(body))
                self.send_json(202, {
                    "ok": True,
                    "status": "accepted",
                    "job_id": job_id,
                    "status_url": f"/api/v1/memu/jobs/{job_id}",
                })
                return

            entry = store_entry(body)
            is_idempotent = bool(entry.pop("_resumed", False))
            self.send_json(200, {
                "ok": True,
                "id": entry["id"],
                "stored_at": entry["stored_at"],
                "idempotent": is_idempotent,
                "entry": entry,
            })
            return

        if path == "/api/v1/memu/search":
            if not body.get("agent_id") and body.get("agent"):
                body = dict(body)
                body["agent_id"] = body.get("agent")
            is_valid, schema_reason = _validate_search_schema(body, strict=MEMU_STRICT_SCHEMA_MODE)
            if not is_valid:
                self.send_json(400, {"error": schema_reason})
                return
            query = str(body.get("query", ""))
            # Canonical alias compatibility: accept /retrieve payloads with messages[]
            if not query and isinstance(body.get("messages"), list):
                for m in reversed(body.get("messages", [])):
                    if not isinstance(m, dict):
                        continue
                    c = m.get("content")
                    if isinstance(c, dict):
                        c = c.get("text") or c.get("value") or ""
                    if c:
                        query = str(c)
                        break
            if not query:
                self.send_json(400, {"error": "Missing required field: query"})
                return
            _, qflags = _sanitize_text(query)
            if qflags:
                body = dict(body)
                body["query_risk"] = {"deterministic_flags": qflags}
            agent_id = body.get("agent_id", None)
            limit = int(body.get("limit", 20))
            use_hybrid = bool(body.get("hybrid", True))
            results = fused_search(query=query, agent_id=agent_id, limit=limit) if use_hybrid else search_entries(query=query, agent_id=agent_id, limit=limit)
            self.send_json(200, {"results": results, "count": len(results), "query": query, "risk": bool(qflags), "method": "hybrid-rrf" if use_hybrid else "lexical"})
            return


        if path == "/api/v1/memu/update":
            entry_id = str(body.get("id", "")).strip()
            if not entry_id:
                self.send_json(400, {"error": "Missing required field: id"})
                return
            patch = {k: v for k, v in body.items() if k in {"key", "content", "category", "tags", "metadata", "expires_at"}}
            actor = body.get("actor") or body.get("agent_id") or body.get("user_id") or "system"
            entry = update_entry(entry_id, patch, actor=str(actor))
            if not entry:
                self.send_json(404, {"error": "Entry not found", "id": entry_id})
                return
            self.send_json(200, {"ok": True, "id": entry_id, "entry": entry})
            return

        if path == "/api/v1/memu/delete":
            entry_id = str(body.get("id", "")).strip()
            if not entry_id:
                self.send_json(400, {"error": "Missing required field: id"})
                return
            actor = body.get("actor") or body.get("agent_id") or body.get("user_id") or "system"
            hard = bool(body.get("hard", False))
            deleted = delete_entry(entry_id, actor=str(actor), hard=hard)
            if not deleted:
                self.send_json(404, {"error": "Entry not found", "id": entry_id})
                return
            self.send_json(200, {"ok": True, "id": entry_id, "deleted": True, "mode": "hard" if hard else "soft"})
            return

        if path == "/api/v1/memu/restore":
            entry_id = str(body.get("id", "")).strip()
            if not entry_id:
                self.send_json(400, {"error": "Missing required field: id"})
                return
            actor = body.get("actor") or body.get("agent_id") or body.get("user_id") or "system"
            restored = restore_entry(entry_id, actor=str(actor))
            if not restored:
                self.send_json(404, {"error": "Entry not found", "id": entry_id})
                return
            self.send_json(200, {"ok": True, "id": entry_id, "restored": True, "entry": restored})
            return

        if path == "/api/v1/memu/semantic-search":
            query = str(body.get("query", ""))
            if not query:
                self.send_json(400, {"error": "Missing required field: query"})
                return
            _, qflags = _sanitize_text(query)
            if qflags:
                body = dict(body)
                body["query_risk"] = {"deterministic_flags": qflags}
            agent_id = body.get("agent_id", None)
            limit = int(body.get("limit", 20))
            results = tfidf_search(query=query, agent_id=agent_id, limit=limit)
            self.send_json(200, {
                "results": results,
                "count": len(results),
                "query": query,
                "method": "tfidf",
                "risk": bool(qflags),
                "note": "TF-IDF ranking (pure Python). Upgrade to fastembed/openai-embeddings for neural semantic search."
            })
            return

        self.send_json(404, {"error": f"Unknown endpoint: {path}"})


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if MEMU_BIND_HOST not in {"127.0.0.1", "localhost", "::1"}:
        log.warning(f"Non-loopback bind requested ({MEMU_BIND_HOST}); forcing loopback for security.")
        MEMU_BIND_HOST = "127.0.0.1"

    server = HTTPServer((MEMU_BIND_HOST, PORT), MemUHandler)
    SECURITY_AUDIT_MARKER.parent.mkdir(parents=True, exist_ok=True)
    if not SECURITY_AUDIT_MARKER.exists():
        SECURITY_AUDIT_MARKER.write_text(json.dumps({"created": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    log.info(f"memU bridge server binding: {MEMU_BIND_HOST}:{PORT}")
    log.info(f"memU bridge server starting on port {PORT}")
    log.info(f"Memory store (SQLite): {MEMU_DB_PATH}")
    log.info(f"API Key: {API_KEY[:8]}...")
    log.info("Endpoints:")
    log.info(f"  GET  http://localhost:{PORT}/api/v1/memu/health")
    log.info(f"  POST http://localhost:{PORT}/api/v1/memu/store")
    log.info(f"  POST http://localhost:{PORT}/api/v1/memu/search          (hybrid lexical+TFIDF)")
    log.info(f"  POST http://localhost:{PORT}/api/v1/memu/semantic-search (TF-IDF ranked)")
    log.info(f"  POST http://localhost:{PORT}/api/v1/memu/update | /delete | /restore")
    log.info(f"  GET  http://localhost:{PORT}/api/v1/memu/list | /history | /audit")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("memU server stopped.")
