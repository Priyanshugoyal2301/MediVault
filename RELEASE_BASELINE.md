# RELEASE_BASELINE.md — Phase 10 Repository Consolidation

**Audit date:** 2026-08-28  
**Phase:** 10 — Audit & preparation (no commits made)  
**Decision:** **READY WITH OBSERVATIONS**

---

## Executive Summary

MediVault AI has **3 commits** on `main` (last: Feature 3 RAG + frontend). Locally, **52 tracked files are modified** and **384 new trackable files** (~5.07 MB) sit uncommitted, representing the complete ML migration (Phases 1–9), BFF hardening, frontend API wiring, documentation, synthetic datasets, and a research site.

**No secrets, PHI, or files >50 MB were found.** Model artifacts (~20 MB) are correctly gitignored. The repository **can proceed to human-approved staging and commit** after consciously accepting: stale `00_PROJECT_STATE.md` header, auth test dependency gap in non-venv environments, demo preflight script encoding issue on Windows, and duplicate root-level benchmark docs.

**No commits, pushes, deletes, or history rewrites were performed during this audit.**

---

## Current Git State

| Field | Value |
|-------|-------|
| Branch | `main` (up to date with `origin/main`) |
| Remote | `https://github.com/Priyanshugoyal2301/MediVault.git` |
| HEAD | `297d22c` feat(f3): RAG Q&A engine, deterministic safety layer, and React frontend |
| Tracked files | 138 |
| Modified (unstaged) | 52 files (+2754 / -1565 lines) |
| Untracked (trackable) | 384 files (~5.07 MB) |
| Staged | 0 |
| `.env` on disk | **Absent** (good) |

Detail: [`phase10-git-inventory.md`](phase10-git-inventory.md)

---

## Repository Inventory

| Category | Trackable items | Recommended action |
|----------|-----------------|-------------------|
| A. Core app (`apps/`, `services/`) | ~70 modified + new | **COMMIT** |
| B. ML source (`models/`, `packages/`) | 148 source files (~0.45 MB) | **COMMIT** |
| C. Tests (`tests/phase*`, unit updates) | 31+ files | **COMMIT** |
| D. Documentation (`docs/`, `BIBLE.md`, validation) | ~100 files | **COMMIT** |
| E. Datasets (synthetic JSONL) | 37 files (~3.5 MB) | **COMMIT** |
| F. Model artifacts | 126 files (~19.86 MB) | **DO NOT COMMIT** (ignored) |
| G. Generated (`dist/`, `node_modules/`, `*_latest.json`) | ~74 MB | **DO NOT COMMIT** (ignored) |
| H. Configuration (`.env.example`, compose, Dockerfiles) | modified | **COMMIT** |
| I. Secrets | none found | — |
| J. Review needed | root benchmark dupes, preflight script | **REVIEW** |

---

## Files Safe to Commit

### Modified tracked (52)

All 52 modified tracked files are **source, config, or documentation** with no secrets. Safe to commit after human review of diffs.

### New trackable (384) — commit these groups

- `apps/api/core/`, `apps/api/routers/`, `apps/web/src/api.js`
- `apps/research-site/` **source only** (not `dist/`, not `node_modules/`)
- `models/` source (148 files; artifacts auto-excluded)
- `datasets/` synthetic JSONL, README, LICENSING, platform eval snapshots
- `packages/ml-eval/`, `packages/ml-interfaces/`
- `services/ai-service/adapters/`, `core/`, `rag/bm25.py`, `bootstrap.py`, `intent.py`
- `tests/phase1` through `tests/phase9`, new unit tests
- `infra/migrations/versions/004_add_explanation_columns.py`
- `docs/**`, `validation/**`, `BIBLE.md`, `known-limitations.md`
- `scripts/demo_preflight.ps1`, `scripts/smoke_demo.ps1`
- `data/datasets/plan_c/` (except generated `results_latest.json` — review)

**Estimated committed payload:** ~5.5 MB (source + synthetic data; no artifacts)

---

## Files That Must NOT Be Committed

| Path pattern | Reason |
|--------------|--------|
| `.env`, `*.env` | Secrets |
| `node_modules/` | Dependencies (73 MB research-site alone) |
| `dist/`, `build/` | Build output |
| `models/**/artifacts/` | Regenerable binaries (~20 MB) |
| `datasets/evaluation/*_latest.json` | Regenerated metrics |
| `__pycache__/`, `.pytest_cache/` | Cache |
| `.venv/`, `venv/` | Virtual environment |
| Hugging Face / FAISS caches | External downloads |
| MIMIC, NHANES, eICU raw data | Licensed / credentialed |

