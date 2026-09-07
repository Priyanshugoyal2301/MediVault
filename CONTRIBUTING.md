# CONTRIBUTING.md — MediVault AI

**Maintainer:** Deepansh Khanna ([`CONTRIBUTORS.md`](CONTRIBUTORS.md))

Thank you for contributing. This guide covers the development workflow, code conventions, database migrations, and the non-negotiable privacy rules. Also see [`docs/DEVELOPER_RULES.md`](docs/DEVELOPER_RULES.md).

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Code Structure & Conventions](#code-structure--conventions)
3. [Privacy Rules (Non-Negotiable)](#privacy-rules-non-negotiable)
4. [Database Migrations (Alembic)](#database-migrations-alembic)
5. [Adding a New Service Endpoint](#adding-a-new-service-endpoint)
6. [Running Tests](#running-tests)
7. [Logging](#logging)
8. [Pre-commit Hooks](#pre-commit-hooks)
9. [Branching & PRs](#branching--prs)

---

## Development Setup

See [README.md](README.md) for the full local setup. Quick start:

```bash
git clone https://github.com/Priyanshugoyal2301/MediVault.git
cd MediVault
python -m venv .venv && source .venv/bin/activate   # macOS/Linux
# OR: .venv\Scripts\activate                         # Windows
pip install -r requirements-dev.txt
cp .env.example .env  # fill in required values
docker-compose up -d postgres
alembic -c infra/migrations/alembic.ini upgrade head
```

Start services with `python scripts/run_service.py …` as described in [README.md](README.md).

---

## Code Structure & Conventions

### Service layout (each service is identical)

```
services/<service-name>/
  main.py              # FastAPI app + router registration
  core/
    config.py          # pydantic-settings Settings class
  db/
    models.py          # SQLAlchemy ORM models
    session.py         # async engine + get_db dependency
    base_repository.py # ScopedRepository base class (DO NOT remove)
    repositories/
      <name>_repository.py
  routers/
    <feature>.py       # APIRouter + Pydantic schemas + endpoints
  requirements.txt
```

### Import rules

| ✅ Always do this | ❌ Never do this |
|---|---|
| `from packages.shared_utils import get_logger` | `import logging` |
| `owner_id` from JWT only | `owner_id` from request body |
| Subclass `ScopedRepository` | Query a health table without `owner_id` |

### Naming

- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/variables:** `snake_case`
- **Router prefixes:** `/kebab-case` (e.g., `/reports`, `/anomaly`)

---

## Privacy Rules (Non-Negotiable)

These rules exist because we process personal health data. Violations will be rejected in code review.

### Rule 1 — Owner-scoped queries

Every repository that touches health data **must** subclass `ScopedRepository`. Never add a method that accepts `owner_id=None`.

```python
# ✅ Correct
class MyRepository(ScopedRepository[MyModel]):
    model = MyModel

    async def my_method(self, owner_id: uuid.UUID, ...) -> ...:
        ...
```

### Rule 2 — No diagnoses in AI output

AI-generated text (explanations, summaries) must NEVER:
- Say "you have [condition]"
- Say "you are diagnosed with"
- Use words like "critical", "dangerous", "alarming" in reference to a reading

It MUST:
- Say "your readings show a [rising/falling/stable] pattern"
- Recommend consulting a doctor, never prescribe

Tone rules are enforced by test suite (`test_anomaly.py`, `test_explainer.py`).

### Rule 3 — Redacting logger

```python
# In every module that handles health data:
from packages.shared_utils import get_logger
logger = get_logger(__name__)
```

Never `import logging`. The redacting logger strips health-field names (test_name, value_numeric, etc.) before any log record is emitted.

### Rule 4 — Local OCR only

Use Tesseract (self-hosted). Do not add cloud OCR API calls (Google Vision, AWS Textract, etc.) without a DEV_LOG entry explaining the privacy rationale.

---

## Database Migrations (Alembic)

Migrations live in `infra/migrations/`.

```bash
cd infra/migrations

# Create a new migration (auto-generate from model changes)
alembic revision --autogenerate -m "describe_your_change"

# Apply all pending migrations
alembic upgrade head

# Downgrade one step
alembic downgrade -1

# Check current state
alembic current
```

**Rules:**
- Every new table that stores health data **must** have `owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE`.
- Never rename a column in a migration without a DEV_LOG entry.
- Migration files are append-only — never edit an existing migration that has been applied.

---

## Adding a New Service Endpoint

1. **Model** (if new table): add to `db/models.py`, create a migration.
2. **Repository**: create `db/repositories/<name>_repository.py`, subclass `ScopedRepository`.
3. **Router**: create `routers/<name>.py`. Get `owner_id` from `X-User-ID` header only.
4. **Register**: add `app.include_router(...)` in `main.py`.
5. **Tests**: add `tests/unit/<service>/test_<name>.py` covering:
   - Happy path
   - Missing/invalid `X-User-ID` → 401
   - Cross-user scoping isolation

---

## Running Tests

```bash
# From repo root
$env:PYTHONPATH="."; python -m pytest -v    # Windows
PYTHONPATH="." python -m pytest -v          # macOS/Linux

# Specific test file
python -m pytest tests/unit/ai-service/test_anomaly.py -v
```

All new code must ship with tests. CI will reject PRs where new paths are untested.

---

## Logging

```python
from packages.shared_utils import get_logger
logger = get_logger(__name__)

# Use structured arguments, not f-strings, so redaction can operate on fields
logger.info("Report uploaded: report_id=%s owner_id=%s", report_id, owner_id)
```

Do NOT log `value_numeric`, `test_name`, `explanation_en/hi` or any extracted health values directly. These are automatically redacted by the logger, but don't rely on that as your only protection.

---

## Pre-commit Hooks

Install once:

```bash
pip install pre-commit
pre-commit install
```

Hooks configured in `.pre-commit-config.yaml`:
- **ruff** — linting and import sorting
- **bare-import-logging check** — rejects `import logging` in service code

To run manually:

```bash
pre-commit run --all-files
```

---

## Branching & PRs

| Branch | Purpose |
|--------|---------|
| `main` | Stable, always green tests |
| `feature/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation only |

**PR checklist:**
- [ ] Tests pass (`pytest`)
- [ ] No bare `import logging` (pre-commit hook)
- [ ] New health-data tables have `owner_id NOT NULL`
- [ ] AI output text passes tone rules (no diagnoses)
- [ ] README / docs updated if user-facing behavior changed
- [ ] ML flags left at default off unless intentionally enabling and evaluating
