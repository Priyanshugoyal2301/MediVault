# API Gateway / BFF — `apps/api`

## What this service owns

Browser-facing Backend-for-Frontend:

- Validate JWT with required subject, issued-at and expiry claims; check the current account through auth `/auth/me`
- Strip client identity/service-key headers and inject trusted identity plus the configured internal service key
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
# From repo root: AUTH_SECRET_KEY must match auth-service;
# INTERNAL_SERVICE_KEY must match health/AI (random, 32+ characters).
pip install -r apps/api/requirements.txt
python scripts/run_service.py apps.api.main:app 8000
```

## Health

`GET /health` → gateway status and version (no internal service addresses).