---

## Files Requiring Human Review

| Item | Question | Recommendation |
|------|----------|----------------|
| `benchmark_*.md` at repo root | Duplicate of `docs/benchmark_*.md`? | Keep `docs/` canonical; drop or symlink root copies |
| `phase*-summary.md` at root | Overlap with validation docs? | Consolidate |
| `data/datasets/plan_c/results_latest.json` | Generated? | Add to `.gitignore` |
| `scripts/demo_preflight.ps1` | Unicode em-dash breaks Windows PS | Fix encoding before release |
| `00_PROJECT_STATE.md` | Stale Phase 1 header | Update before tagging |
| `datasets/evaluation/platform_*.json` | Snapshot vs regenerate? | Commit as audit trail (recommended) |

---

## Large File Strategy

| Threshold | Count | Action |
|-----------|-------|--------|
| >10 MB | 1 (`matrix.npy` 14.98 MB) | **Already ignored** — regenerate via `train.py` |
| >50 MB | 0 | — |
| >100 MB | 0 | — |

**Strategy:** No Git LFS required for current tree. Artifacts excluded by policy. Synthetic JSONL (~3.5 MB total) commits normally. If `matrix.npy` must ship pre-trained, consider LFS or CI artifact — not recommended for hackathon baseline.

Detail: [`docs/MODEL_ARTIFACT_GOVERNANCE.md`](docs/MODEL_ARTIFACT_GOVERNANCE.md)

---

## Dataset Strategy

- **Commit:** All synthetic JSONL, LOINC subset, KB text, LICENSING.md, platform benchmark JSON
- **Ignore:** `*_latest.json`, CSV/parquet/pkl/zip patterns
- **Never commit:** MIMIC, NHANES, eICU, DocLayNet, real PHI

Detail: [`docs/DATASET_GOVERNANCE.md`](docs/DATASET_GOVERNANCE.md)

---

## Model Artifact Strategy

- **Commit:** Source code, configs, model cards, requirements (~0.45 MB)
- **Ignore:** All `models/**/artifacts/` (~19.86 MB)
- **Demo:** No artifacts required (all ML flags default off)
- **ML tests:** Pass with flags off; train scripts available if flags enabled

Detail: [`docs/MODEL_ARTIFACT_GOVERNANCE.md`](docs/MODEL_ARTIFACT_GOVERNANCE.md)

---

## Secret and Sensitive Data Findings

| Check | Result |
|-------|--------|
| `.env` present | **No** |
| `.env` tracked | **No** |
| API keys in source | **None** (placeholders only: `CHANGE_ME`, demo `password123`) |
| PHI in datasets | **None identified** (synthetic only) |
| Tracked credentials | **None** |
| HIGH PRIORITY issues | **None** |

`.env.example` contains `INTERNAL_SERVICE_KEY=dev-internal-key-change-me` — acceptable as template; operators must rotate for shared environments.

---

## .gitignore Recommendations

### SAFE TO ADD NOW

```gitignore
# Plan C generated results
data/datasets/plan_c/results_latest.json

# Hugging Face / ML caches (if created in-repo)
.cache/
.huggingface/

# Research site local Vercel
apps/research-site/.vercel
```

### REQUIRES REVIEW

```gitignore
# Only if team decides NOT to commit platform benchmark snapshots
# datasets/evaluation/platform_*.json
```

### DO NOT ADD

```gitignore
# Do NOT ignore — required for reproducibility:
# datasets/**/*.jsonl
# models/**/*.py
# docs/
```

Current `.gitignore` is **adequate** for release. Minor additions above are optional improvements.

---

## Reproducibility Status

| Criterion | Status |
|-----------|--------|
| README instructions | Good |
| `.env.example` complete | Yes |
| Migrations through 004 | **004 uncommitted — must commit** |
| Synthetic datasets in repo | Yes (when committed) |
| Model artifacts | Regenerate via train scripts |
| Demo without ML flags | Achievable |
| Aggregated dev requirements | **Missing** |

Detail: [`reproducibility-gap-analysis.md`](reproducibility-gap-analysis.md)

