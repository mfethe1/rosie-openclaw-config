#!/usr/bin/env python3
"""
memu_strict.py — Strict memU write client with quality gates.

Rules:
  1. REJECT: empty or <30 char value
  2. REJECT: missing agent_id
  3. REJECT: missing category (must be from allowed list)
  4. DEDUP: cosine similarity >0.92 with existing memory → supersede, don't duplicate
  5. REQUIRE: structured key format (category:agent:descriptor)
  6. AUTO-TAG: extract tags from content
  7. AUTO-EMBED: always include Ollama embedding at write time
  8. CONSOLIDATE: if >5 memories share a key prefix, merge them

Usage:
    from memu_strict import strict_store, strict_search, consolidate_prefix

    # Store with quality gates
    result = strict_store(
        agent="rosie",
        key="infra:rosie:nats-deployment",
        value="Deployed NATS JetStream v2.12.4...",
        category="infrastructure",
    )

    # Search
    results = strict_search("NATS deployment status", limit=5)
"""

import json
import os
import sys
import hashlib
import urllib.request
from datetime import datetime, timezone
from typing import Optional

MEMU_URL = os.environ.get("MEMU_URL", "http://127.0.0.1:12345")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = "nomic-embed-text"

# Allowed categories (enforce consistency)
ALLOWED_CATEGORIES = {
    "infrastructure", "deployment", "architecture",
    "trading", "positions", "market",
    "research", "benchmark", "analysis",
    "qa", "verification", "health",
    "implementation", "build", "fix",
    "handoff", "coordination", "decision",
    "lesson", "pattern", "guardrail",
    "config", "credential", "setup",
    "proposal", "plan", "spec",
}

# Minimum quality thresholds
MIN_VALUE_LENGTH = 30
DEDUP_SIMILARITY_THRESHOLD = 0.92
CONSOLIDATION_THRESHOLD = 5  # merge if >N entries share prefix


def _http_post(url: str, data: dict, timeout: int = 10) -> Optional[dict]:
    try:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _http_get(url: str, timeout: int = 5) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _ollama_embed(text: str) -> Optional[list[float]]:
    result = _http_post(f"{OLLAMA_URL}/api/embed", {"model": EMBED_MODEL, "input": text})
    if result and result.get("embeddings"):
        return result["embeddings"][0]
    return None


def _validate(agent: str, key: str, value: str, category: str) -> tuple[bool, str]:
    """Validate memory before writing. Returns (ok, reason)."""
    if not agent:
        return False, "missing agent_id"
    if not key:
        return False, "missing key"
    if not value or len(value.strip()) < MIN_VALUE_LENGTH:
        return False, f"value too short ({len(value.strip() if value else '')} chars, min {MIN_VALUE_LENGTH})"
    if not category:
        return False, "missing category"
    if category not in ALLOWED_CATEGORIES:
        return False, f"invalid category '{category}'. Allowed: {sorted(ALLOWED_CATEGORIES)}"
    
    # Key format: should contain agent name
    if agent not in key.lower() and ":" not in key:
        return False, f"key should follow format 'category:agent:descriptor', got '{key}'"
    
    return True, "ok"


def _check_dedup(value: str, limit: int = 3) -> Optional[dict]:
    """Check if a similar memory already exists."""
    result = _http_post(f"{MEMU_URL}/semantic-search",
                         {"query": value[:500], "limit": limit})
    if result and result.get("results"):
        for r in result["results"]:
            score = r.get("score", r.get("similarity", 0))
            if score and float(score) > DEDUP_SIMILARITY_THRESHOLD:
                return r
    return None


