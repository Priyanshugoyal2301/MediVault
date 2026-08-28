# Phase 10.1 — Commit Audit

**Date:** 2026-08-28  
**Status:** CONSOLIDATION COMPLETE WITH OBSERVATIONS  
**Branch:** `main` (11 commits ahead of `origin/main`)  
**No push performed.**

---

## Commit table

| # | Hash | Commit message | Purpose | Files | Validation | Risk notes |
|---|------|----------------|---------|-------|------------|------------|
| 1 | `d034c66` | chore(infra): consolidate configuration and schema baseline | `.env.example`, `.gitignore`, `docker-compose`, migration 004, `requirements-dev.txt` | 5 | Config review PASS | Low |
| 2 | `88c2c41` | feat(bff): add consolidated API gateway and proxy routing | BFF core/auth/proxy + auth-service hardening | 13 | Staged review PASS | Medium (JWT boundary) |
| 3 | `e00d571` | feat(services): integrate health and AI service enhancements | Health/AI services, ML adapters, registry, packages | 56 | Staged review PASS | Medium |
| 4 | `e61e3df` | feat(web): connect frontend to live backend APIs | React views + `api.js` client | 9 | Staged review PASS | Low |
| 5 | `a4ef45c` | feat(ml): add document understanding and semantic retrieval pipeline | OCR, normalizer, retrieval models | 50 | Phase 1–3: **59 PASS** | Low (flags off) |
| 6 | `db5aa43` | feat(ml): add predictive health modeling and explainability | Risk, forecast, health score, explainability | 51 | Phase 4–6 in suite | Low |
| 7 | `84bef3c` | feat(ml): add anomaly detection quality assessment and platform hardening | Anomaly, image quality, platform | 47 | Phase 7–9: **75 PASS** | Low |
| 8 | `811acee` | data: add governed synthetic datasets and dataset manifests | Synthetic JSONL, LICENSING, Plan C scripts | 48 | No artifacts staged | Low |
| 9 | `af1f0d4` | test: add ML phase validation and regression coverage | Phase tests, validation reports, unit updates | 38 | Phase suites PASS | Low |
| 10 | `8225bfa` | docs: consolidate ML architecture research and project documentation | Full docs, BIBLE, governance, Phase 10 reports | 97 | Consistency review PASS | Low |
| 11 | `75fac9a` | feat(research): add project research site and demo tooling | Research site source, demo scripts | 24 | No dist/node_modules staged | Low |

**Total:** 438 files changed, +45,313 / −1,564 lines vs `origin/main`

---

## Backup branch

| Branch | Points to | Notes |
|--------|-----------|-------|
| `backup/pre-phase10-consolidation` | `297d22c` | Pre-consolidation snapshot; not pushed |

---

## Files intentionally excluded

| Pattern | On disk | In git |
|---------|---------|--------|
| `models/**/artifacts/` | Yes (~19.86 MB) | **No** |
| `apps/research-site/node_modules/` | Yes (~73 MB) | **No** |
| `apps/research-site/dist/` | Yes | **No** |
| `datasets/evaluation/*_latest.json` | Some | **No** |
| `data/datasets/plan_c/results_latest.json` | If generated | **No** (gitignored) |
| `.env` | No | **No** |
| `__pycache__/`, `.pytest_cache/` | Yes | **No** |

---

## Large file verification

| File | Size | Committed? |
|------|------|------------|
| `models/normalizer/artifacts/matrix.npy` | 14.98 MB | **No** (gitignored) |
| Any file >50 MB | — | **None** |
| Largest committed file | ~884 KB (`datasets/forecasting/train_synthetic.jsonl`) | Yes (synthetic) |

`git ls-files` scan for `artifacts/`, `node_modules`, `.env`, `matrix.npy`: **clean**

---

## Secret scan result

| Check | Result |
|-------|--------|
| `.env` committed | **No** |
| API keys in committed source | **None** |
| Placeholder secrets in `.env.example` | `CHANGE_ME` only (acceptable) |
| Demo password `password123` in docs/tests | Intentional demo credential |

**HIGH PRIORITY issues:** None

---

## Dataset verification

- All committed datasets are **synthetic** or curated educational KB text
- `LICENSING.md` present per ML dataset folder
- No MIMIC/NHANES/PHI committed
- `docs/DATASET_GOVERNANCE.md` committed in docs commit

---

## Model artifact verification

- Zero artifact files in git history (post-consolidation commits)
- `docs/MODEL_ARTIFACT_GOVERNANCE.md` committed
- Regeneration via `models/*/train.py` documented

---

## Remaining untracked files

**0** trackable untracked files (`git ls-files --others --exclude-standard`)

Working tree: **clean**

---

## Remaining ignored files (expected)

- `models/*/artifacts/` (7 directories)
- `apps/research-site/node_modules/`
- `apps/research-site/dist/`
- Python/Node caches

---

## Test results (post-consolidation)

| Suite | Command | Result |
|-------|---------|--------|
| ML Phases 1–3 | `PYTHONPATH=. pytest tests/phase1 tests/phase2 tests/phase3 -q` | **PASS** (59) |
| ML Phases 4–9 | `PYTHONPATH=. pytest tests/phase4..phase9 -q` | **PASS** (75) |
| Auth unit | `pytest tests/unit/auth-service -q` | **PASS** (8) — requires `pip install -r requirements-dev.txt` |
| AI + health unit | `pytest tests/unit/ai-service tests/unit/health-service -q` | **PASS** (137) |
| Combined unit (all) | `pytest tests/unit -q` | **PARTIAL** — 8 auth failures when run with ai-service (import isolation; pre-existing) |
| Demo preflight | `powershell -File scripts/demo_preflight.ps1` | **ENVIRONMENT BLOCKED** — no `.env`, services not running |

---

## Observations resolved during consolidation

| # | Observation | Resolution |
|---|-------------|--------------|
| 1 | `00_PROJECT_STATE.md` stale | Updated in docs commit (Phases 1–9, honest limits) |
| 2 | Migration 004 untracked | Committed in infra commit; adds `explanation_en/hi` columns |
| 3 | Duplicate benchmark docs | Removed 5 root stubs; `docs/benchmark_*.md` is canonical |
| 4 | `requirements-dev.txt` missing | Created; aggregates service deps + pytest |

Additional hygiene:
- `.gitignore` extended (Plan C results, HF cache, `.vercel`)
- `demo_preflight.ps1` Unicode dashes replaced (script now parses on Windows)

---

## Known observations (non-blocking)

1. **Unit test isolation:** Auth tests fail when run in same pytest session as full `tests/unit/ai-service` — pass in isolation. Not introduced by consolidation.
2. **Demo preflight:** Requires `.env` + running services — not validated in audit environment.
3. **Root `phase*-summary.md`:** Kept alongside `docs/` summaries (some overlap; documented in Phase 10 report).
4. **Model artifacts:** Must be regenerated locally if enabling ML flags.

---

## Repository health score

| Dimension | Before | After |
|-----------|--------|-------|
| Git hygiene | 2/5 | **5/5** |
| Secret safety | 5/5 | **5/5** |
| Large file hygiene | 5/5 | **5/5** |
| Test coverage (ML) | 4/5 | **4/5** |
| Documentation | 4/5 | **5/5** |
| Reproducibility | 3/5 | **4/5** (`requirements-dev.txt` added) |

**Overall: 4.5 / 5**

---

## Final status

# CONSOLIDATION COMPLETE WITH OBSERVATIONS

All approved work committed in 11 logical commits. No push performed. Awaiting explicit approval for remote publish.
