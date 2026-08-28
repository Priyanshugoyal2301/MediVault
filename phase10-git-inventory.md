# Phase 10 — Git Inventory

**Audit date:** 2026-08-28  
**Auditor role:** Release baseline (read-only; no commits made)  
**Repository root:** `C:/Deepansh/Deepansh/Dev/College/ML/MediVault`

---

## 1. Repository identity

| Field | Value |
|-------|-------|
| Current branch | `main` |
| Remote tracking | `origin/main` (up to date) |
| Remote URL | `https://github.com/Priyanshugoyal2301/MediVault.git` |
| Last commit | `297d22c` — `feat(f3): RAG Q&A engine, deterministic safety layer, and React frontend` |
| Commit history depth | 3 commits total |
| Tracked files (committed) | 138 |
| Modified tracked files | 52 |
| Untracked paths (git status groups) | 108 top-level entries |
| Untracked trackable files (`git ls-files --others --exclude-standard`) | 384 files (~5.07 MB) |
| Staged files | **0** |
| Deleted tracked files | **0** |
| Merge conflicts | **None detected** |

---

## 2. Git commands executed (read-only)

```text
git status
git status --porcelain=v1
git diff --stat          → 52 files, +2754 / -1565 lines
git diff --cached --stat → empty (nothing staged)
git log --oneline --decorate -20
git branch --show-current
git remote -v
git ls-files             → 138 tracked
git check-ignore         → applied to models/, datasets/, dist/, node_modules/
git ls-files --others --exclude-standard → 384 trackable untracked files
```

---

## 3. Modified tracked files (52)

### Configuration & root (4)

| Path | Category | Approx. delta | Recommended action |
|------|----------|---------------|-------------------|
| `.env.example` | H — Configuration | +123 lines | COMMIT |
| `.gitignore` | H — Configuration | +8 lines | COMMIT |
| `00_PROJECT_STATE.md` | D — Documentation | major rewrite | COMMIT (update header for Phases 2–9 before release) |
| `README.md` | D — Documentation | +97 lines | COMMIT |

### Apps — BFF & web (14)

| Path | Category | Recommended action |
|------|----------|-------------------|
| `apps/api/Dockerfile` | A — Core app | COMMIT |
| `apps/api/README.md` | D — Documentation | COMMIT |
| `apps/api/main.py` | A — Core app | COMMIT |
| `apps/api/requirements.txt` | H — Configuration | COMMIT |
| `apps/web/src/App.jsx` | A — Core app | COMMIT |
| `apps/web/src/components/Sidebar.jsx` | A — Core app | COMMIT |
| `apps/web/src/views/*.jsx` (5 files) | A — Core app | COMMIT |
| `apps/web/vite.config.js` | H — Configuration | COMMIT |

### Services (22)

| Area | Files | Category | Recommended action |
|------|-------|----------|-------------------|
| `services/auth-service/` | 4 | A | COMMIT |
| `services/health-service/` | 8 | A | COMMIT |
| `services/ai-service/` | 10 | A + B | COMMIT |

### Data & infra (6)

| Path | Category | Recommended action |
|------|----------|-------------------|
| `data/datasets/evaluate_rag.py` | B — ML source | COMMIT |
| `data/datasets/generate_synthetic_anomaly_data.py` | B — ML source | COMMIT |
| `data/knowledge-base/*.txt` (2) | E — Datasets (KB text) | COMMIT |
| `docker-compose.yml` | H — Configuration | COMMIT |
| `docs/02_ARCHITECTURE.md` | D — Documentation | COMMIT |
| `docs/DEV_LOG.md` | D — Documentation | COMMIT |

### Tests (3)

| Path | Category | Recommended action |
|------|----------|-------------------|
| `tests/unit/ai-service/test_anomaly.py` | C — Tests | COMMIT |
| `tests/unit/ai-service/test_rag.py` | C — Tests | COMMIT |
| `tests/unit/health-service/test_qa.py` | C — Tests | COMMIT |

---

## 4. Untracked inventory by category

### A. Core application source — COMMIT

| Path | Files | Size (excl. node_modules/dist) | Notes |
|------|-------|----------------------------------|-------|
| `apps/api/core/` | 3 | ~4 KB | JWT config + auth helpers |
| `apps/api/routers/` | 2 | ~6 KB | BFF proxy router |
| `apps/web/src/api.js` | 1 | ~3 KB | Frontend API client |
| `services/ai-service/adapters/` | ~12 | ~40 KB | ML adapter layer |
| `services/ai-service/core/` | ~5 | ~15 KB | Registry, flags |
| `services/ai-service/rag/bm25.py`, `bootstrap.py`, `intent.py` | 3 | ~12 KB | Plan B RAG |
| `infra/migrations/versions/004_add_explanation_columns.py` | 1 | ~2 KB | DB migration |

### B. ML source code — COMMIT

| Path | Trackable files | Trackable size | Ignored artifacts |
|------|-----------------|----------------|-------------------|
| `models/` | 148 | ~0.45 MB | 126 files (~19.86 MB) via `models/**/artifacts/` |
| `packages/ml-eval/` | ~8 | ~30 KB | — |
| `packages/ml-interfaces/` | ~9 | ~50 KB | — |
| `data/datasets/plan_c/` | ~8 | ~80 KB | Plan C lab scripts |

