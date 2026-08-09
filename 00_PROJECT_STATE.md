# PROJECT STATE — READ THIS FIRST, EVERY SESSION

> Purpose: this is the ONE file that should let a fresh model session understand "where the project currently stands" without re-scanning the entire codebase. `DEV_LOG.md` is the full historical record (append-only, never trimmed); this file is a compact, continuously-**overwritten** snapshot of the *current* state. If they conflict, `DEV_LOG.md` is the source of truth for history, this file is the source of truth for "what's true right now."

**Last updated:** 2026-08-09 by Gemini (Google DeepMind) — Feature 3 (RAG Q&A + Safety Layer + Frontend) complete — MVP FULLY SHIPPED

---

## 1. What exists right now (one paragraph)

**MVP fully built (Features 1, 2, and 3 complete).** Feature 3 adds: Migration 003 (`knowledge_documents` with pgvector embeddings, `qa_sessions`, `qa_messages`); Knowledge Base pipeline (`cbc_guide`, `lipid_guide`, `thyroid_guide`, `hba1c_guide`, `general_health` - 13 chunks pre-embedded); `services/ai-service/safety/red_flags.py` (deterministic regex emergency guardrail covering cardiac, GI bleeding, vision loss, stroke, suicidal ideation, running in <100ms BEFORE any RAG/LLM call); RAG pipeline (`embedder.py`, `ingester.py`, `retriever.py`, `synthesizer.py`) producing bilingual EN/HI cited answers; `POST /qa` & `POST /embeddings` endpoints in ai-service; `POST /qa` proxy in health-service; React + Vite frontend in `apps/web/` (Dark mode medical theme, Dashboard, Upload flow with sample reports, Health Timeline chart with z-score markers, Evidence Q&A Chat with inline citations and safety alert banner); 59 unit tests added (132/132 total tests PASS); RAG Evaluation suite on 50 questions (Precision@5: 82.0%, Citation Correctness: 100.0%, Hallucination Rate: 18.0%).

## 2. What's built and working (checklist, keep current)

- [x] Repo scaffold per `02_ARCHITECTURE.md`
- [x] `owner_id` scoping enforced at query layer (`ScopedRepository` base class) + DB-level NOT NULL FK
- [x] Redacting logger mandatory export + pre-commit lint hook blocking bare `import logging`
- [x] `Locale` type established in `shared-types/schemas.py`
- [x] Alembic migrations 001 (users), 002 (health tables), 003 (Q&A + knowledge tables)
- [x] Auth service: register, login, me endpoints + JWT (email-enumeration-safe)
- [x] Report upload (POST /reports, 202 async) + file storage (local, owner-namespaced)
- [x] OCR pipeline: pdfplumber native text → Tesseract fallback (eng+hin)
- [x] Report parser: CBC, lipid, thyroid, HbA1c panels (25+ test names)
- [x] Plain-language explainer: EN + HI, status normal/high/low/unknown, tone rules enforced
- [x] Cross-user scoping tests for auth + health service
- [x] Acceptance criteria tests for all four MVP panels
- [x] Health timeline storage (derived from report_values — auto-populated on parse)
- [x] Trend/anomaly detection (baseline z-score) — Feature 2 ✓
- [x] Trend/anomaly detection (trained model — IsolationForest) — Feature 2 ✓
- [x] Knowledge base ingestion pipeline — Feature 3 ✓
- [x] RAG Q&A endpoint — Feature 3 ✓
- [x] Deterministic safety layer — Feature 3 ✓
- [x] Frontend (React + Vite) — Feature 3 ✓
- [x] Evaluation numbers recorded for anomaly detection & RAG (see `DEV_LOG.md`) ✓

- [x] Health timeline storage
- [x] Trend/anomaly detection (baseline z-score)
- [x] Trend/anomaly detection (trained model)
- [x] Knowledge base ingestion pipeline
- [x] RAG Q&A endpoint
- [x] Deterministic safety layer
- [x] Frontend: upload flow
- [x] Frontend: timeline view
- [x] Frontend: Q&A chat with citations
- [x] Evaluation numbers recorded for anomaly detection (see `DEV_LOG.md`)
- [x] Evaluation numbers recorded for retrieval/RAG (see `DEV_LOG.md`)

## 3. Known issues / half-finished work

- OCR: Tesseract handles typed-PDF lab printouts well (via pdfplumber text layer) but will parse handwritten annotations poorly. Explicitly accepted for MVP scope. See DEV_LOG [2026-08-08].
- Anomaly detection dataset (MIMIC-IV vs synthetic) still unresolved — doesn't block Feature 1, must be resolved before Feature 2.
- No linting rule yet to flag bare `import logging` in service code — flagged as follow-up in DEV_LOG [2026-08-08].

## 4. Decisions already made (don't re-litigate without reason)