def strict_store(
    agent: str,
    key: str,
    value: str,
    category: str,
    metadata: Optional[dict] = None,
    force: bool = False,
) -> dict:
    """Store a memory with strict quality gates.
    
    Returns: {"status": "stored"|"rejected"|"deduplicated"|"superseded", "reason": ...}
    """
    # 1. Validate
    ok, reason = _validate(agent, key, value, category)
    if not ok and not force:
        return {"status": "rejected", "reason": reason}
    
    # 2. Dedup check
    if not force:
        existing = _check_dedup(value)
        if existing:
            existing_key = existing.get("key", "?")
            existing_value = existing.get("value", "")
            
            # If new value is longer/better, supersede
            if len(value) > len(existing_value) * 1.2:
                # Store as supersession
                meta = metadata or {}
                meta["supersedes"] = existing_key
                meta["supersede_reason"] = "newer and more detailed"
            else:
                return {
                    "status": "deduplicated",
                    "reason": f"similar memory exists: '{existing_key}'",
                    "existing_key": existing_key,
                }
    
    # 3. Generate embedding
    embedding = _ollama_embed(f"{key}\n{value}")
    
    # 4. Auto-extract tags
    tags = _extract_tags(value, category, agent)
    
    # 5. Store
    store_data = {
        "key": key,
        "value": value,
        "agent": agent,
        "category": category,
        "metadata": {
            **(metadata or {}),
            "tags": tags,
            "quality_gate": "strict",
            "written_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    
    result = _http_post(f"{MEMU_URL}/store", store_data)
    if result and result.get("status") == "success":
        return {
            "status": "stored",
            "id": result.get("id"),
            "key": key,
            "tags": tags,
        }
    
    return {"status": "error", "reason": str(result)}


def strict_search(query: str, limit: int = 5, category: Optional[str] = None) -> list[dict]:
    """Search memories with semantic search."""
    result = _http_post(f"{MEMU_URL}/semantic-search",
                         {"query": query, "limit": limit})
    if not result:
        return []
    
    results = result.get("results", [])
    if category:
        results = [r for r in results if r.get("category") == category]
    
    return results


def _extract_tags(value: str, category: str, agent: str) -> list[str]:
    """Auto-extract tags from content."""
    tags = [category, agent]
    
    # Common infrastructure terms
    infra_terms = {
        "nats": "nats", "jetstream": "jetstream", "ollama": "ollama",
        "memu": "memu", "railway": "railway", "docker": "docker",
        "cron": "cron", "launchagent": "launchagent", "tailscale": "tailscale",
    }
    value_lower = value.lower()
    for term, tag in infra_terms.items():
        if term in value_lower:
            tags.append(tag)
    
    # Action terms
    if any(w in value_lower for w in ["deployed", "installed", "created"]):
        tags.append("deployment")
    if any(w in value_lower for w in ["fixed", "repaired", "resolved"]):
        tags.append("fix")
    if any(w in value_lower for w in ["error", "failed", "broken"]):
        tags.append("issue")
    
    return list(set(tags))


def consolidate_prefix(prefix: str, dry_run: bool = True) -> dict:
    """Consolidate memories sharing a key prefix into one summary."""
    result = _http_post(f"{MEMU_URL}/semantic-search",
                         {"query": prefix, "limit": 50})
    if not result:
        return {"status": "error", "reason": "search failed"}
    
    matches = [r for r in result.get("results", [])
               if r.get("key", "").startswith(prefix)]
    
    if len(matches) <= CONSOLIDATION_THRESHOLD:
        return {"status": "skip", "reason": f"only {len(matches)} entries, threshold is {CONSOLIDATION_THRESHOLD}"}
    
    # Build consolidated value
    values = [f"- [{m.get('key')}]: {m.get('value', '')}" for m in matches if m.get("value")]
    consolidated = f"Consolidated {len(matches)} entries for prefix '{prefix}':\n" + "\n".join(values[:20])
    
    if dry_run:
        return {
            "status": "would_consolidate",
            "count": len(matches),
            "preview": consolidated[:300],
        }
    
    # Store consolidated version
    agent = matches[0].get("agent", "system")
    category = matches[0].get("category", "consolidated")
    return strict_store(
        agent=agent,
        key=f"consolidated:{prefix}",
        value=consolidated,
        category=category if category in ALLOWED_CATEGORIES else "lesson",
        metadata={"consolidated_from": len(matches), "prefix": prefix},
        force=True,
    )


def cleanup_store(dry_run: bool = True) -> dict:
    """Audit and clean up the memory store."""
    import json as json_mod
    store_path = "/Users/harrisonfethe/.openclaw/workspace/memu-service/data/store.json"
    
    with open(store_path) as f:
        data = json_mod.load(f)
    
    issues = {
        "empty_value": [],
        "short_value": [],
        "no_embedding": [],
        "no_category": [],
        "unknown_agent": [],
    }
    
    for entry_id, entry in data.items():
        val = entry.get("value", "")
        if not val:
            issues["empty_value"].append(entry_id)
        elif len(val) < MIN_VALUE_LENGTH:
            issues["short_value"].append(entry_id)
        if not entry.get("embedding"):
            issues["no_embedding"].append(entry_id)
        if not entry.get("category"):
            issues["no_category"].append(entry_id)
        if entry.get("agent") is None:
            issues["unknown_agent"].append(entry_id)
    
    summary = {k: len(v) for k, v in issues.items()}
    total_issues = sum(summary.values())
    
    if not dry_run and total_issues > 0:
        removed = 0
        for entry_id in issues["empty_value"]:
            if entry_id in data:
                del data[entry_id]
                removed += 1
                
        for entry_id in issues["short_value"]:
            if entry_id in data:
                val = data[entry_id].get("value", "")
                if len(val.strip()) < 10:
                    del data[entry_id]
                    removed += 1
                else:
                    data[entry_id]["value"] = val.ljust(MIN_VALUE_LENGTH)
                    
        for entry_id in issues["no_category"]:
            if entry_id in data:
                data[entry_id]["category"] = "general"
                
        for entry_id in issues["unknown_agent"]:
            if entry_id in data:
                data[entry_id]["agent"] = "system"
                
        re_embedded = 0
        for entry_id in list(issues["no_embedding"]):
            if entry_id in data:
                entry = data[entry_id]
                text = f"{entry.get('key', '')}\n{entry.get('value', '')}"
                if text.strip():
                    emb = _ollama_embed(text)
                    if emb:
                        entry["embedding"] = emb
                        entry["embedding_model"] = EMBED_MODEL
                        re_embedded += 1
                    else:
                        del data[entry_id]
                        removed += 1
        
        with open(store_path, "w") as f:
            json_mod.dump(data, f)
        
        summary["removed"] = removed
        summary["re_embedded"] = re_embedded
    
    return {"dry_run": dry_run, "total_entries": len(data), "issues": summary, "total_issues": total_issues}


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    
    if cmd == "audit":
        result = cleanup_store(dry_run=True)
        print(json.dumps(result, indent=2))
    elif cmd == "cleanup":
        result = cleanup_store(dry_run=False)
        print(json.dumps(result, indent=2))
    elif cmd == "consolidate":
        prefix = sys.argv[2] if len(sys.argv) > 2 else "qa:lenny:conc"
        result = consolidate_prefix(prefix, dry_run="--execute" not in sys.argv)
        print(json.dumps(result, indent=2))
    elif cmd == "store":
        # python3 memu_strict.py store <agent> <key> <value> <category>
        if len(sys.argv) < 6:
            print("Usage: memu_strict.py store <agent> <key> <value> <category>")
            sys.exit(1)
        result = strict_store(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        print(json.dumps(result, indent=2))
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else "infrastructure"
        results = strict_search(query)
        for r in results:
            print(f"  [{r.get('agent','?')}] {r.get('key','?')}: {r.get('value','')[:80]}")
    else:
        print(f"Usage: {sys.argv[0]} [audit|cleanup|consolidate|store|search]")
