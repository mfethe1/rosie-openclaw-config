# memU health sweep 2026-02-24T150235

## Route contract checks
- /api/v1/memu/health:
{
  "status": "ok",
  "service": "memU bridge",
  "version": "2.2.0",
  "features": [
    "sqlite-storage",
    "like-and-tfidf-search",
    "tfidf-semantic-search",
    "recency-decay",
    "use-count-boost",
    "idempotency",
    "content-hash-dedup",
    "event-stream",
    "wal-auto-checkpoint",
    "wal-threshold-escalation",
    "periodic-gc",
    "crash-recovery",
    "atomic-event-log",
    "thread-local-conn-pool",
    "begin-immediate",
    "explicit-rollback",
    "health-triggered-checkpoint",
    "expires-at-ttl",
    "event-log-rotation",
    "connection-recovery"
  ],
  "db_path": "/Users/harrisonfethe/.openclaw/workspace/memory/memu_store/memu.db",
  "db_bytes": 729088,
  "wal_bytes": 86552,
  "row_count": 547,
  "pending_gc": 0,
  "ttl_days": 180,
  "timestamp": "2026-02-24T20:02:35.244074+00:00"
}
- /health (legacy probe):
404
- /api/v1/memu/store auth-less (expect 401/405):
401

## 24h service log tail
- memu_server.log updated within 24h: yes
2026-02-24 00:05:37,287 [memU] INFO memU bridge server starting on port 8711
2026-02-24 00:05:37,287 [memU] INFO Memory store (SQLite): /Users/harrisonfethe/.openclaw/workspace/memory/memu_store/memu.db
2026-02-24 00:05:37,287 [memU] INFO Memory store (SQLite): /Users/harrisonfethe/.openclaw/workspace/memory/memu_store/memu.db
2026-02-24 00:05:37,287 [memU] INFO API Key: openclaw...
2026-02-24 00:05:37,287 [memU] INFO API Key: openclaw...
2026-02-24 00:05:37,287 [memU] INFO Endpoints:
2026-02-24 00:05:37,287 [memU] INFO Endpoints:
2026-02-24 00:05:37,287 [memU] INFO   GET  http://localhost:8711/api/v1/memu/health
2026-02-24 00:05:37,287 [memU] INFO   GET  http://localhost:8711/api/v1/memu/health
2026-02-24 00:05:37,287 [memU] INFO   POST http://localhost:8711/api/v1/memu/store
2026-02-24 00:05:37,287 [memU] INFO   POST http://localhost:8711/api/v1/memu/store
2026-02-24 00:05:37,287 [memU] INFO   POST http://localhost:8711/api/v1/memu/search          (SQLite LIKE match)
2026-02-24 00:05:37,287 [memU] INFO   POST http://localhost:8711/api/v1/memu/search          (SQLite LIKE match)
2026-02-24 00:05:37,287 [memU] INFO   POST http://localhost:8711/api/v1/memu/semantic-search (TF-IDF ranked)
2026-02-24 00:05:37,287 [memU] INFO   POST http://localhost:8711/api/v1/memu/semantic-search (TF-IDF ranked)
2026-02-24 00:05:37,287 [memU] INFO   GET  http://localhost:8711/api/v1/memu/list
2026-02-24 00:05:37,287 [memU] INFO   GET  http://localhost:8711/api/v1/memu/list
2026-02-24 00:05:43,052 [memU] INFO STORE id=7af263cd-110a-43a1-8342-97dc155bc227 agent=shared idem=ch-1513ed49d006ca8f2 key='cron-health-sweep-20260224-0004'
2026-02-24 00:05:43,052 [memU] INFO STORE id=7af263cd-110a-43a1-8342-97dc155bc227 agent=shared idem=ch-1513ed49d006ca8f2 key='cron-health-sweep-20260224-0004'
2026-02-24 00:06:10,032 [memU] INFO Startup integrity check: OK
2026-02-24 00:06:10,041 [memU] INFO memU bridge server starting on port 8711
2026-02-24 00:06:10,041 [memU] INFO Memory store (SQLite): /Users/harrisonfethe/.openclaw/workspace/memory/memu_store/memu.db
2026-02-24 00:06:10,041 [memU] INFO API Key: openclaw...
2026-02-24 00:06:10,041 [memU] INFO Endpoints:
2026-02-24 00:06:10,041 [memU] INFO   GET  http://localhost:8711/api/v1/memu/health
2026-02-24 00:06:10,041 [memU] INFO   POST http://localhost:8711/api/v1/memu/store
2026-02-24 00:06:10,041 [memU] INFO   POST http://localhost:8711/api/v1/memu/search          (SQLite LIKE match)
2026-02-24 00:06:10,041 [memU] INFO   POST http://localhost:8711/api/v1/memu/semantic-search (TF-IDF ranked)
2026-02-24 00:06:10,041 [memU] INFO   GET  http://localhost:8711/api/v1/memu/list
2026-02-24 00:06:12,278 [memU] INFO STORE id=8a2ec5d9-35fc-4f79-a014-9f9dbe8622e6 agent=shared idem=ch-83110046646b4b0c3 key='cron-health-sweep-dupfix-2'
2026-02-24 00:06:31,222 [memU] INFO STORE id=5c60feef-cc87-4077-a62e-9b80006daa8f agent=rosie idem=ch-317c3aa4eaee8389d key='eval-memu-health-sweep-2026-02-24-0004-2026-02-24T05:06:31'
2026-02-24 03:03:01,836 [memU] INFO STORE id=3cfff80d-df5b-4322-acbf-0fd4db722d5d agent=rosie idem=ch-5891c0332a548b96f key='contract-check-20260224'
2026-02-24 03:03:23,054 [memU] INFO STORE id=bc62cd27-e688-4dec-be83-6222bf1e90a6 agent=rosie idem=ch-99803a9fdb4456eb5 key='eval-memu-health-sweep-24h-2026-02-24T08:03:22'
2026-02-24 03:03:28,796 [memU] INFO STORE id=6ffd570a-f569-4f43-8875-1fa9e1bafaea agent=rosie idem=ch-3a622cbad8dd11ed4 key='memu-health-sweep-2026-02-24-0302'
2026-02-24 06:02:54,395 [memU] INFO STORE id=52631557-4784-4312-b64e-e74e5cd65e8f agent=rosie idem=ch-3ae53d8beaca4d191 key='sweep-contract-ac492d72-cf3f-46d5-9fe5-438325421dd2'
2026-02-24 06:03:32,049 [memU] INFO STORE id=32a82e8d-da55-4a0a-97aa-6645c2374dbc agent=rosie idem=ch-085462b796445ff1f key='eval-memu-health-sweep-2026-02-24-0602-2026-02-24T11:03:31'
2026-02-24 09:02:41,537 [memU] INFO STORE id=33b5d78b-f10e-45ea-89ee-a918d67b281b agent=rosie idem=ch-6219d968e101737f9 key='health-sweep-a2d8855a'
2026-02-24 09:03:21,393 [memU] INFO STORE id=ac1628ea-57c4-484a-876b-990280c89df4 agent=rosie idem=ch-ce4c68611e58a736a key='eval-memu-health-sweep-2026-02-24-0902-2026-02-24T14:03:21'
2026-02-24 12:03:18,851 [memU] INFO STORE id=6b47dea3-9760-4363-845d-c564a486edb4 agent=rosie idem=ch-74a3d15306687311e key='eval-memu-health-sweep-2026-02-24-1202-2026-02-24T17:03:18'
2026-02-24 12:03:25,046 [memU] INFO STORE id=f7e06753-8e74-491e-a03c-c2331cdbd5bb agent=rosie idem=ch-7ed03777c1a82da48 key='sweep-contract-4dbc9a7e'