---

## Test Baseline

| Suite | Result |
|-------|--------|
| ML Phases 1–3 (59 tests) | **PASS** |
| ML Phases 4–9 (75 tests) | **PASS** |
| Unit tests (ai + health) | **PASS** (137 total unit; 8 auth fail on missing `jose`) |
| Demo preflight | **NOT RUN** — no `.env`, services down, PS encoding issue |
| Smoke demo | **NOT RUN** |

Detail: [`phase10-baseline-validation.md`](phase10-baseline-validation.md)

---

## Documentation Consistency

- Product claims are **honest** (prototype, non-diagnostic, synthetic eval).
- `00_PROJECT_STATE.md` and `BIBLE.md` need header sync for Phases 2–9.
- Research site aligns with `docs/PRESENTATION_CLAIMS.md`.

Detail: [`documentation-consistency-report.md`](documentation-consistency-report.md)

---

## Research Site Status

| Field | Value |
|-------|-------|
| Path | `apps/research-site/` |
| Purpose | Faculty review, competitions, portfolio (not product demo) |
| Stack | Vite + React 18, framer-motion, react-router |
| Self-contained | Yes — separate `package.json` |
| Build | `npm run build` → `dist/` (gitignored) |
| Deploy | `vercel.json` configured for static export |
| Claims accuracy | **Good** — prototype, synthetic limits, non-diagnostic, no HIPAA |
| Commit recommendation | **COMMIT source**; exclude `dist/`, `node_modules/` |
| `node_modules` on disk | 73.56 MB (ignored) |

---

## Proposed Commit Plan

**Do not execute without explicit approval.**

### Commit 1 — Infrastructure & configuration

**Message:** `chore(infra): env template, gitignore, docker-compose, migration 004`

**Files:** `.env.example`, `.gitignore`, `docker-compose.yml`, `infra/migrations/versions/004_add_explanation_columns.py`

**Risk:** Low | **Revertible:** Yes

---

### Commit 2 — BFF gateway & service hardening

**Message:** `feat(api): JWT BFF with auth proxy and trusted X-User-ID injection`

**Files:** `apps/api/**`, `services/auth-service/**`, `services/health-service/core/config.py`, Dockerfiles

**Risk:** Medium (auth path) | **Revertible:** Yes

---

### Commit 3 — Health & AI service integration

**Message:** `feat(services): demo seed, timeline, Q&A proxy, ML registry adapters`

**Files:** `services/health-service/**`, `services/ai-service/**`, `packages/ml-interfaces/`, `packages/ml-eval/`

**Risk:** Medium | **Revertible:** Yes | **Depends on:** Commit 2

---

### Commit 4 — Frontend live API wiring

**Message:** `feat(web): connect dashboard, upload, timeline, and Q&A to BFF APIs`

**Files:** `apps/web/src/**`, `apps/web/vite.config.js`

**Risk:** Low | **Revertible:** Yes | **Depends on:** Commits 2–3

---

### Commit 5 — ML packages Phases 1–3

**Message:** `feat(ml): OCR adapter, test normalizer, semantic retrieval (flags default off)`

**Files:** `models/ocr/`, `models/normalizer/`, `models/retrieval/`, `tests/phase1/`, `tests/phase1a/`, `tests/phase2/`, `tests/phase3/`

**Risk:** Low (flags off) | **Revertible:** Yes

---

### Commit 6 — ML packages Phases 4–6

**Message:** `feat(ml): risk prediction, biomarker forecasting, health score + SHAP`

**Files:** `models/risk_prediction/`, `models/forecasting/`, `models/health_score/`, `models/explainability/`, `tests/phase4/`–`phase6/`

**Risk:** Low | **Revertible:** Yes

---

### Commit 7 — ML packages Phases 7–9

**Message:** `feat(ml): anomaly detection, image quality gate, platform audit suite`

**Files:** `models/anomaly_detection/`, `models/image_quality/`, `models/platform/`, `tests/phase7/`–`phase9/`

**Risk:** Low | **Revertible:** Yes

---

### Commit 8 — Datasets & evaluation data

**Message:** `data: synthetic ML datasets, licensing stubs, platform benchmark snapshots`

**Files:** `datasets/**` (excluding ignored), `data/datasets/plan_c/`, `data/datasets/*.py`

