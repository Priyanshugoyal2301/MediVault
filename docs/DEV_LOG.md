# DEV LOG

> Append-only project log. Every meaningful change, decision, or removal gets an entry here.
> Newest entries at the top. Do not delete old entries — this is the one file in the repo that's allowed to grow; everything else should stay clean per `04_AGENT_RULES.md`.

## How to write an entry

```
## [YYYY-MM-DD] Short title of the change

**Type:** feature | decision | removal | fix | evaluation-result | open-question

**What changed:**
Plain description of what was built, decided, or removed.

**Why:**
The reasoning — especially if there was a tradeoff or an alternative that was rejected.

**Affects:**
Which service(s)/file(s)/feature(s) this touches.

**Follow-up needed:**
Anything left open, or "none".
```

---

## [2026-08-09] Feature 2 complete: Health Timeline + Anomaly Detection

**Type:** feature + evaluation-result

**What changed:**

- **services/health-service:**
  - `db/repositories/timeline_repository.py` — `TimelineRepository` subclassing `ScopedRepository`; `bulk_create_events`, `list_events_for_test`, `get_timeline_summary` (all owner-scoped).
  - `routers/timeline.py` — `GET /timeline` (summary) + `GET /timeline/{test_name}` (history).
  - `routers/reports.py` — updated `_trigger_parse` background task to automatically populate `timeline_events` rows after a successful parse (values with `date_of_test` only).
  - `main.py` — registered timeline router.

- **services/ai-service:**
  - `anomaly/zscore.py` — pure-Python Z-score trend detector; normalised least-squares slope for trend direction; out-of-range streak counter; no dependencies beyond stdlib.
  - `anomaly/model.py` — IsolationForest anomaly scorer; z-score fallback for <5 data points; normalised score [-1, +1].
  - `anomaly/detector.py` — unified pipeline; bilingual EN+HI plain-language summaries; strict non-diagnostic tone.
  - `routers/anomaly.py` — `POST /anomaly/detect`.
  - `main.py` — registered anomaly router.

- **Test suite:**
  - `tests/unit/health-service/test_timeline.py` — 7 tests (repo: skip-no-date, chronological order, summary grouping, cross-user scoping; endpoints: 200/401/404).
  - `tests/unit/ai-service/test_anomaly.py` — 32 tests (Z-score edge cases, model fallback, detector fields, 11 tone-rule parametrised tests EN+HI, endpoint schema/validation/sort).
  - All 39 new tests PASS.

- **conftest.py** — extended `HyphenatedModuleFinder` to also handle `packages.*` namespace (fixes `packages.shared_utils` import in endpoint tests).

- **Synthetic evaluation:** `data/datasets/generate_synthetic_anomaly_data.py` — 200 synthetic CBC patients, 20% with injected Hb anomalies.

**Evaluation results (anomaly detection — 2026-08-09):**

| Metric | Value |
|---|---|
| Precision | 0.7358 |
| Recall | 0.9750 |
| F1 Score | 0.8387 |
| False-Alert Rate | 0.0875 |
| TP/FP/FN/TN | 39/14/1/146 |

Model: Z-score baseline (|z|>2) + IsolationForest (contamination=0.1, n_estimators=100) with z-score fallback for <5 points.

**Why:**

High recall (0.975) is prioritised over precision for an MVP — missing a real anomaly (false negative, FN=1) is worse than flagging a normal reading (FP=14). The 8.75% false-alert rate is acceptable for a "this looks unusual, please check with your doctor" message.

**Affects:** ai-service (anomaly), health-service (timeline + reports), conftest, all tests.

**Follow-up needed:**

- Install `python-jose` in test environment to fix 8 pre-existing auth test failures (unrelated to Feature 2).
- Consider a real MIMIC-IV dataset run before Feature 3 GA.
- Feature 3 (RAG Q&A + safety layer + frontend) is next.

---

## [2026-08-08] Feature 1 complete: Medical Report Understanding

