# API Gateway / BFF — `apps/api`

## What this service owns

Browser-facing Backend-for-Frontend:

- Validate JWT (`Authorization: Bearer …`)
- Strip any client `X-User-ID` and inject trusted identity from token `sub`
- Proxy to auth-service and health-service
- **Does not** expose AI-service routes

## Tech

FastAPI + httpx + python-jose

## Routing map (actual)

| Client route | Upstream |
|---|---|
| `POST /auth/register` | auth-service `/auth/register` |
| `POST /auth/login` | auth-service `/auth/login` |
| `GET /auth/me` | auth-service `/auth/me` |
| `GET\|POST /reports…` | health-service (JWT required) |
| `GET /timeline…` | health-service (JWT required) |
| `POST /qa` | health-service (JWT required; health calls AI) |

There is **no** `/api` prefix. Vite proxies these paths to `:8000`.

## Running locally

```bash
# From repo root: ensure .env has AUTH_SECRET_KEY matching auth-service
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Health

`GET /health` → gateway status + configured upstream URLs.
