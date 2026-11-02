# MediVault AI — Complete Project Summary & Contributor Handover Guide

> **Purpose:** This document is a complete walkthrough of MediVault AI for new contributors, team members, or partners pulling the codebase. It details what has been built, the system architecture, evaluation results, how to run tests/services, pending features, known limitations, and clear guidelines on how to contribute further.

---

## 📍 1. Executive Summary & Vision

**MediVault AI** is a privacy-first, evidence-grounded medical AI platform. It turns scattered lab reports (PDFs/images) into an understandable, longitudinal, cited health record — **without ever issuing a medical diagnosis**.

### Core Problem Solved:
Healthcare interaction today is binary: "I'm fine" or "I need a doctor." Consumers struggle to interpret lab reports over time or find trustworthy answers to specific questions without encountering noise or hallucinated advice.

### The Three Technical Pillars:
1. **Longitudinal Memory & Timeline:** Multi-year tracking of blood test metrics scoped per user.
2. **Trend-Based Anomaly Detection:** Flagging subtle multi-point trajectories (e.g., rising LDL across 4 consecutive tests) using Z-score baselines and IsolationForest ML models.
3. **Evidence-Grounded RAG Q&A + Safety Layer:** Answers cited back to authoritative medical guidelines (WHO, NHS, ICMR) with a deterministic, non-ML safety guardrail for emergency red-flag symptoms (<100ms response).

---

## 🏗️ 2. System Architecture & Codebase Map

The project is structured as a clean, decoupled microservices architecture with a shared packages layer, enabling modular development.

```
/MediVault
  ├── /apps
  │   ├── /api                     # API Gateway / BFF (FastAPI) — routes client requests
  │   └── /web                     # Frontend Web App (React + Vite, Dark Glassmorphism UI)
  ├── /services
  │   ├── /auth-service            # Auth, Sessions, JWT, owner identity
  │   ├── /health-service          # Reports CRUD, Timeline repository, owner-scoped DB access
  │   └── /ai-service              # OCR + Parser, Anomaly Detection Engine, Safety Layer, RAG Engine
  ├── /packages
  │   ├── /shared-types            # Shared Pydantic schemas & DTOs
  │   └── /shared-utils            # Redacting logger (health data privacy enforcement)
  ├── /data
  │   ├── /knowledge-base          # Curated medical reference guides (WHO, NHS, ICMR)
  │   └── /datasets                # Synthetic anomaly & RAG evaluation datasets + runners
  ├── /infra
  │   └── /migrations              # Alembic database schema migrations (001, 002, 003)
  ├── /docs                        # Architecture, rules, dev log, and handover documentation
  └── /tests
      └── /unit                    # 132 automated unit tests across all services
```

---

## ✅ 3. What Has Been Completed (Shipped MVP Scope)

All 3 core MVP features defined in `03_MVP_SCOPE.md` have been fully built, tested, evaluated, and documented.

### Feature 1: Medical Report Understanding
- **OCR Engine:** `TesseractBackend` (`pdfplumber` native text extraction with `pytesseract` fallback for scanned PDFs/images, bilingual eng+hin).
- **Report Parser:** Panel regex matchers for **CBC** (13 metrics), **Lipid Profile** (7 metrics), **Thyroid Function** (5 metrics), and **HbA1c** (2 metrics).
- **Bilingual Explainer:** Generates non-diagnostic, plain-language summaries in **English & Hindi**, flagging status as `normal`, `high`, `low`, or `unknown`.
- **Privacy Enforcement:** DB-level and query-level `owner_id` scoping via `ScopedRepository` base class.

### Feature 2: Health Timeline & Anomaly Detection
- **Timeline Repository:** Auto-populates `timeline_events` upon report parse completion.
- **Z-Score Trend Detector (`zscore.py`):** Pure-Python slope calculator, streak counter, and out-of-range baseline detector.
- **ML Anomaly Classifier (`model.py`):** `IsolationForest` model with Z-score fallback for series with <5 historical points.
- **Bilingual Summaries (`detector.py`):** Plain-language trend trajectory descriptions in English and Hindi.
- **Endpoints:** `GET /timeline` (summary per test) and `GET /timeline/{test_name}` (chronological history).

