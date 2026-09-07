# MediVault AI

A privacy-conscious health vault prototype: upload lab reports, get plain-language explanations (English + Hindi), track personal biomarker trends, and ask citation-backed questions — without issuing diagnoses.

**Status:** Hackathon / research prototype. JWT-backed FastAPI microservices, React demo client, and an optional ML platform behind feature flags (all off by default).

> Not medical device software. Not a substitute for clinical care.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Key features](#key-features)
3. [Architecture](#architecture)
4. [Tech stack](#tech-stack)
5. [Prerequisites](#prerequisites)
6. [Quick start](#quick-start)
7. [Running with Docker Compose](#running-with-docker-compose)
8. [Demo path](#demo-path)
9. [API overview](#api-overview)
10. [ML feature flags](#ml-feature-flags)
11. [Tests](#tests)
12. [Project structure](#project-structure)
13. [Documentation](#documentation)
14. [Privacy & safety](#privacy--safety)
15. [Contributing](#contributing)
16. [License](#license)

---

## What it does

MediVault turns scattered lab PDFs/images into an **owner-scoped** vault:

| Capability | Behavior |
|------------|----------|
| Upload & parse | Magic-byte MIME check, async OCR + structured extraction (CBC, lipid, thyroid, HbA1c) |
| Demo seed | Deterministic CBC/Lipid panels for judging — no OCR required |
| Explanations | Template bilingual copy; non-diagnostic tone |
| Timeline | Chronological values per metric; personal-series statistical anomaly monitor |
| Q&A | Safety-first layer, then BM25 + intent retrieval over a local knowledge base |
| Auth | Register / login / JWT; browser never sends `X-User-ID` |

**It does not:** diagnose conditions, replace a clinician, or (in default local setup) send PHI to cloud OCR APIs.

---

## Key features

- **BFF security model** — Browser → API gateway (`apps/api`) validates JWT, strips client `X-User-ID`, injects trusted identity into health-service.
- **Owner-scoped data access** — Repository layer requires `owner_id` on health queries.
- **Local-first AI path** — Tesseract OCR, in-memory KB for live Q&A (`MEDIVAULT_FAST_KB=1`), statistical anomaly (z-score / CUSUM) by default.
- **Optional ML platform** — OCR adapter, normalizer, retrieval, risk, forecast, health score, anomaly, image quality — enabled only via env flags with fallbacks.
- **Research site** — Static institutional site in `apps/research-site/` (separate from the product SPA).

---

## Architecture

```
Browser (apps/web :3000)
        │  JWT
        ▼
API Gateway / BFF (apps/api :8000)
   JWT verify · strip client X-User-ID · proxy
        │                    │
        ▼                    ▼
 Auth (:8001)          Health (:8002) ──internal──▶ AI (:8003)
 JWT + bcrypt          reports/timeline/qa         parse / anomaly / qa
        │                    │
        └────────┬───────────┘
                 ▼
          PostgreSQL + pgvector
```

AI ports are not exposed through the BFF. Health→AI calls use `INTERNAL_SERVICE_KEY` when set.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| API / services | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy, asyncpg, Alembic |
| Auth | python-jose (JWT), passlib/bcrypt |
| Database | PostgreSQL 16 + pgvector (Docker image) |
| OCR / vision | Tesseract, pdfplumber, Pillow |
| Retrieval (default) | In-memory BM25 + intent |
| Frontend | React 18, Vite 5 |
| Orchestration | Docker Compose |

---

## Prerequisites

| Tool | Notes |
|------|--------|
| Python 3.11+ | Virtualenv recommended |
| Node.js 18+ | For `apps/web` (and optional research site) |
| Docker & Docker Compose | Postgres (and optional full stack) |
| Tesseract OCR | Needed for real uploads; demo seed works without it |
| Git | |

---

## Quick start

### 1. Clone and virtualenv

```bash
git clone https://github.com/Priyanshugoyal2301/MediVault.git
cd MediVault
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements-dev.txt
# or per-service:
# pip install -r services/auth-service/requirements.txt
# pip install -r services/health-service/requirements.txt
# pip install -r services/ai-service/requirements.txt
# pip install -r apps/api/requirements.txt
```

### 3. Environment

```bash
cp .env.example .env
```

Set at least:

- `POSTGRES_PASSWORD`
- `AUTH_SECRET_KEY` (32+ characters; shared by auth-service and BFF)
- `INTERNAL_SERVICE_KEY` (shared by health-service and ai-service)

Defaults (do not change unless ports conflict):

| Service | Port |
|---------|------|
| BFF | 8000 |
| Auth | 8001 |
| Health | 8002 |
| AI | 8003 |
| Web | 3000 |
| Postgres | 5432 |

If **5432** is busy: set `POSTGRES_PUBLISH_PORT=5433` and `POSTGRES_PORT=5433` in `.env`.  
If **8001** / **3000** are busy: remap in `.env` (`AUTH_SERVICE_URL`, etc.) and pass matching ports to `run_service.py`. Preflight overrides: `MEDIVAULT_AUTH_PORT`, `MEDIVAULT_WEB_PORT`, and related vars (see `scripts/demo_preflight.ps1`).

### 4. Postgres + migrations

```bash
docker-compose up -d postgres
alembic -c infra/migrations/alembic.ini upgrade head
```

### 5. Start services (repo root)

```bash
python scripts/run_service.py services.auth_service.main:app 8001
python scripts/run_service.py services.health_service.main:app 8002
python scripts/run_service.py services.ai_service.main:app 8003
python scripts/run_service.py apps.api.main:app 8000
```

`scripts/run_service.py` resolves hyphenated package paths and starts the BFF with the correct `app_dir`.

### 6. Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000 (Vite proxies `/auth`, `/reports`, `/timeline`, `/qa` to the BFF).

### 7. Smoke checks

```bash
# Windows PowerShell (from repo root)
powershell -File scripts/demo_preflight.ps1
powershell -File scripts/smoke_demo.ps1
```

---

## Running with Docker Compose

```bash
docker-compose up --build
```

Starts postgres, auth, health, AI, and the BFF. Use `--build` after Dockerfile changes (for example AI packaging of `packages/ml-interfaces`). Run the web client separately with `npm run dev` in `apps/web`.

Health and AI bind to localhost only in Compose.

---

## Demo path

Prefer the **LIPID Demo** seed (no OCR):

1. Register / sign in in the web UI  
2. Upload → **LIPID Demo**  
3. Timeline → **LDL Cholesterol**  
4. Q&A chips (guideline → personal → safety/emergency)

Full judge script: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md). Talking points: [`docs/JUDGE_QA.md`](docs/JUDGE_QA.md), [`docs/PRESENTATION_CLAIMS.md`](docs/PRESENTATION_CLAIMS.md).

---

## API overview

Public browser traffic should use the **BFF** (`http://127.0.0.1:8000`) with `Authorization: Bearer <token>`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Obtain JWT |
| `GET` | `/auth/me` | Current user |
| `POST` | `/reports` | Upload report (async parse) |
| `POST` | `/reports/demo/seed?panel=cbc\|lipid` | Deterministic demo data |
| `GET` | `/reports` | List reports |
| `GET` | `/reports/{id}` | Report + values + explanations |
| `DELETE` | `/reports/{id}` | Delete report (cascade) |
| `GET` | `/timeline` | Latest value per test |
| `GET` | `/timeline/{test_name}` | History for a metric |
| `GET` | `/timeline/{test_name}/anomaly` | History + trend/anomaly |
| `POST` | `/qa` | Safety-first Q&A |

Internal AI (not routed via BFF): `POST /parse`, `POST /anomaly/detect`, `POST /qa`.  
Service READMEs and [`docs/API.md`](docs/API.md) cover ML registry-only surfaces.

---

## ML feature flags

All `USE_*` flags default to **0** (rule-based / statistical path). Flip only after evaluating the matching `models/*` and `validation/` docs. Reference: [`docs/FEATURE_FLAGS.md`](docs/FEATURE_FLAGS.md), [`.env.example`](.env.example).

Restart **ai-service** after changing flags (registry is process-cached).

---

## Tests

```bash
# From repo root (PYTHONPATH set for imports)
# Windows: $env:PYTHONPATH="."
# macOS/Linux: export PYTHONPATH=.

python -m pytest tests/unit -q
python -m pytest tests/phase1 tests/phase1a tests/phase2 tests/phase3 -q
# Additional ML phases: tests/phase4 … tests/phase9
```

Offline ML tooling:

```bash
python models/platform/safe_train.py   # guarded auto-train (Phases 2–8)
python models/platform/train_guard.py  # decisions only
python models/platform/audit.py
python models/platform/benchmark_suite.py
python models/platform/e2e_validate.py
```

See [`docs/TRAINING.md`](docs/TRAINING.md).

---

## Project structure

```
MediVault/
├── apps/
│   ├── api/                 # JWT BFF / API gateway
│   ├── web/                 # React + Vite demo SPA
│   └── research-site/       # Static research / portfolio site
├── services/
│   ├── auth-service/        # Register, login, JWT
│   ├── health-service/      # Reports, timeline, Q&A proxy
│   └── ai-service/          # OCR, anomaly, RAG, ML adapters
├── packages/
│   ├── shared-types/        # Shared Pydantic schemas
│   ├── shared-utils/        # Redacting logger
│   ├── ml-interfaces/       # ML protocol interfaces
│   └── ml-eval/             # Eval helpers
├── models/                  # Offline train/eval for ML phases
├── datasets/                # Synthetic / fixture datasets + licensing
├── data/knowledge-base/     # Guideline text for live Q&A
├── infra/migrations/        # Alembic
├── scripts/                 # run_service, smoke_demo, demo_preflight
├── tests/                   # Unit + phase suites
├── validation/              # Per-model validation notes
├── docs/                    # Architecture, API, demo, ML docs
├── BIBLE.md                 # Long-form technical encyclopedia
├── docker-compose.yml
├── requirements-dev.txt
└── .env.example
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Judge / live demo flow |
| [`docs/FEATURE_FLAGS.md`](docs/FEATURE_FLAGS.md) | ML flag matrix |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | Env and backend knobs |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture index |
| [`docs/API.md`](docs/API.md) | ML-oriented API notes |
| [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) | Honest platform limits |
| [`docs/MODEL_REGISTRY.md`](docs/MODEL_REGISTRY.md) | Model inventory |
| [`docs/PRESENTATION_CLAIMS.md`](docs/PRESENTATION_CLAIMS.md) | Conservative claims sheet |
| [`BIBLE.md`](BIBLE.md) | Full technical encyclopedia |
| [`CONTRIBUTORS.md`](CONTRIBUTORS.md) | Author — Deepansh Khanna |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contributor workflow |
| [`docs/DEVELOPER_RULES.md`](docs/DEVELOPER_RULES.md) | Developer conventions |

---

## Privacy & safety

1. **No diagnoses** — Summaries and RAG answers must not assert “you have X.”
2. **Owner-scoped queries** — Enforced in health-service repositories.
3. **Redacting logger** — Use `packages.shared_utils.get_logger`; do not log raw PHI field values.
4. **Local OCR by default** — Tesseract; avoid cloud OCR unless privacy rationale is explicit.
5. **Trusted identity** — Only the BFF may inject `X-User-ID` after JWT validation.
6. **Emergency safety layer** — Chest-pain / breathing-style prompts trigger fixed safety copy before RAG.

Developer rules: [`docs/DEVELOPER_RULES.md`](docs/DEVELOPER_RULES.md).

---

## Contributing

Maintainer: **Deepansh Khanna** — see [`CONTRIBUTORS.md`](CONTRIBUTORS.md).

Development workflow: [`CONTRIBUTING.md`](CONTRIBUTING.md). Keep ML flags off unless you are intentionally enabling and evaluating a model.

---

## License

No `LICENSE` file is present in this repository yet. Treat the code as source-available for evaluation unless the owners publish terms. Do not use MediVault outputs as clinical advice.
