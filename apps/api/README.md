# API Gateway / BFF — `apps/api`

## What this service owns

Backend-for-Frontend layer. Receives all requests from the web client and routes them to the correct downstream service. No business logic lives here — just auth token validation, request forwarding, and response shaping for the client.

## Tech

FastAPI (Python 3.11+)

## API contract (routing map)

| Client route | Forwarded to |
|---|---|
| `POST /api/auth/register` | `auth-service POST /auth/register` |
| `POST /api/auth/login` | `auth-service POST /auth/login` |
| `GET /api/reports` | `health-service GET /reports` |
| `POST /api/reports` | `health-service POST /reports` (triggers AI parsing job) |
| `GET /api/timeline` | `health-service GET /timeline` |
| `POST /api/qa` | `ai-service POST /qa` |

All endpoints (except `/api/auth/*`) require a valid JWT in the `Authorization` header — validated here before forwarding.

## Running locally

```bash
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Or via docker-compose from the repo root.

## Health check

`GET /health` → `200 {"status": "ok"}`
