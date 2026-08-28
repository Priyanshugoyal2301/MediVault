# Documentation Consistency Report — Phase 10

**Audit date:** 2026-08-28

---

## Documents reviewed

| Document | Consistency |
|----------|-------------|
| `00_PROJECT_STATE.md` | **PARTIAL** — header stale; XGBoost note inaccurate |
| `README.md` | **GOOD** — hackathon prototype |
| `docs/ROADMAP.md` | **GOOD** — Phases 0–9 Done |
| `docs/ML_ARCHITECTURE.md` | **GOOD** |
| `docs/MODEL_REGISTRY.md` | **GOOD** — flags off |
| `known-limitations.md` | **GOOD** |
| `BIBLE.md` | **STALE** — audit date 2026-08-10 |
| `docs/PRESENTATION_CLAIMS.md` | **GOOD** — conservative |
| Research site `site.js` | **GOOD** — honest limitations |

---

## Key gaps

### `00_PROJECT_STATE.md`

- Header references Phase 1 only; Phases 2–9 complete in code.
- Says "XGBoost not used" but Phases 4–6 use XGBoost when flags enabled.
- "Integration test suite still empty" — clarify means E2E HTTP, not phase tests.

### Docs vs uncommitted code

Extensive `docs/` describes `models/` and adapters not yet on `origin/main`. Alignment occurs after commit.

---

## Claims vs implementation

| Claim | Reality | Status |
|-------|---------|--------|
| BM25 default | `MEDIVAULT_FAST_KB=1` | Accurate |
| pgvector not live | In-memory KB | Accurate |
| ML flags off | `.env.example` all `=0` | Accurate |
| Statistical anomaly default | `USE_ANOMALY_MODEL=0` | Accurate |

---

## Overclaiming risk: **LOW**

No dangerous clinical or production overclaims found. Update stale headers before release tag.

---

## Pre-release doc updates

| Priority | File | Action |
|----------|------|--------|
| P1 | `00_PROJECT_STATE.md` | Sync Phases 2–9; fix XGBoost note |
| P1 | `BIBLE.md` | Bump audit date |
| P2 | Root benchmark duplicates | Consolidate with `docs/` |
