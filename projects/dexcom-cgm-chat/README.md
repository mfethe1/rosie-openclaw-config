# Dexcom CGM Chat Hub

Lightweight app area for Dexcom data ingest + chat context.

## What this does
- OAuth callback endpoint for Dexcom auth grant
- Background poller placeholder for glucose pulls
- Local JSON store for recent readings
- Chat endpoint placeholder for question/answer on blood sugar trends

## Quick start
1. Copy `.env.example` to `.env`
2. Add Dexcom client credentials
3. Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8788
```

4. Open `http://localhost:8788/health`

## Endpoints
- `GET /health`
- `GET /dexcom/callback?code=...`
- `GET /readings`
- `POST /chat`

## Next implementation steps
- Exchange OAuth code for tokens
- Persist/refresh token securely (keychain/env vault)
- Pull EGVs on interval and normalize timestamps
- Add alerting thresholds and trend summaries
