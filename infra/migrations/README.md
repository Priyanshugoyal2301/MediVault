# DB Migrations — `infra/migrations`

## Purpose

Alembic migration scripts covering the shared PostgreSQL instance used by all services.

## Conventions

- Migrations are per-service namespaced: `auth_`, `health_`, `ai_` prefixes on migration file names.
- Run order: auth → health → ai (auth creates `users` table; health and ai reference it).
- All migration files live here (not inside individual service directories) so the full DB schema history is in one place.

## Setup

```bash
# From repo root
cd infra/migrations
alembic upgrade head
```

Alembic config (`alembic.ini`) to be added here at Feature 1 when the first real migration is created.
