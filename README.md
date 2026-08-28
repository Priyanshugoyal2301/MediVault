# MediVault AI

> A hackathon prototype that turns scattered lab reports into an owner-scoped health vault with plain-language explanations, personal trend scoring, and citation-backed Q&A — designed not to issue diagnoses.

**Status:** Hackathon prototype — Features 1–3 backend + live web client behind a JWT BFF. See [`00_PROJECT_STATE.md`](00_PROJECT_STATE.md) and [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

---

## Table of Contents

1. [What MediVault Does](#what-medivault-does)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Setup — Local Development](#setup--local-development)
5. [Running Services](#running-services)
6. [API Reference](#api-reference)
7. [Running Tests](#running-tests)
8. [Project Structure](#project-structure)
9. [Privacy & Safety Rules](#privacy--safety-rules)

---

## What MediVault Does

MediVault takes uploaded medical lab reports (PDFs, images), OCRs them, extracts structured health values (CBC, lipid panel, thyroid, HbA1c), explains them in plain language (English + Hindi), and tracks trends over time to flag unusual patterns. Product tone is non-diagnostic (templates + safety layer); educational KB text may name conditions and must be framed as guidelines, not a personal diagnosis.

**It does NOT:**
- Diagnose conditions
- Replace a doctor's advice
- Store data in the cloud by default (local storage in dev)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Client (browser)                                       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP (local demo) / TLS if you terminate it
┌────────────────────▼────────────────────────────────────┐
│  API Gateway  (apps/api/ — FastAPI BFF)                 │
│  • JWT validation   • trusted X-User-ID injection       │
└──────┬────────────────────┬─────────────────────────────┘
       │                    │
┌──────▼──────┐  ┌──────────▼──────┐     ┌────────────────┐
│ Auth Service│  │ Health Service  │────▶│ AI Service     │
│ /auth/*     │  │ /reports        │     │ /parse         │
│ JWT, bcrypt │  │ /timeline /qa   │     │ /anomaly /qa   │
└─────────────┘  └────────┬────────┘     └────────────────┘
                           │ owner_id scoped
                     ┌─────▼──────┐
                     │ PostgreSQL  │
                     │ (pgvector   │
                     │  installed; │
                     │  live Q&A   │
                     │  uses in-   │
                     │  memory KB) │
                     └────────────┘
```

All health data queries are **owner-scoped** at the repository layer. Browser traffic must go through the BFF (`apps/api`), which validates the JWT and injects a trusted `X-User-ID` (client-supplied `X-User-ID` is stripped). AI endpoints are not exposed through the BFF. Live Q&A retrieval uses an in-memory knowledge base loaded at AI startup (`MEDIVAULT_FAST_KB=1` by default).

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | [python.org](https://python.org) |
| Docker & Docker Compose | 24+ | For PostgreSQL and service orchestration |
| Tesseract OCR | 5.x | `sudo apt install tesseract-ocr tesseract-ocr-hin` or `brew install tesseract` |
| Git | 2.x | |

**Python packages** (per service — see each `requirements.txt`):

```
fastapi, uvicorn, sqlalchemy, asyncpg, alembic
pydantic-settings, python-jose[cryptography], passlib[bcrypt]
httpx, pdfplumber, pytesseract, Pillow
scikit-learn, numpy  # ai-service only
```

---

## Setup — Local Development

### 1. Clone & create virtual environment

```bash
git clone https://github.com/Priyanshugoyal2301/MediVault.git
cd MediVault
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 2. Install dependencies

Install per-service (or install all at once for development):

```bash
# All services combined (development convenience)
pip install -r services/auth-service/requirements.txt
pip install -r services/health-service/requirements.txt
pip install -r services/ai-service/requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — required values:
#   POSTGRES_PASSWORD=<your_local_password>
#   AUTH_SECRET_KEY=<32+ char random string>
#   INTERNAL_SERVICE_KEY=<shared health↔AI key>
```

### 4. Start PostgreSQL

```bash
docker-compose up -d postgres
```

If port **5432** is already in use locally, set `POSTGRES_PUBLISH_PORT=5433` in `.env` (and `POSTGRES_PORT=5433` for host-run services).

### 5. Run database migrations

From the **repo root** (loads `.env` automatically):

```bash
alembic -c infra/migrations/alembic.ini upgrade head
```

---

## Running Services

Each service is a separate FastAPI app. From the **repo root**, use the bootstrap wrapper (handles hyphenated `services/*-service` imports and BFF `app_dir`):

```powershell
python scripts/run_service.py services.auth_service.main:app 8001
python scripts/run_service.py services.health_service.main:app 8002
python scripts/run_service.py services.ai_service.main:app 8003
python scripts/run_service.py apps.api.main:app 8000
# Frontend
cd apps/web; npm install; npm run dev
```

If default ports conflict (e.g. **8001** taken), override `AUTH_SERVICE_URL` / `HEALTH_SERVICE_URL` / `AI_SERVICE_URL` in `.env` and pass matching ports to `run_service.py`.

Docker Compose starts postgres + services (health/AI bound to localhost only). Judge script: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

```bash
docker-compose up --build
```

Use `--build` after Dockerfile changes (e.g. AI `packages/ml-interfaces`); otherwise `docker-compose up` is sufficient if images are current.

---

## API Reference

### Auth Service (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register a new user (`email`, `password`, `locale`) |
| `POST` | `/auth/login` | Login → returns JWT access token |
| `GET` | `/auth/me` | Get authenticated user profile |

**Authentication:** All non-auth endpoints require `Authorization: Bearer <token>` header.

---

### Health Service (`/reports`, `/timeline`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reports` | Upload a medical report (PDF/image). Returns 202 — async OCR+parse |
| `POST` | `/reports/demo/seed?panel=cbc\|lipid` | Deterministic demo report (no OCR) for judging |
| `GET` | `/reports` | List all reports for the authenticated user |
| `GET` | `/reports/{id}` | Get a report with extracted values + bilingual explanations |
| `DELETE` | `/reports/{id}` | Delete report + cascade (file, values, timeline events) |
| `GET` | `/timeline` | Get health timeline summary (latest value per test name) |
| `GET` | `/timeline/{test_name}` | Full chronological history for a specific lab metric |
| `GET` | `/timeline/{test_name}/anomaly` | History + trend/anomaly analysis from AI service |
| `POST` | `/qa` | Evidence Q&A (safety-first; injects owner lab values) |

---

### AI Service (`/parse`, `/anomaly`) — Internal only

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/parse` | OCR + parse + explain a report (called by health-service background task) |
| `POST` | `/anomaly/detect` | Trend + anomaly detection for a lab metric time series |

---

## Running Tests

```bash
# Unit + Phase 1 OCR + Phase 1A hardening
python -m pytest tests/unit/ai-service tests/phase1 tests/phase1a -q
```

ML flag defaults stay off (`USE_UNLIMITED_OCR=0`). Optional OCR config: `docs/CONFIGURATION.md`.

```bash
# From repo root — sets PYTHONPATH so imports resolve correctly
$env:PYTHONPATH="."; python -m pytest          # Windows PowerShell
PYTHONPATH="." python -m pytest                 # macOS/Linux

# Run only Feature 2 tests
python -m pytest tests/unit/ai-service/test_anomaly.py tests/unit/health-service/test_timeline.py -v
```

**Test coverage by area:**

| Area | Test File |
|------|-----------|
| Auth (JWT + scoping) | `tests/unit/auth-service/test_auth.py` |
| Report upload + parsing | `tests/unit/health-service/test_reports.py` |
| Timeline storage + scoping | `tests/unit/health-service/test_timeline.py` |
| Z-score + anomaly detection | `tests/unit/ai-service/test_anomaly.py` |
| OCR + parser + explainer | `tests/unit/ai-service/test_parser.py` |
| Unlimited-OCR Phase 1 / 1A | `tests/phase1/`, `tests/phase1a/` |
| Test name normalizer Phase 2 | `tests/phase2/` |
| Semantic retrieval Phase 3 | `tests/phase3/` |
| Disease risk Phase 4 | `tests/phase4/` |
| Biomarker forecast Phase 5 | `tests/phase5/` |
| Health score Phase 6 | `tests/phase6/` |
| Anomaly detection Phase 7 | `tests/phase7/` |
| Image quality Phase 8 | `tests/phase8/` |
| Platform hardening Phase 9 | `tests/phase9/` |

**ML platform (offline):**

```bash
python models/platform/audit.py
python models/platform/benchmark_suite.py
python models/platform/e2e_validate.py
```

Deliverables: [`platform-summary.md`](platform-summary.md), [`benchmark_complete.md`](benchmark_complete.md), [`docs/MODEL_REGISTRY.md`](docs/MODEL_REGISTRY.md), [`validation/platform-validation.md`](validation/platform-validation.md).

## Project Structure

```
MediVault/
├── apps/
│   ├── api/              # API Gateway (BFF)
│   └── web/              # Frontend (Feature 3)
├── services/
│   ├── auth-service/     # JWT auth
│   ├── health-service/   # Reports + timeline
│   └── ai-service/       # OCR, parsing, anomaly, RAG
├── packages/
│   ├── shared-types/     # Pydantic schemas
│   └── shared-utils/     # Redacting logger
├── infra/
│   └── migrations/       # Alembic migrations
├── tests/
│   ├── unit/             # Per-service unit tests
│   └── integration/      # End-to-end tests (WIP)
├── data/
│   └── datasets/         # Synthetic evaluation scripts
├── docs/
│   ├── 01_PROJECT_CONTEXT.md
│   ├── 02_ARCHITECTURE.md
│   ├── 03_MVP_SCOPE.md
│   ├── 04_AGENT_RULES.md
│   └── DEV_LOG.md
├── 00_PROJECT_STATE.md   # ← read this first every session
├── conftest.py           # pytest configuration + module resolution
├── docker-compose.yml
└── .env.example
```

---

## Privacy & Safety Rules

1. **No diagnoses.** The AI summarises trends in plain language. It never says "you have [condition]".
2. **Owner-scoped queries.** Every DB query requires `owner_id` — structurally enforced at the repository layer (`ScopedRepository`).
3. **Redacting logger.** All services use `from packages.shared_utils import get_logger`. Never `import logging` directly — health field names are redacted before emission.
4. **Local OCR.** We use Tesseract (self-hosted), not a cloud OCR API, to avoid transmitting raw health data externally.
5. **JWT-only user identity.** Browser clients send `Authorization: Bearer <jwt>` to the BFF. The BFF decodes the JWT and injects trusted `X-User-ID` for health-service — never trust a client-supplied owner id.

For the full rules, see [`docs/04_AGENT_RULES.md`](docs/04_AGENT_RULES.md).