**Risk:** Low (synthetic only) | **Revertible:** Yes

---

### Commit 9 — Tests & validation

**Message:** `test: phase suites, unit test updates, validation reports`

**Files:** `tests/**`, `validation/**`, updated unit tests

**Risk:** Low | **Revertible:** Yes

---

### Commit 10 — Documentation & project state

**Message:** `docs: ML architecture, model registry, guides, BIBLE, and phase summaries`

**Files:** `docs/**`, `BIBLE.md`, `00_PROJECT_STATE.md`, `README.md`, `known-limitations.md`, root checklists

**Risk:** Low | **Revertible:** Yes | **Note:** Update `00_PROJECT_STATE.md` header in this commit

---

### Commit 11 — Research site & demo scripts

**Message:** `feat(research-site): static research portal and demo preflight scripts`

**Files:** `apps/research-site/` (source only), `scripts/demo_preflight.ps1`, `scripts/smoke_demo.ps1`

**Risk:** Low | **Revertible:** Yes

---

## Risks Before Commit

| Risk | Severity | Mitigation |
|------|----------|------------|
| Large uncommitted work lost | **High** if hard reset | Commit in planned batches; backup branch first |
| `00_PROJECT_STATE.md` misleading | Medium | Update in Commit 10 |
| Auth tests fail in bare Python | Medium | Document venv + requirements-dev |
| Duplicate benchmark docs confuse | Low | Consolidate in Commit 10 |
| Accidental artifact staging | Low | Verify `git add` excludes `models/**/artifacts/` |
| Public repo exposes synthetic-only data | Low | LICENSING.md present |

---

## Recommended Next Actions

1. **Review this report** and approve commit plan (or revise grouping).
2. **Create backup branch:** `git branch backup/pre-phase10-consolidation` (read-only snapshot).
3. **Update `00_PROJECT_STATE.md`** to reflect Phases 1–9 before doc commit.
4. **Fix `demo_preflight.ps1`** Unicode dashes (optional but recommended).
5. **Add `requirements-dev.txt`** aggregating service deps.
6. **Execute staged commits** per approved plan — one commit at a time with `git status` verification.
7. **After all commits:** run full test suite in venv; tag `v0.4.0-ml-platform` or similar.
8. **Do not push** until explicit approval.

---

## Repository Health Score

| Dimension | Score (1–5) | Notes |
|-----------|-------------|-------|
| Code completeness | **5** | Full ML platform locally |
| Git hygiene | **2** | 384 uncommitted files on 3-commit history |
| Secret safety | **5** | Clean audit |
| Large file hygiene | **5** | Artifacts ignored |
| Test coverage (ML phases) | **4** | 134 phase tests pass |
| Test coverage (E2E) | **2** | No integration suite |
| Documentation | **4** | Extensive; minor staleness |
| Reproducibility | **3** | Needs venv discipline + migration 004 |
| Honest claims | **5** | Non-diagnostic throughout |

**Overall health: 3.9 / 5 — READY WITH OBSERVATIONS**

---

## Phase 10 Decision

# READY WITH OBSERVATIONS

The repository can safely proceed to human-approved staging and commit. Specific issues to consciously accept:

1. Auth unit tests require proper venv (`python-jose` not in audit environment).
2. `00_PROJECT_STATE.md` header is stale until updated in doc commit.
3. Demo preflight script has Windows PowerShell encoding issue.
4. ~3.5 MB synthetic datasets will enter git (acceptable; documented).
5. Model artifacts remain local-only (correct; train to regenerate).

**No staging, commits, or pushes were performed. Awaiting explicit approval.**

---

## Related deliverables

| File | Purpose |
|------|---------|
| [`phase10-git-inventory.md`](phase10-git-inventory.md) | Full git state |
| [`phase10-baseline-validation.md`](phase10-baseline-validation.md) | Test results |
| [`documentation-consistency-report.md`](documentation-consistency-report.md) | Doc audit |
| [`reproducibility-gap-analysis.md`](reproducibility-gap-analysis.md) | Setup gaps |
| [`docs/DATASET_GOVERNANCE.md`](docs/DATASET_GOVERNANCE.md) | Dataset policy |
| [`docs/MODEL_ARTIFACT_GOVERNANCE.md`](docs/MODEL_ARTIFACT_GOVERNANCE.md) | Artifact policy |
