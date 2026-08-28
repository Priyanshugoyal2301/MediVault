# Phase 11 Commit Audit

**Date:** 2026-08-29  
**Baseline:** `e70933e` (origin/main at Phase 11 start)  
**Branch:** `main` (local, **not pushed**)

---

# Phase 11 Decision

**LIVE DEMO READY WITH OBSERVATIONS**

---

# Commits Created

## 1. `8121563` — fix(integration): resolve live demo service startup and seed flow

**Purpose:** Code and configuration fixes required for reproducible local demo startup and demo seed flow.

**Files included:**

| File | Change |
|------|--------|
| `apps/api/core/config.py` | Load repo-root `.env` for BFF |
| `scripts/bootstrap_imports.py` | Hyphenated `services/*-service` import finder (new) |
| `scripts/run_service.py` | Unified local uvicorn launcher incl. `apps.api.main:app` (new) |
| `services/health-service/db/models.py` | Read-only `User` ORM stub for FK resolution |
| `services/ai-service/Dockerfile` | `COPY packages/ml-interfaces` |
| `docker-compose.yml` | Configurable `POSTGRES_PUBLISH_PORT` |
| `.env.example` | Document `POSTGRES_PUBLISH_PORT` |
| `infra/migrations/env.py` | Load repo-root `.env` for alembic |
| `infra/migrations/versions/003_create_qa_and_knowledge_tables.py` | Fix nested `sa.Column`; pgvector via raw SQL only |
| `scripts/demo_preflight.ps1` | `MEDIVAULT_*_PORT` overrides (defaults unchanged) |

---

## 2. `dc17fab` — docs(demo): document validated startup and live demo workflow

**Purpose:** Document validated startup order, default vs override ports, and Phase 11 validation evidence.

**Files included:**

| File | Change |
|------|--------|
| `README.md` | `run_service.py`, repo-root alembic, `POSTGRES_PUBLISH_PORT`, `docker-compose up --build` |
| `docs/DEMO_SCRIPT.md` | Updated judge preflight flow and port-conflict guidance |
| `PHASE11_LIVE_DEMO_VALIDATION.md` | Full validation report (new) |

---

## 3. docs(phase11): add live demo fixes commit audit

(Hash: see `git log -1` on `main` — this commit contains the audit file.)

**Purpose:** Record Phase 11 commit grouping, validation evidence, and excluded files.

**Files included:**

| File | Change |
|------|--------|
| `PHASE11_COMMIT_AUDIT.md` | This audit report (new) |

---

# Fixes Included

| Fix | Verification |
|-----|--------------|
| BFF repo-root `.env` | `apps.api.main:app` starts via `run_service.py`; `/health` OK |
| `run_service.py` + bootstrap | All four services start from repo root |
| Health `User` stub | ORM metadata resolves FKs; stub has `id` only; no health-service user writes; auth owns auth |
| AI Dockerfile `ml-interfaces` | `docker-compose build ai-service` **PASS** (build only; runtime not re-tested in container this session) |
| Migration 003 pgvector | Nested column removed; raw SQL `vector(384)` |
| Alembic dotenv | `alembic -c infra/migrations/alembic.ini upgrade head` from repo root |
| `POSTGRES_PUBLISH_PORT` | Default 5432; override documented, not hardcoded |
| Preflight port overrides | Defaults 8001/8002/8003/8000/3000; `MEDIVAULT_*_PORT` env vars work |

---

# Validation Results

| Check | Result | Notes |
|-------|--------|-------|
| Health unit tests (`tests/unit/health-service/`) | **19 PASS** | Includes reports/timeline/qa |
| `scripts/smoke_demo.ps1` | **PASS** | Re-run during Phase 11.1 commit prep |
| `scripts/demo_preflight.ps1` | **PASS** | With `MEDIVAULT_AUTH_PORT=8011`, `MEDIVAULT_WEB_PORT=3002` |
| User ORM stub inspection | **PASS** | `User` columns: `['id']` only |
| AI Docker build | **PASS** | Image builds with `packages/ml-interfaces` layer |
| AI Docker runtime | **Not re-tested** | Local AI on :8003 used for smoke; rebuild validated at build time |
| Default preflight ports | **Not tested** | Machine has 8001/3000 conflicts; defaults preserved in script |

---

# Documentation Updated

- `README.md` — startup order, migrations, `run_service.py`, port overrides, `docker-compose up --build`
- `docs/DEMO_SCRIPT.md` — judge preflight, automated checks, override examples
- `PHASE11_LIVE_DEMO_VALIDATION.md` — validation evidence; machine-specific ports labeled as examples only

**Documented startup order:**

1. Copy `.env.example` → `.env`
2. `docker-compose up -d postgres`
3. `alembic -c infra/migrations/alembic.ini upgrade head`
4. Start Auth (`run_service.py` … 8001)
5. Start Health (… 8002)
6. Start AI (… 8003)
7. Start BFF (`apps.api.main:app` … 8000)
8. Start Web (`npm run dev`)
9. `scripts/demo_preflight.ps1`
10. `scripts/smoke_demo.ps1`

---

# Known Observations

1. After AI Dockerfile changes, use `docker-compose up --build` (or `docker-compose build ai-service`) before relying on the container.
2. Port conflicts require `.env` `*_SERVICE_URL` overrides and matching `run_service.py` ports; `MEDIVAULT_*_PORT` for preflight only.
3. Browser E2E not manually stepped through; API smoke covers judge path.

---

# Files Explicitly Excluded

| File / path | Reason |
|-------------|--------|
| `.env` | Local secrets (gitignored) |
| `phase11_logs/` | Generated runtime logs |
| `POST_PUSH_VERIFICATION.md` | Phase 10 artifact |
| `PUSH_READINESS.md` | Phase 10 artifact |
| `node_modules/`, `dist/`, caches, model artifacts | Not part of Phase 11 |

---

# Git Status

```
On branch main
Your branch is ahead of 'origin/main' by 3 commits.
Untracked: POST_PUSH_VERIFICATION.md, PUSH_READINESS.md, phase11_logs/
```

**Ahead of origin/main:**

```
 .env.example                                       |  2 +
 PHASE11_LIVE_DEMO_VALIDATION.md                    | 146 +++++++++++++++
 README.md                                          |  26 ++-
 apps/api/core/config.py                            |   8 +-
 docker-compose.yml                                 |   2 +-
 docs/DEMO_SCRIPT.md                                |  15 +-
 infra/migrations/env.py                            |  10 +
 .../versions/003_create_qa_and_knowledge_tables.py |  12 +-
 scripts/bootstrap_imports.py                       |  75 ++++++++
 scripts/demo_preflight.ps1                         |  26 ++-
 scripts/run_service.py                             |  41 +++++
 services/ai-service/Dockerfile                     |   1 +
 services/health-service/db/models.py               |   9 +
 13 files changed, 333 insertions(+), 40 deletions(-)
```

---

# Recommended Next Step

**Await explicit approval before `git push origin main`.**

Optional follow-up (not in scope): commit or gitignore Phase 10 untracked reports (`PUSH_READINESS.md`, `POST_PUSH_VERIFICATION.md`).

**This report does not authorize a push.**
