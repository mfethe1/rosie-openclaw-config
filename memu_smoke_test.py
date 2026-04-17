import os
import requests
import uuid
import json
import time

BASE_URL = os.environ.get("MEMU_URL", "http://localhost:12345").rstrip("/")
API_PREFIX = "/api/v1/memu"

def smoke_test():
    unique_id = str(uuid.uuid4())
    content = f"Smoke test content {unique_id}"
    agent = "rosie"
    key = f"smoke-test-{unique_id}"

    # 1. Store
    store_payload = {
        "agent": agent,
        "value": content,
        "key": key,
        "session_id": "smoke-session",
        "category": "eval",
        "dedup": False,
        "metadata": {"nonce": unique_id, "source": "infra/openclaw-sync/memu_smoke_test.py"}
    }
    headers = {
        "Authorization": "Bearer openclaw-memu-local-2026"
    }
    print(f"Storing: {store_payload}")
    try:
        resp = requests.post(f"{BASE_URL}{API_PREFIX}/store", json=store_payload, headers=headers)
        resp.raise_for_status()
        store_data = resp.json()
        print(f"Store response: {store_data}")
        proof_id = store_data.get("id")
    except Exception as e:
        print(f"Store failed: {e}")
        return

    time.sleep(1) # Allow for indexing/committing

    # 2. Search
    search_payload = {
        "query": unique_id,
        "limit": 3
    }
    print(f"Searching: {search_payload}")
    try:
        resp = requests.post(f"{BASE_URL}{API_PREFIX}/search", json=search_payload, headers=headers)
        resp.raise_for_status()
        search_data = resp.json()
        print(f"Search response: {json.dumps(search_data, indent=2)}")

        results = search_data.get("results", []) if isinstance(search_data, dict) else search_data
        found = any(item.get("id") == proof_id for item in results)

        if found:
            print(f"Smoke test PASSED: Memory stored and retrieved. proof_id={proof_id}")
        else:
            print("Smoke test FAILED: Memory stored but not found in search results.")

    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    smoke_test()
