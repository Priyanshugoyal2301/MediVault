# MediVault AI

> An AI layer that turns a person's scattered medical reports and health data into an understandable, evidence-cited, remembered health record — without ever issuing a diagnosis.

**Status:** Feature 2 complete (Timeline + Anomaly Detection). See [`00_PROJECT_STATE.md`](00_PROJECT_STATE.md) for the current build state.

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

MediVault takes uploaded medical lab reports (PDFs, images), OCRs them, extracts structured health values (CBC, lipid panel, thyroid, HbA1c), explains them in plain language (English + Hindi), and tracks trends over time to flag unusual patterns — all without ever making a diagnosis.

**It does NOT:**
- Diagnose conditions
- Replace a doctor's advice
- Store data in the cloud by default (local storage in dev)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Client (browser / mobile)                              │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────┐
│  API Gateway  (apps/api/ — FastAPI BFF)                 │
│  • JWT validation   • X-User-ID header injection        │
└──────┬────────────────────┬───────────────┬─────────────┘
       │                    │               │
┌──────▼──────┐  ┌──────────▼──────┐  ┌───▼──────────────┐
│ Auth Service│  │ Health Service  │  │  AI Service      │
│ /auth/*     │  │ /reports/*      │  │  /parse          │
│ JWT, bcrypt │  │ /timeline/*     │  │  /anomaly/detect │
└─────────────┘  └────────┬────────┘  └──────────────────┘
                           │ owner_id scoped
                     ┌─────▼──────┐
                     │ PostgreSQL  │
                     │ + pgvector  │
                     └────────────┘
```

All health data queries are **owner-scoped** at the repository layer — a user can never receive another user's data, even if the API layer forgets to check.

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
#   JWT_SECRET_KEY=<32+ char random string>
```

### 4. Start PostgreSQL

```bash
docker-compose up -d db
```

### 5. Run database migrations

```bash
cd infra/migrations
alembic upgrade head
cd ../..
```

---

## Running Services

Each service is a separate FastAPI app. Run in separate terminals:

```bash
# Auth Service (port 8000)
cd services/auth-service
uvicorn main:app --reload --port 8000

# Health Service (port 8001)
cd services/health-service
uvicorn main:app --reload --port 8001

# AI Service (port 8002)
cd services/ai-service
uvicorn main:app --reload --port 8002
```

Or start everything with Docker Compose:

```bash
docker-compose up
```

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
| `GET` | `/reports` | List all reports for the authenticated user |
| `GET` | `/reports/{id}` | Get a report with extracted values + bilingual explanations |
| `DELETE` | `/reports/{id}` | Delete report + cascade (file, values, timeline events) |
| `GET` | `/timeline` | Get health timeline summary (latest value per test name) |
| `GET` | `/timeline/{test_name}` | Full chronological history for a specific lab metric |

---

### AI Service (`/parse`, `/anomaly`) — Internal only

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/parse` | OCR + parse + explain a report (called by health-service background task) |
| `POST` | `/anomaly/detect` | Trend + anomaly detection for a lab metric time series |

---

## Running Tests

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

---

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
5. **JWT-only user identity.** The `owner_id` for every query comes from the decoded JWT, never from the request body.

For the full rules, see [`docs/04_AGENT_RULES.md`](docs/04_AGENT_RULES.md).
