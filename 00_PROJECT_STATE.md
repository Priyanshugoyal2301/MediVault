# PROJECT STATE — READ THIS FIRST, EVERY SESSION

> Compact current-state snapshot. History lives in `docs/DEV_LOG.md`. Prefer honesty over marketing.

**Last updated:** 2026-08-28 — ML platform Phases 1–9 integrated (all feature flags default off); Phase 10 repository consolidation

---

## 1. What exists right now

MediVault is a **hackathon-ready prototype**: FastAPI microservices (auth / health / AI) behind a JWT BFF that validates tokens and injects trusted `X-User-ID`. The React frontend talks to live APIs (Vite proxy → `:8000`). Deterministic **demo seed** panels (`POST /reports/demo/seed`) populate CBC/Lipid + timeline without OCR.

**Live demo path (flags off):** Tesseract + regex OCR, template bilingual explanations, BM25+intent RAG with template synthesizer, deterministic safety layer, and **statistical personal-series anomaly monitoring** (z-score / CUSUM — not a persisted clinical ML model).

**ML platform (Phases 1–9, default off):** Unlimited-OCR adapter, test normalizer, semantic retrieval, disease risk, biomarker forecasting, health score + SHAP, ML anomaly detection, image quality gate, and platform audit/benchmark tooling — all behind feature flags with graceful fallbacks. See `docs/MODEL_REGISTRY.md` and `docs/FEATURE_FLAGS.md`.

This is **not** a production PHI system (no encrypt-at-rest, no durable job queue, no clinical validation).

---

## 2. Status checklist

### Implemented (demoable)

- [x] Auth: register / login / me (JWT, bcrypt, password min length 8)
- [x] API gateway BFF: JWT verify, strip client `X-User-ID`, proxy auth/health
- [x] Report upload + magic-byte MIME check + async parse
- [x] Demo seed reports (CBC, Lipid) with explanations + timeline history
- [x] OCR/parse/explain pipeline (legacy default; Unlimited-OCR optional)
- [x] Timeline summary + `/timeline/{test}/anomaly` proxy to AI
- [x] Q&A proxy loads owner-scoped report values into AI retriever
- [x] Frontend wired to real APIs (auth, upload/seed, timeline, Q&A)
- [x] Honest RAG eval (Hit@5 / MRR; BM25+intent default)
- [x] ML Phases 1–9 source + phase test suites (flags default off)
- [x] Research site (`apps/research-site/`) for portfolio / faculty review

### Prototype / partial

- [ ] Encryption at rest / TLS termination
- [ ] Durable OCR job queue (still FastAPI BackgroundTasks)
- [ ] pgvector retrieval in the live Q&A path (in-memory KB chunks today)
- [ ] `embed_report` vector write path (stub)
- [ ] Account deletion / consent capture / access audit log
- [ ] HTTP end-to-end integration test suite (phase unit tests exist; no full E2E)

### Intentionally deferred

- Full WCAG AA audit
- S3 storage backend
- Logout/token revocation store
- Clinical / multi-site validation of ML models

---

## 3. How to run the demo (local)

```bash
# 1) Postgres
docker-compose up -d postgres

# 2) .env from .env.example — set POSTGRES_PASSWORD, AUTH_SECRET_KEY, INTERNAL_SERVICE_KEY

# 3) Migrations (through 004)
cd infra/migrations && alembic upgrade head && cd ../..

# 4) Dev deps (one venv)
pip install -r requirements-dev.txt

# 5) Services (separate terminals, repo root on PYTHONPATH)
$env:PYTHONPATH="."
# auth :8001, health :8002, ai :8003, api :8000
# web: cd apps/web && npm install && npm run dev  → :3000
```

See `docs/DEMO_SCRIPT.md` for the judge path.

---

## 4. Known issues

- Default anomaly path is statistical — disclose thresholds and leave-last-out causality.
- RAG default is BM25+intent — do not claim MiniLM numbers unless dense path was explicitly enabled.
- ML Phases 4–8 metrics are largely **synthetic** — not clinical validation.
- OCR quality on real Indian lab scans is not rigorously measured.
- Model artifacts are **not** in git — run `models/*/train.py` if enabling ML flags.

---

## 5. Decisions

- Public entry = BFF only for browser traffic
- AI service not proxied through BFF
- Prefer deterministic demo seed for live judging reliability
- Template synthesizer kept (safer/faster than free-form LLM)
- All ML flags default **off** — demo uses statistical monitor + BM25
- Plan C: IE aliases + tone scrub; dense MiniLM only as warm optional (`MEDIVAULT_USE_DENSE=1`)