### Feature 3: Evidence-Grounded Q&A (RAG) + Safety Layer + React UI
- **Migration 003:** Created `knowledge_documents` (pgvector 384-dim embeddings), `qa_sessions`, and `qa_messages` tables.
- **Deterministic Safety Layer (`services/ai-service/safety/red_flags.py`):** Pure-regex guardrail executing in **<100ms BEFORE any RAG/LLM call**. Covers 5 emergency categories (cardiac, GI bleeding, sudden vision loss, stroke, suicidal ideation) returning fixed emergency guidance.
- **RAG Engine (`services/ai-service/rag/`):**
  - `embedder.py`: `all-MiniLM-L6-v2` 384-dim sentence-transformers model.
  - `ingester.py`: Ingestion pipeline for curated plain-text guides (WHO, NHS, ICMR).
  - `retriever.py`: Hybrid search (pgvector cosine search + user report history keyword matching).
  - `synthesizer.py`: Template-based bilingual answer generator with inline citations (`[1]`, `[2]`).
- **React Frontend (`apps/web/`):** React + Vite dark mode UI featuring Auth, Dashboard, Upload & Parser View, Timeline Charts, and Evidence Q&A Chat with citation modals and safety alert banners.

---

## 📈 4. Empirical Evaluation Results

The codebase includes two automated evaluation scripts logging quantitative performance metrics in `docs/DEV_LOG.md`:

### A. Anomaly Detection Evaluation (`data/datasets/generate_synthetic_anomaly_data.py`)
Tested on 200 synthetic CBC patient trajectories (20% injected anomalies):
- **Precision:** `0.7358`
- **Recall:** `0.9750` (Prioritised high recall to avoid missing real anomalies)
- **F1 Score:** `0.8387`
- **False-Alert Rate:** `0.0875` (8.75%)

### B. RAG Q&A Evaluation (`data/datasets/evaluate_rag.py`)
Tested on 50 labeled medical Q&A evaluation pairs across all 4 panels:
- **Retrieval Precision@5:** `82.0%` (41/50)
- **Citation Correctness:** `100.0%` (50/50 — all citations accurately link to source guidelines)
- **Hallucination Rate:** `18.0%` (9/50 — non-matching template fallback when query exceeds KB scope)

---

## 🧪 5. Automated Test Suite (132/132 Passing)

Run the full unit test suite from the repository root:

```bash
$env:PYTHONPATH="."; python -m pytest -v
```

### Breakdown of 132 Unit Tests:
- `tests/unit/ai-service/test_anomaly.py`: 32 tests (Z-score edge cases, model fallback, 11 tone-rule tests)
- `tests/unit/ai-service/test_parser.py`: 21 tests (OCR fallback, panel parsers, bilingual explainer tone)
- `tests/unit/ai-service/test_safety.py`: 35 tests (5 red-flag categories, 10 non-trigger normal questions, <100ms performance, edge cases)
- `tests/unit/ai-service/test_rag.py`: 17 tests (retriever scoring, synthesizer citations, ingester chunking, cross-user scoping)
- `tests/unit/auth-service/test_auth.py`: 8 tests (JWT roundtrip, invalid tokens, email-enum-safe auth)
- `tests/unit/health-service/test_reports.py`: 5 tests (report CRUD, ScopedRepository enforcement)
- `tests/unit/health-service/test_timeline.py`: 7 tests (timeline summary, chronological sorting, cross-user isolation)
- `tests/unit/health-service/test_qa.py`: 7 tests (Q&A proxy contract, safety trigger through proxy, locale validation)

---

## 🚀 6. Local Setup & Execution Guide for New Contributors

