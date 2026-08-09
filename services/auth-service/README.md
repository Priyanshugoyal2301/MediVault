# Auth Service — `services/auth-service`

## What this service owns

User identity, credential storage, JWT issuance and validation, session management.

**This service is the designated hook point for future auth strategies** (biometric login, government ID / ABHA verification) — new auth methods are added here as additional strategies without touching Health or AI services.

## Tech

FastAPI + SQLAlchemy (asyncpg) + Alembic + python-jose

## API contract

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Create user (email + password). Returns JWT. |
| `POST` | `/auth/login` | Authenticate. Returns JWT. |
| `POST` | `/auth/logout` | Invalidate session token. |
| `GET` | `/auth/me` | Return authenticated user's profile. |
| `GET` | `/health` | Service health check. |

## Database tables owned

- `users` — id, email, hashed_password, locale_preference, created_at, deleted_at

## Running locally

```bash
cd services/auth-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```