### C. Tests — COMMIT

| Path | Files | Notes |
|------|-------|-------|
| `tests/phase1/` | 4 | Phase 1 OCR |
| `tests/phase1a/` | 3 | Phase 1A hardening |
| `tests/phase2/` – `tests/phase9/` | 24 | ML phase suites |
| `tests/unit/ai-service/test_ml_infra.py` | 1 | Registry tests |
| `tests/unit/ai-service/test_plan_c.py` | 1 | Plan C tests |

### D. Documentation — COMMIT

| Path | Files | Size |
|------|-------|------|
| `docs/` (new) | 70 | ~180 KB |
| `BIBLE.md` | 1 | ~70 KB |
| `validation/` | 10 | ~50 KB |
| Root summaries | 21 | ~100 KB |
| `known-limitations.md`, `deployment-checklist.md`, etc. | — | — |

### E. Datasets — COMMIT (with governance review)

| Path | Trackable | Ignored | Total on disk |
|------|-----------|---------|---------------|
| `datasets/` | 37 files (~3.5 MB) | 8 `*_latest.json` eval outputs | ~3.94 MB |

**Trackable synthetic JSONL (redistributable):**  
`anomaly_detection/`, `forecasting/`, `health_score/`, `risk_prediction/`, `test_normalization/`, `retrieval/eval_benchmark.jsonl`

**Ignored by `.gitignore`:** `datasets/evaluation/*_latest.json` (regenerated by evaluate scripts)

**Platform eval JSON (not `*_latest`):** `platform_benchmark_complete.json`, `platform_e2e_validation.json`, `platform_reproducibility_audit.json`, `ocr_phase1a_bench.json` — COMMIT as benchmark snapshots

### F. Model artifacts — DO NOT COMMIT

| Path | Size | Status |
|------|------|--------|
| `models/**/artifacts/**` | ~19.86 MB | Correctly ignored by `.gitignore:63` |
| Largest single file | `models/normalizer/artifacts/matrix.npy` — **14.98 MB** | IGNORED |

Regenerate via `models/*/train.py` or document download in `docs/MODEL_ARTIFACT_GOVERNANCE.md`.

### G. Generated artifacts — DO NOT COMMIT

| Path | Size | Status |
|------|------|--------|
| `apps/research-site/node_modules/` | 73.56 MB | Ignored (`node_modules/`) |
| `apps/research-site/dist/` | ~0.5 MB | Ignored (`dist/`) |
| `datasets/evaluation/*_latest.json` | ~35 KB total | Ignored |
| `.pytest_cache/`, `__pycache__/` | varies | Ignored |

### H. Configuration — COMMIT

Already covered: `.env.example`, `.gitignore`, `docker-compose.yml`, service Dockerfiles, `apps/research-site/vercel.json`

### I. Secrets / sensitive — NO ISSUES FOUND

| Check | Result |
|-------|--------|
| `.env` present on disk | **No** (`Test-Path .env` → False) |
| `.env` tracked in git | **No** |
| Tracked `*.env`, `*.pem`, `*.key` | **None** |
| Real API keys in source | **None found** (only placeholders: `CHANGE_ME`, demo `password123`) |

### J. Unclear / requires human review

| Path | Issue | Recommended action |
|------|-------|-------------------|
| `benchmark_*.md` (repo root) | Duplicate of `docs/benchmark_*.md` | REVIEW — dedupe or symlink policy |
| `phase*-summary.md` (repo root) | Overlap with `docs/` and `validation/` | REVIEW — keep one canonical location |
| `data/datasets/plan_c/results_latest.json` | Generated eval output | REVIEW — likely IGNORE (add pattern) |
| `scripts/demo_preflight.ps1` | Unicode em-dash causes PowerShell parse error on Windows | REVIEW — fix encoding before relying on script |
| `00_PROJECT_STATE.md` header | Says "Phase 1" only; Phases 2–9 complete in code | REVIEW — update before release tag |

---

## 5. Diff magnitude summary

```
52 modified tracked files
  +2,754 insertions
  -1,565 deletions
  Net: ~1,189 lines added

384 new trackable files (~5.07 MB)
  models source:     148 files (~0.45 MB)
  datasets synthetic: 37 files (~3.5 MB)
  docs + validation:  ~80 files (~0.25 MB)
  apps + services:    ~45 files (~0.15 MB)
  tests:              31 files (~0.31 MB)
```

---

## 6. Working tree safety assessment

| Risk | Level | Notes |
|------|-------|-------|
| Secrets in working tree | **Low** | No `.env`; placeholders only |
| PHI in datasets | **Low** | Synthetic JSONL + curated KB text |
| Large binaries accidentally staged | **Low** | Artifacts gitignored; only 1 file >10 MB and it is ignored |
| Lost work if hard reset | **HIGH** | ~384 untracked files + 52 modified files not committed |
| Remote divergence | **Low** | Branch matches `origin/main`; all delta is local |

**No destructive git operations were performed during this audit.**
