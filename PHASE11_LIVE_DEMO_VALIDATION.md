# Phase 11 — Live Demo Validation

**Date:** 2026-08-29  
**Baseline:** `main` @ `e70933e` (synced with `origin/main`)  
**Decision:** **LIVE DEMO READY WITH OBSERVATIONS**

---

## Summary

The full hackathon demo path was validated on a Windows host with **port conflicts** on 5432, 8001, and 3000. After applying Phase 11 fixes (documented below), all backend services, automated smoke tests, and preflight checks passed. The browser UI loads on an alternate port (`3002`).

| Check | Result |
|-------|--------|
| Postgres + migrations (004) | PASS |
| Auth `/health` | PASS (port **8011**) |
| Health `/health` | PASS (port **8002**) |
| AI `/health` + KB bootstrap | PASS (port **8003**, local process) |
| BFF `/health` | PASS (port **8000**) |
| `scripts/smoke_demo.ps1` | **PASS** (register → LIPID seed → timeline anomaly → Q&A ×3 + safety) |
| `scripts/demo_preflight.ps1` | **PASS** (with port env overrides) |
| Web UI (Vite) | PASS (`http://127.0.0.1:3002`) |
| ML feature flags | All default **OFF** (confirmed via AI `/health`) |

---

## Environment

| Component | Notes |
|-----------|-------|
| OS | Windows 10 (26200) |
| Postgres | Docker `medivault-postgres-1` on `127.0.0.1:5433` |
| Port conflicts | `8001` (bcbs-backend), `3000` (opspilot-frontend), `5432` (opspilot-postgres) |
| Service mode | Hybrid: Postgres in Docker; auth/health/AI/BFF as **local Python** via `scripts/run_service.py` |
| Auth port override | `AUTH_SERVICE_URL=http://127.0.0.1:8011` in local `.env` |

---

## Issues Found and Fixes Applied

### 1. BFF could not load repo-root `.env` when cwd ≠ repo root

**Symptom:** `AUTH_SECRET_KEY` missing when starting from `apps/api`.  
**Fix:** `apps/api/core/config.py` loads `.env` from repo root via `Path(__file__).parents[3]`.

### 2. BFF hyphenated / relative imports

**Symptom:** `ModuleNotFoundError: No module named 'routers.proxy'` via bare uvicorn.  
**Fix:** `scripts/run_service.py` supports `apps.api.main:app` with `app_dir=apps/api`.

### 3. Local uvicorn cannot import `services.auth_service` without bootstrap

**Symptom:** `ModuleNotFoundError` for hyphenated service paths.  
**Fix:** New `scripts/bootstrap_imports.py` + `scripts/run_service.py` wrapper.

### 4. Health-service demo seed 500 — missing `users` ORM stub

**Symptom:** `NoReferencedTableError: Foreign key ... could not find table 'users'`.  
**Fix:** Minimal read-only `User` stub in `services/health-service/db/models.py` for FK resolution.

### 5. Docker AI image missing `packages/ml-interfaces`

**Symptom:** `/anomaly/detect` → 500, `No module named 'packages.ml_interfaces'`.  
**Fix:** `COPY packages/ml-interfaces` added to `services/ai-service/Dockerfile`.  
**Workaround validated:** Run AI locally via `run_service.py` until image is rebuilt.

### 6. Migration 003 nested `sa.Column` for pgvector embedding

**Fix:** Raw SQL only for vector column (committed in working tree).

### 7. Alembic `.env` + Postgres publish port

**Fix:** `infra/migrations/env.py` loads repo-root `.env`; `POSTGRES_PUBLISH_PORT` in `docker-compose.yml` + `.env.example`.

---

## Smoke Demo Output (representative)

```
Register judge002223@example.com ...
Seed LIPID demo ...
  report_id=ae2fd644-... values=3
Timeline LDL anomaly ...
  trend=rising is_anomaly=True method=statistical_monitor
Q&A guideline ... citations=3 safety=False
Q&A personal ... (vault answer)
Safety ... safety_triggered=True
SMOKE PASSED
```

---

## Observations (non-blocking)

1. **Docker AI image** — after Dockerfile changes, run `docker-compose build ai-service` or `docker-compose up --build` before relying on the container for anomaly/Q&A paths.
2. **Default ports may conflict** on dev machines running other stacks; use `MEDIVAULT_*_PORT` env vars in `demo_preflight.ps1` and matching `*_SERVICE_URL` in `.env`. Default ports (8000/8001/8002/8003/3000) remain unchanged in docs and scripts.
3. **Frontend default 3000** may be occupied; run `npm run dev -- --port 3002` and add origin to `CORS_ORIGINS` if calling BFF from browser on non-3000 port.
4. **Live demo E2E in browser** was not manually stepped through (UI serves 200 on :3002); automated API smoke covers the judge path.

---

## Recommended Startup (machine with port conflicts — example only)

Default ports are **8001/8002/8003/8000/3000**; the commands below use overrides validated on one Windows host where those ports were occupied.

```powershell
# Repo root
docker-compose up -d postgres
alembic -c infra/migrations/alembic.ini upgrade head

python scripts/run_service.py services.auth_service.main:app 8011
python scripts/run_service.py services.health_service.main:app 8002
python scripts/run_service.py services.ai_service.main:app 8003
python scripts/run_service.py apps.api.main:app 8000

cd apps/web; npm run dev -- --port 3002 --host 127.0.0.1

# Verify
$env:MEDIVAULT_AUTH_PORT='8011'; $env:MEDIVAULT_WEB_PORT='3002'
powershell -File scripts/demo_preflight.ps1
powershell -File scripts/smoke_demo.ps1
```

---

## Files Changed (Phase 11)

| File | Purpose |
|------|---------|
| `apps/api/core/config.py` | Repo-root `.env` for BFF |
| `scripts/bootstrap_imports.py` | Hyphenated import finder |
| `scripts/run_service.py` | Unified local service launcher |
| `services/health-service/db/models.py` | `User` FK stub |
| `services/ai-service/Dockerfile` | Include `ml-interfaces` |
| `docker-compose.yml`, `.env.example` | `POSTGRES_PUBLISH_PORT` |
| `infra/migrations/env.py`, `003_*.py` | Dotenv + pgvector fix |
| `scripts/demo_preflight.ps1` | Configurable ports |
| `README.md`, `docs/DEMO_SCRIPT.md` | Updated setup instructions |

---

## Final Decision

**LIVE DEMO READY WITH OBSERVATIONS**

The API judge journey is reproducible and automated smoke passes. Rebuild the AI Docker image (`docker-compose up --build`) or run AI locally via `run_service.py` before demo day.