**Type:** feature

**What was built (four sub-steps):**

### Sub-step 1: Auth DB + Auth Service
- `services/auth-service/core/config.py` — pydantic-settings config
- `services/auth-service/core/security.py` — `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`; JWT secret is injected (not read from env directly), making it unit-testable
- `services/auth-service/db/models.py` — User SQLAlchemy model
- `services/auth-service/db/session.py` — async session factory
- `services/auth-service/db/repositories/user_repository.py` — email-normalised lookup, soft-delete; no global user list
- `services/auth-service/routers/auth.py` — `POST /auth/register` (201+JWT), `POST /auth/login` (401-safe for wrong password AND no user, prevents email enumeration), `GET /auth/me` (JWT-scoped — user_id from token only, can never return another user's profile)
- Tests: JWT roundtrip, wrong-secret, malformed token, password hashing, cross-user scoping assertion

### Sub-step 2: Report Upload Endpoint
- `services/health-service/core/config.py` — storage backend switch (local/S3), ai-service URL
- `services/health-service/db/models.py` — Report, ReportValue, TimelineEvent (all owner_id nullable=False matching migration 002)
- `services/health-service/db/repositories/report_repository.py` — **subclasses `ScopedRepository`**; adds `create_report`, `set_parsing_status`, `save_report_values`, `get_values_for_report` — all owner-scoped
- `services/health-service/storage/base.py` — StorageBackend Protocol (swap local → S3 without touching router)
- `services/health-service/storage/local_storage.py` — files namespaced by owner_id, paths not logged raw
- `services/health-service/routers/reports.py` — `POST /reports` (202 async, triggers parse background task), `GET /reports` (list), `GET /reports/{id}` (with values), `DELETE /reports/{id}` (hard cascade). `owner_id` always from `X-User-ID` header — never from request body. 404 for both not-found and wrong-owner (no enumeration).

### Sub-step 3: OCR + Parsing Pipeline
- `services/ai-service/ocr/base.py` — `OcrBackend` Protocol (swappable — see DEV_LOG Tesseract entry)
- `services/ai-service/ocr/tesseract_backend.py` — native PDF text via pdfplumber (primary), Tesseract via PyMuPDF (fallback for scanned/image PDFs), eng+hin language pack
- `services/ai-service/parsers/patterns.py` — regex patterns for CBC (13 tests), lipid profile (7), thyroid (5), HbA1c (2). Handles Indian lab formats (colon-separated, table, comma-decimal, name aliases)
- `services/ai-service/parsers/report_parser.py` — `ReportParser(ocr=OcrBackend)` → `[ParsedValue]`; deduplicates on test_name (first match wins), normalises comma-decimal

### Sub-step 4: Plain-language Explanation Generation
- `services/ai-service/explainer/templates.py` — `TestInfo` dataclass + entries for all MVP-required tests in both English and Hindi; `_FALLBACK` for unlisted tests; TONE RULES embedded in docstring (non-negotiable, 01_PROJECT_CONTEXT.md §4)
- `services/ai-service/explainer/explainer.py` — `explain()` → `Explanation(status, explanation_en, explanation_hi)`; status: normal/high/low/unknown (unknown when no ref range); never contains "you have X" or "diagnosed with"
- `services/ai-service/routers/parse.py` — internal `POST /parse` wires OCR + parser + explainer; returns bilingual structured values to health-service

**Tests written:**
- `tests/unit/auth-service/test_auth.py` — JWT, password, cross-user scoping
- `tests/unit/ai-service/test_parser.py` — CBC/lipid/thyroid/HbA1c extraction acceptance criteria + explainer tone rules (no diagnosis keywords in EN or HI)
- `tests/unit/health-service/test_reports.py` — ScopedRepository structural check, explainer integration

**Privacy decisions captured:**
- `owner_id` from `X-User-ID` header — set by API gateway from validated JWT; health-service never reads JWT itself
- 404 for wrong-owner (not 403) — prevents record enumeration
- File paths namespaced by owner_id — prevents cross-user file access by path guessing
- Storage paths not logged raw — only `path_suffix` (filename only) logged

**Known limitations (MVP scope, not defects):**
- Background parse uses FastAPI `BackgroundTasks` — not a persistent queue (no retry on process crash). Flagged for upgrade before production.
- OCR accuracy on handwritten annotations: accepted limitation, see DEV_LOG Tesseract entry.
- `locale` field in parse request is hardcoded to `en-IN` in health-service until user locale is propagated from auth-service (Feature 3 work).

**Acceptance criteria status:**
- ✅ PDF upload accepted (MIME check, 20 MB max)
- ✅ OCR pipeline: native text layer primary, Tesseract fallback
- ✅ CBC panel extraction (13 tests including Hb, WBC, RBC, Platelets, MCV, MCH, MCHC, differentials)
- ✅ Lipid profile extraction (7 values including TC, LDL, HDL, TG, VLDL)
- ✅ Thyroid extraction (TSH, T3, T4, Free T3, Free T4)
- ✅ HbA1c extraction (HbA1c, eAG)
- ✅ Plain-language summary per value with status (normal/high/low/unknown)
- ✅ English + Hindi explanations
- ✅ Tone rules: no diagnosis keywords verified by test suite

---

## [2026-08-08] Pre-commit lint rule: bare 'import logging' blocked outside shared-utils

**Type:** decision + feature

**What changed:**
- `pyproject.toml` — ruff config (lint + format, Python 3.11 target)
- `scripts/check_no_raw_logging.py` — script that fails if `import logging` appears outside `packages/shared-utils/logging.py`
- `.pre-commit-config.yaml` — wires ruff + the custom hook as pre-commit checks

**Why:**
`__all__ = ["get_logger"]` in shared-utils makes the safe logger what IDEs surface, but doesn't fail at commit or CI time. `import logging` still works at runtime with no friction. The script adds a second enforcement layer: any commit containing a bare `import logging` in a service file will fail the hook. This makes bypassing the safe logger visible in every PR, not just in code review if someone notices it.

**Affects:**
`pyproject.toml` (new), `scripts/check_no_raw_logging.py` (new), `.pre-commit-config.yaml` (new).

**Follow-up needed:**
Wire this check into the CI pipeline (GitHub Actions / equivalent) when CI is set up — currently it only runs as a pre-commit hook on local commit.

---

## [2026-08-08] DB-level owner_id enforcement: NOT NULL FK in all health tables

**Type:** decision + feature

**What changed:**
Alembic infrastructure created (`infra/migrations/alembic.ini`, `env.py`, `script.py.mako`).
Two initial migrations:
- `001_create_users_table.py` — users table with locale constraint (`CHECK IN ('en-IN', 'hi-IN')`), soft-delete, is_active flag.
- `002_create_health_tables.py` — reports, report_values, timeline_events — every table has `owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE`.

**Why — two-layer privacy enforcement:**
Layer 1 (app): `ScopedRepository` base class requires `owner_id` in every method — bypassing it requires actively working around the type system.
Layer 2 (DB): `NOT NULL FK + ON DELETE CASCADE` on `owner_id` means even a raw SQL query or a future bypass of the repository class cannot insert a row without a valid owner, and cannot read across users if the query filters by owner_id (which the repository always does). A row without an owner simply cannot exist in the DB.

These two layers are complementary:
- App layer catches mistakes during development (type errors, linter).
- DB layer catches mistakes at runtime (any raw query path that reaches the DB).

**Affects:**
`infra/migrations/` — alembic setup + two migration files. All health-service repositories must subclass `ScopedRepository`; all health tables have owner_id NOT NULL FK.

**Follow-up needed:**
Add `psycopg2-binary` to a shared dev requirements file for Alembic to use (asyncpg is for FastAPI runtime; psycopg2 is for Alembic sync migrations). Log when done.

---

## [2026-08-08] Structural enforcement: owner_id scoping at query layer

**Type:** decision + feature

**What changed:**
Created `services/health-service/db/base_repository.py` — a `ScopedRepository[ModelT]` generic base class.

All health-service repositories that store personal health data must subclass `ScopedRepository`. The class exposes only four methods: `get_by_id`, `list_for_owner`, `create`, `delete_for_owner` — every one requires `owner_id: UUID` as a mandatory parameter. There is no method that queries without an `owner_id`.

**Why:**
`02_ARCHITECTURE.md §4` states: "every table that stores personal health data needs an `owner_id` and must be scoped by it at the **query layer**, not just the API layer." This is the actual privacy enforcement point, not the API handler's token check (which is a second layer, not the first).

Without a base class, the rule is a comment that future sessions can accidentally violate under time pressure. With a base class, a query without `owner_id` requires actively working around the type system — it becomes the harder path, not the easier one.

**Design notes:**
- `get_by_id` returns `None` for both "not found" and "wrong owner" — callers cannot distinguish them, which prevents record enumeration attacks.
- Background/admin jobs that legitimately need unscoped queries must use a separate `AdminRepository` (not yet created), not this class. That separation makes it auditable.

**Affects:**
`services/health-service/db/base_repository.py` (new), `services/health-service/db/__init__.py` (new). All future health-service repositories must inherit from `ScopedRepository`.

**Follow-up needed:**
When Feature 1 builds `ReportRepository`, verify it subclasses `ScopedRepository` and add a cross-user scoping test per `04_AGENT_RULES.md §5`.

---

## [2026-08-08] Structural enforcement: get_logger made mandatory export from shared-utils

**Type:** decision

**What changed:**
`packages/shared-utils/__init__.py` now exports only `get_logger` and sets `__all__ = ["get_logger"]`. The docstring explicitly documents that `import logging` / `logging.getLogger()` is wrong for health-data code paths, and explains the correct import pattern.

**Why:**
"Available but optional" safe logger gets bypassed under time pressure. The goal is to make the safe path the *easy* path. With `__all__` set, linters and IDEs surface only `get_logger` as the package's public API. The incorrect alternative (`import logging`) still works — there's no way to block stdlib imports — but it now requires deliberately reaching past the package-provided logger, which is the right friction level.

**Affects:**
`packages/shared-utils/__init__.py`.

**Follow-up needed:**
Add a linting rule (e.g. `ruff` or `flake8-bugbear`) that flags bare `import logging` in service code before Feature 1 is complete — log that addition in DEV_LOG when done.

---

## [2026-08-08] MVP second language: Hindi (hi-IN) chosen

**Type:** decision

**What changed:**
Second language for the MVP is confirmed as **Hindi (hi-IN)**. English (en-IN) remains primary. This closes the open question from the scaffold session before Feature 1 schema/UI decisions are made.

**Why:**

| Language | Native speakers (India) | Lab-report prevalence | i18n tooling maturity | Tesseract support |
|---|---|---|---|---|
| **Hindi (chosen)** | ~600 million (largest in India) | High — many commercial labs print bilingual Hindi/English reports | Excellent (React-i18next, Python gettext) | ✅ `tesseract-ocr-hin` package available |
| Tamil | ~80 million | Moderate | Good | ✅ available |
| Bengali | ~100 million | Moderate | Good | ✅ available |
| Telugu | ~80 million | Moderate | Good | ✅ available |

Hindi is the highest-reach single addition for the India-primary target user from `01_PROJECT_CONTEXT.md §5`. It is also the most likely second language on printed lab reports that users will upload. Tesseract has a maintained Hindi language pack, keeping OCR in-process and consistent with the privacy decision made above.

**What this means concretely for Feature 1:**
1. The `users` table's `locale_preference` column must support at least `en-IN` and `hi-IN` as valid values — use an enum or constrained varchar, not freetext.
2. All user-facing strings (plain-language explanations generated by the AI service) must be produced in the user's locale. At Feature 1 the implementation is: pass `locale` as a parameter to the explanation-generation function; English and Hindi templates created in parallel.
3. String externalisation in the frontend: use a proper i18n library from the start — do not hardcode English strings in JSX.

**Affects:**
`services/auth-service` (users table schema), `services/ai-service` (explanation generation), `apps/web` (i18n setup), `packages/shared-types/schemas.py` (locale enum).

**Follow-up needed:**
- Add `tesseract-ocr-hin` to `ai-service/Dockerfile` (do this now, before Feature 1 build).
- Add `LOCALE = Literal["en-IN", "hi-IN"]` type to `shared-types/schemas.py` before auth schema is written.

---

## [2026-08-08] OCR engine: Tesseract chosen over cloud document-AI APIs

**Type:** decision

**What changed:**
`ai-service` Dockerfile installs `tesseract-ocr` system package. Python layer uses `pytesseract` (Tesseract wrapper) + `pdfplumber` (for native-PDF text extraction without OCR when text layer is present).

**Why — tradeoff analysis:**

Three realistic options were evaluated:

| Option | Accuracy (typed PDFs) | Accuracy (scanned/handwritten) | Cost | Privacy | Offline? |
|---|---|---|---|---|---|
| **Tesseract (chosen)** | Good (pdfplumber handles native-PDF natively; Tesseract only runs on image/scanned fallback) | Fair — adequate for typed lab printouts, poor for handwritten | Free, self-hosted | ✅ Data never leaves the machine | ✅ |
| Google Cloud Document AI / Vision API | Excellent | Excellent | Per-page pricing; adds API dependency and rate-limit risk | ❌ User health data sent to Google | ❌ |
| AWS Textract | Excellent | Very good | Per-page pricing; similar to Cloud Vision | ❌ User health data sent to AWS | ❌ |

**Rationale for choosing Tesseract:**
1. **Privacy is non-negotiable for this product.** Sending patient lab report images to a third-party cloud OCR API is incompatible with the product principles in `01_PROJECT_CONTEXT.md §4` ("User owns their data"). Even if the API doesn't train on submitted data, it creates a data-processor relationship that complicates compliance in India's health-data regulatory environment.
2. **The MVP target document type is typed lab printouts from commercial labs**, not handwritten clinical notes. For typed PDFs with a text layer, `pdfplumber` extracts text directly (no OCR at all), giving near-perfect accuracy. Tesseract is only invoked for image-only PDFs or photos of reports.
3. **Cost and dependency reduction.** Tesseract is free, runs in-process, and adds no per-report pricing or API quota risk at MVP scale.

**Known limitation — what this decision gives up:**
- Handwritten annotations on reports will parse poorly. This is logged as a known issue in `00_PROJECT_STATE.md` and is explicitly acceptable for MVP scope (target user: commercial lab printouts, not handwritten GP notes).
- If the product later moves to clinical settings with handwritten records, revisit this decision — the abstraction in `ai-service/routers/parse.py` (when built) should isolate OCR backend so it can be swapped without touching the rest of the parsing pipeline.

**Affects:**
`services/ai-service/Dockerfile`, `services/ai-service/requirements.txt`, future `services/ai-service/routers/parse.py`.

**Follow-up needed:**
When `parse.py` is built (Feature 1), wrap the OCR call in an abstraction (e.g. `OcrBackend` protocol) so the engine is swappable — don't call pytesseract directly in business logic. Log that pattern in DEV_LOG when implemented.

---

## [2026-08-08] Repo scaffold created per 02_ARCHITECTURE.md

**Type:** decision + feature

**What changed:**
Full monorepo skeleton created under `c:\project\MediValt`:
- Root: `README.md`, `.gitignore`, `.env.example`, `docker-compose.yml`
- `apps/api/` — FastAPI BFF skeleton (main.py, requirements.txt, Dockerfile, README)
- `apps/web/` — placeholder README (framework finalised at Feature 3)
- `services/auth-service/` — FastAPI skeleton (main.py, requirements.txt, Dockerfile, README with API contract)
- `services/health-service/` — FastAPI skeleton (main.py, requirements.txt, Dockerfile, README with API contract and privacy note)
- `services/ai-service/` — FastAPI skeleton (main.py, requirements.txt, Dockerfile with Tesseract, README with safety-layer rule)
- `packages/shared-types/` — `__init__.py`, `schemas.py` stub, README
- `packages/shared-utils/` — `__init__.py`, `logging.py` (redacting logger), README
- `data/knowledge-base/` — README with sourcing/licensing criteria
- `data/datasets/` — README with evaluation requirements reminder
- `infra/migrations/` — README with naming conventions
- `tests/unit/`, `tests/integration/` — gitkeep + README with cross-user scoping rule

**Why:**
Establishes the service boundary shape from day one so future features (biometrics, avatar, family accounts) plug into auth-service or as new services without touching health-service or ai-service. The redacting logger in shared-utils is live from scaffold so it's structurally impossible for a future session to accidentally log raw health values without bypassing the designated logger.

**Affects:**
Whole repo — scaffold only, no business logic.

**Stack confirmed (do not re-litigate without logging reason):**
- Backend: FastAPI (Python 3.11)
- Primary DB: PostgreSQL with pgvector extension (`pgvector/pgvector:pg16` Docker image)
- Vector store: pgvector (inside Postgres) — migrate to dedicated vector DB only if scale demands, log that decision when made
- Auth: JWT-based (python-jose + passlib/bcrypt)
- File storage: local disk in dev (abstracted via env var), S3-compatible in prod
- OCR: Tesseract (pytesseract) + pdfplumber for PDF text extraction
- ML: scikit-learn (anomaly detection), sentence-transformers (embeddings)
- Containerisation: Docker + docker-compose
- Frontend: React or Next.js — deferred decision until Feature 3 sprint

**Follow-up needed:**
- [ ] **Open question — product name:** currently placeholder "MediVault AI". Final name needed before any user-facing strings are shipped.
- [ ] **Open question — second language:** English is confirmed for MVP; regional language TBD (Hindi? Tamil?). Needed before i18n scaffolding at Feature 3.
- [ ] **Open question — anomaly detection dataset:** MIMIC-IV subset vs. synthetic. Decision needed before Feature 2. Must be logged here with full reasoning once made.

---

## [YYYY-MM-DD] Project initialized

**Type:** decision

**What changed:**
Repository scaffolded per `02_ARCHITECTURE.md`. MVP scope locked per `03_MVP_SCOPE.md`.

**Why:**
Establishing a single source of truth before any feature work begins, so all future sessions build against the same context.

**Affects:**
Whole repo.

**Follow-up needed:**
- Confirm final product name (currently placeholder "MediVault AI").
- Confirm the MVP's second language (English is fixed; regional language TBD).
- Confirm dataset source for anomaly detection (MIMIC-IV subset vs. synthetic — see `03_MVP_SCOPE.md` evaluation requirements; this decision needs its own log entry with reasoning once made).

---

<!-- New entries go above this line, newest at top -->

---

## [2026-08-09] Feature 2 Anomaly Detection — Synthetic Evaluation

**Dataset**: 200 synthetic patients, 20% with injected anomalies (Haemoglobin, σ=3.5 spike).

| Metric            | Value   |
|-------------------|---------|
| Precision         | 0.7358 |
| Recall            | 0.9750 |
| F1 Score          | 0.8387 |
| False-Alert Rate  | 0.0875 |
| TP / FP / FN / TN | 39 / 14 / 1 / 146 |

Model: Z-score baseline (|z|>2 → anomaly) + IsolationForest (contamination=0.1) with zscore fallback for <5 data points.