### Prerequisites:
- **Python:** 3.11.x
- **Node.js:** v18+ or v22+
- **Tesseract OCR:** Installed on system (optional for synthetic/PDF native text)
- **PostgreSQL:** Optional for unit tests (tests use mocked DB sessions), required for live DB integration (`pgvector` extension enabled)

### Step 1: Clone & Setup Python Environment
```bash
git clone https://github.com/Priyanshugoyal2301/MediVault.git
cd MediVault

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# Install service dependencies
pip install -r services/auth-service/requirements.txt
pip install -r services/health-service/requirements.txt
pip install -r services/ai-service/requirements.txt
```

### Step 2: Run Tests
```bash
$env:PYTHONPATH="."; python -m pytest -v
```

### Step 3: Run RAG Evaluation
```bash
python data/datasets/evaluate_rag.py
```

### Step 4: Launch Frontend (React + Vite)
```bash
cd apps/web
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🔮 7. What Is Pending / Recommended Next Contributions

For a new contributor looking to take MediVault AI to production or extend its capabilities, here is the prioritized roadmap:

### 🎯 Short-Term Enhancements (Production Readiness):
1. **Live LLM Integration for RAG:**
   - **Current state:** RAG uses template-based answer synthesis (`synthesizer.py`) to avoid external API key requirements.
   - **Improvement:** Integrate a live LLM API (e.g. Gemini 1.5 Flash / Pro via `@google/generative-ai` or OpenAI) inside `synthesizer.py`.
   - **Constraint:** Keep the `check_safety()` guardrail executing **BEFORE** the LLM call, and enforce citation formatting.

2. **Full Async Docker Compose Orchestration:**
   - Wire PostgreSQL + pgvector container with automatic Alembic migration run (`alembic upgrade head`) on container startup in `docker-compose.yml`.

3. **Handwritten & Mobile Camera OCR Enhancement:**
   - **Current state:** Tesseract handles printed PDF lab reports well.
   - **Improvement:** Add an optional vision-LLM or specialized OCR pipeline (e.g., PaddleOCR or Google Cloud Vision API fallback) for handwritten Indian lab reports.

### 🚀 Long-Term Roadmap (Post-MVP Scope):
1. **MIMIC-IV Benchmark Run:** Validate anomaly detection model on MIMIC-IV clinical laboratory dataset.
2. **Prescription OCR & Medicine Reminders:** Extract drug names, dosage, and schedules.
3. **Ayushman Bharat Health Account (ABHA) Integration:** Government health ID verification for the Indian healthcare ecosystem.
4. **Multi-Profile Family Accounts:** Family member profile switching under a master account.

---

## 🔒 8. Non-Negotiable Development Rules

Any developer contributing to MediVault AI **MUST** adhere to the following rules documented in `docs/04_AGENT_RULES.md` and `docs/01_PROJECT_CONTEXT.md`:

1. **Owner-Scoped Queries:** All health-data queries in `health-service` MUST use `ScopedRepository` and include `owner_id`. Never write global or unscoped SELECT queries on patient data.
2. **Deterministic Safety FIRST:** The safety layer (`services/ai-service/safety/red_flags.py`) MUST run on every question BEFORE any RAG/LLM invocation. Emergency messages must be returned verbatim.
3. **No Diagnostic Claims:** Explanations and answers MUST use non-diagnostic phrasing ("commonly associated with", "may indicate", "consult your doctor"). Never state "you have X" or "you are diagnosed with Y".
4. **Redacting Logger:** Always import logger from `packages.shared_utils` (`from packages.shared_utils import get_logger`). Never import raw `logging` or print health values to log files.
5. **No Broken Tests:** Ensure all 132 pytest unit tests pass before committing code (`$env:PYTHONPATH="."; python -m pytest`).

---

**Happy Coding!** MediVault AI is built to be clean, modular, and easy to extend. Refer to `docs/02_ARCHITECTURE.md` and `docs/DEV_LOG.md` for historical design rationale.
