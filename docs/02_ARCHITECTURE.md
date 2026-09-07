# ARCHITECTURE & PROJECT STRUCTURE

> Goal: an MVP that is small in scope but built like a real product — cleanly separated services, so future features (biometrics, avatar, ID verification, family accounts) plug in without a rewrite.

## 1. High-level system design

```
                    Client (Web/Mobile)
                            |
                     API Gateway / BFF
                            |
        --------------------------------------------
        |                   |                       |
  Auth Service       Core Health Service      AI/ML Service
  (pluggable —       (reports, timeline,      (report parsing,
   swap in biometric  users, data ownership)   anomaly detection,
   / ID verification                            RAG Q&A engine)
   later without                                       |
   touching this)                              Vector DB + Medical
                                                 Knowledge Store
        --------------------------------------------
                            |
                    Primary Database (Postgres)
                            |
                  Encrypted Storage (documents/reports)
```

**Why this shape:** every future feature the roadmap mentions (biometrics, ID verification, avatar) attaches to the Auth Service or as a new service alongside the existing ones — it should never require touching the Core Health or AI/ML services. Keep service boundaries strict from day one even though MVP may deploy them as one process.

## 2. Recommended stack (adjust only with explicit reasoning logged in the dev log)

- **Backend:** Python, FastAPI (async, good ML/NLP ecosystem fit)
- **Frontend:** React or Next.js (web-first MVP; mobile wrapper later)
- **Primary DB:** PostgreSQL
- **Vector store:** pgvector (inside Postgres) for MVP — avoids running a second database; migrate to a dedicated vector DB only if scale demands it
- **Auth:** JWT-based, stateless — designed so a biometric/ID-verification provider can be swapped in as an additional auth strategy later
- **File/report storage:** encrypted object storage (local disk abstraction in dev, S3-compatible in prod)
- **ML/NLP:** statistical personal-series anomaly; BM25 retrieval; optional Unlimited-OCR; optional Medical Test Normalizer (`USE_ML_NORMALIZER`); optional MiniLM dense retrieval
- **Models package:** `models/ocr/` (Phase 1), scaffolds for risk/retrieval/normalizer/…  
- **Containerization:** Docker + docker-compose for local dev, structured so each service has its own Dockerfile

## 3. Repository structure

```
/project-root
  /apps
    /web                # frontend app
    /api                # FastAPI app (BFF / gateway layer)
  /services
    /auth-service        # auth, sessions, future biometric/ID hooks
    /health-service       # reports, timeline, user health data (CRUD, ownership)
    /ai-service            # anomaly detection model + RAG pipeline
  /packages
    /shared-types          # shared schemas/DTOs used by multiple services
    /shared-utils            # shared logging, error handling, config loading
  /data
    /knowledge-base           # curated medical source documents for retrieval
    /datasets                  # training/eval data for anomaly detection (or scripts to fetch it)
  /infra
    docker-compose.yml
    /migrations                 # DB schema migrations
  /docs
    01_PROJECT_CONTEXT.md
    02_ARCHITECTURE.md
    03_MVP_SCOPE.md
    DEVELOPER_RULES.md
    DEMO_SCRIPT.md
    FEATURE_FLAGS.md
  /tests
    /unit
    /integration
```

Rules:
- No service reaches into another service's database tables directly — only through its API.
- Anything shared across services goes in `/packages`, never copy-pasted between services.
- Every service has its own `README.md` stating what it owns and its API contract.

## 4. Data model essentials (MVP)

- `users` — identity, auth credentials/tokens, locale preference
- `reports` — uploaded report metadata, parsed status, owner_id
- `report_values` — extracted structured values (test name, value, unit, reference range, date) linked to a report
- `timeline_events` — derived from report_values, used for trend/anomaly detection
- `qa_sessions` / `qa_messages` — user questions, retrieved sources, generated answers, citations
- `knowledge_documents` — the curated medical corpus + embeddings for retrieval

Every table that stores personal health data needs an `owner_id` and must be scoped by it at the query layer, not just the API layer — this is the actual privacy enforcement point.

## 5. Security & privacy (build these into MVP, not later)

- Encrypt report files and sensitive columns at rest.
- All access to a user's data requires their token; no shared/global read endpoints.
- Deletion endpoint must cascade: primary record, derived timeline entries, and embeddings tied to that user's uploaded documents (do NOT delete shared knowledge_documents, only the user's own report data).
- Log access to health data (who accessed what, when) — required for any real healthcare product and cheap to add now.
- No health data in application logs, ever (redact before logging).

## 6. Scaling considerations (design for, don't over-build for)

- Stateless services behind the API gateway so horizontal scaling is just adding instances.
- Long-running work (OCR, embedding generation, anomaly detection runs) goes through a job queue, not inline in the request — even a simple one (e.g. a Postgres-backed queue or Redis+RQ) — so report upload doesn't block on ML processing.
- Keep the knowledge base ingestion pipeline separate from the live Q&A path, so re-indexing sources doesn't affect uptime.