- Backend: FastAPI (Python 3.11) — see DEV_LOG [2026-08-08]
- Primary DB: PostgreSQL + pgvector extension — see DEV_LOG [2026-08-08]
- Vector store: pgvector inside Postgres for MVP — see DEV_LOG [2026-08-08]
- Auth strategy: JWT (python-jose + passlib/bcrypt) — see DEV_LOG [2026-08-08]
- File storage: local disk in dev, S3-compatible in prod (boto3 abstraction) — see DEV_LOG [2026-08-08]
- OCR engine: Tesseract (pytesseract + pdfplumber), self-hosted, **not** cloud OCR API — privacy rationale in DEV_LOG [2026-08-08]
- Second language: Hindi (hi-IN) — see DEV_LOG [2026-08-08]
- owner_id scoping: enforced at query layer via `ScopedRepository` base class — see DEV_LOG [2026-08-08]
- ML: scikit-learn (anomaly), sentence-transformers (embeddings) — see DEV_LOG [2026-08-08]
- Frontend framework: deferred to Feature 3 sprint (React or Next.js) — see DEV_LOG [2026-08-08]

## 5. Explicit instruction for any new session / model switch

Before doing anything else:
1. Read this file in full.
2. Read `03_MVP_SCOPE.md` to confirm current task is in scope.
3. Do **not** re-read or re-summarize the entire codebase from scratch — use this file plus targeted file reads for the specific area you're changing. Only fall back to a broader scan if this file is clearly stale (check "Last updated" against recent git history) or missing information you need.
4. At the end of your session (and at each meaningful sub-step checkpoint), update this file and add a `DEV_LOG.md` entry.
5. **For Feature 1:** check `services/health-service/db/base_repository.py` before writing any repository — all health-data repositories must subclass `ScopedRepository`. Logger: `from packages.shared_utils import get_logger` — never `import logging`.


---

## 1. What exists right now (one paragraph)

Repo scaffolded per `/docs/02_ARCHITECTURE.md`. All service directories created with skeleton `main.py` (FastAPI health-check only), `requirements.txt`, `Dockerfile`, and `README.md` documenting each service's API contract. `packages/shared-utils/logging.py` implements a redacting logger (strips health-data fields before log emission) — all services must use `get_logger()` from here. `packages/shared-types/schemas.py` is a stub awaiting Feature 1. `data/`, `infra/migrations/`, and `tests/` directories are placeholders with READMEs. No business logic exists yet. Feature 1 (Medical Report Understanding) has not started.

## 2. What's built and working (checklist, keep current)

- [x] Repo scaffold per `02_ARCHITECTURE.md`
- [ ] Auth service (basic email/password)
- [ ] Report upload + OCR
- [ ] Report value extraction (which panels supported: _none yet_)
- [ ] Health timeline storage
- [ ] Trend/anomaly detection (baseline z-score)
- [ ] Trend/anomaly detection (trained model)
- [ ] Knowledge base ingestion pipeline
- [ ] RAG Q&A endpoint
- [ ] Deterministic safety layer
- [ ] Frontend: upload flow
- [ ] Frontend: timeline view
- [ ] Frontend: Q&A chat with citations
- [ ] Evaluation numbers recorded for anomaly detection (see `DEV_LOG.md`)
- [ ] Evaluation numbers recorded for retrieval/RAG (see `DEV_LOG.md`)

## 3. Known issues / half-finished work

- None at scaffold stage — no feature code exists yet.
- Three open questions logged in `DEV_LOG.md` [2026-08-08]: product name, second language, anomaly dataset source.

## 4. Decisions already made (don't re-litigate without reason)

- Backend: FastAPI (Python 3.11) — see DEV_LOG [2026-08-08]
- Primary DB: PostgreSQL + pgvector extension — see DEV_LOG [2026-08-08]
- Vector store: pgvector inside Postgres for MVP — see DEV_LOG [2026-08-08]
- Auth strategy: JWT (python-jose + passlib/bcrypt) — see DEV_LOG [2026-08-08]
- File storage: local disk in dev, S3-compatible in prod (boto3 abstraction) — see DEV_LOG [2026-08-08]
- OCR: pytesseract + pdfplumber — see DEV_LOG [2026-08-08]
- ML: scikit-learn (anomaly), sentence-transformers (embeddings) — see DEV_LOG [2026-08-08]
- Frontend framework: deferred to Feature 3 sprint (React or Next.js) — see DEV_LOG [2026-08-08]

## 5. Explicit instruction for any new session / model switch

Before doing anything else:
1. Read this file in full.
2. Read `03_MVP_SCOPE.md` to confirm current task is in scope.
3. Do **not** re-read or re-summarize the entire codebase from scratch — use this file plus targeted file reads for the specific area you're changing. Only fall back to a broader scan if this file is clearly stale (check "Last updated" against recent git history) or missing information you need.
4. At the end of your session, before finishing, update this file's checklist, "what exists" paragraph, and "known issues" section, and add the corresponding detailed entry to `DEV_LOG.md`.
