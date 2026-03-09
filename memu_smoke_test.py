import requests
import uuid
import json
import time

BASE_URL = "http://localhost:8711/api/v1/memu"

def smoke_test():
    unique_id = str(uuid.uuid4())
    content = f"Smoke test content {unique_id}"
    agent = "rosie"
    key = f"smoke-test-{unique_id}"

    # 1. Store
    store_payload = {
        "agent": agent,
        "content": content,
        "key": key,
        "user_id": "smoke-tester",
        "session_id": "smoke-session",
        "category": "eval"
    }
    headers = {
        "Authorization": "Bearer openclaw-memu-local-2026"
    }
    print(f"Storing: {store_payload}")
    try:
        resp = requests.post(f"{BASE_URL}/store", json=store_payload, headers=headers)
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
        "query": f"Smoke test content {unique_id}",
        "limit": 1
    }
    print(f"Searching: {search_payload}")
    try:
        resp = requests.post(f"{BASE_URL}/semantic-search", json=search_payload, headers=headers) # Using semantic search as per logs showing TFIDF
        resp.raise_for_status()
        search_data = resp.json()
        print(f"Search response: {json.dumps(search_data, indent=2)}")
        
        found = False
        if isinstance(search_data, list):
             for item in search_data:
                 if item.get("id") == proof_id:
                     found = True
                     break
        elif isinstance(search_data, dict) and "results" in search_data:
             for item in search_data["results"]:
                 if item.get("id") == proof_id:
                     found = True
                     break
        
        if found:
            print("Smoke test PASSED: Memory stored and retrieved.")
        else:
            print("Smoke test FAILED: Memory stored but not found in search results.")

    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    smoke_test()
