# Phase 10 — Baseline Validation

**Audit date:** 2026-08-28  
**Environment:** Windows 10, Python 3.12.10, repo root  
**Note:** No code was modified to make tests pass.

---

## 1. Test matrix

| Suite | Command | Result | Passed | Failed | Skipped | Notes |
|-------|---------|--------|--------|--------|---------|-------|
| Core unit tests | `python -m pytest tests/unit/ -q` | **PARTIAL FAIL** | 137 | 8 | 0 | All 8 failures in `auth-service` |
| Auth unit (isolated) | `pytest tests/unit/auth-service/test_auth.py -v` | **FAIL** | 0 | 8 | 0 | `ModuleNotFoundError: No module named 'jose'` |
| ML Phase 1–3 | `PYTHONPATH=. pytest tests/phase1 tests/phase2 tests/phase3 -q` | **PASS** | 59 | 0 | 0 | |
| ML Phase 4–9 | `PYTHONPATH=. pytest tests/phase4..phase9 -q` | **PASS** | 75 | 0 | 0 | |
| Non-auth unit + phases | `PYTHONPATH=. pytest tests/unit/ai-service tests/unit/health-service tests/phase1..phase9 -q` | **COLLECTION ERROR** | — | 1 error | — | Import conflict when combining certain suites; individual suites pass |
| Demo preflight | `powershell -File scripts/demo_preflight.ps1` | **NOT RUNNABLE** | — | — | — | See §2 |
| Smoke demo | `powershell -File scripts/smoke_demo.ps1` | **NOT RUN** | — | — | — | Requires live services + `.env` |

**Aggregate (runnable offline ML + service unit tests, excluding auth):**  
**~271 tests passed** (137 unit − 8 auth + 59 phase1–3 + 75 phase4–9, with minor overlap in unit ai-service counts)

---

## 2. Failure classification

### Auth unit tests (8 failures)

| Classification | **Dependency / environment issue** |
|----------------|----------------------------------|
| Root cause | `python-jose` not installed in the active global Python 3.12 environment |
| Evidence | `ModuleNotFoundError: No module named 'jose'` in `services/auth-service/core/security.py` |
| Pre-existing? | Likely — last commit passed in CI/dev venv with `pip install -r services/auth-service/requirements.txt` |
| Regression from local changes? | **Unlikely** — import failure, not logic failure |
| Remediation | Install auth-service requirements before release validation; document in README |

### Demo preflight script

| Classification | **Environment + script encoding issue** |
|----------------|----------------------------------------|
| Root cause 1 | No `.env` file on disk (expected for fresh clone) |
| Root cause 2 | PowerShell parser error on Unicode em-dash (`—`) characters in `scripts/demo_preflight.ps1` lines 12, 21, 29 |
| Services running? | **No** — ports 8000–8003 not expected to be up during audit |
| Remediation | Copy `.env.example` → `.env`; fix script to ASCII dashes; start services per `docs/DEMO_SCRIPT.md` |

### Phase test collection (combined run)

| Classification | **Unknown / low severity** |
|----------------|---------------------------|
| Note | `tests/phase7/test_anomaly.py` collects fine in isolation; error only when run with full unit+phase bundle |
| Impact | Does not block individual phase validation |
| Remediation | Investigate pytest import path / namespace collision before CI hardening |

---

## 3. Environment limitations

| Limitation | Impact on audit |
|------------|-----------------|
| No `.env` | Cannot run live demo or preflight |
| Services not started | Cannot smoke-test HTTP endpoints |
| Global Python (not project venv) | Auth deps missing (`jose`) |
| No Postgres running | DB-dependent integration tests not exercised |
| Windows PowerShell encoding | Preflight script parse failure |

---

## 4. Baseline conclusion

| Area | Status |
|------|--------|
| ML phase test suites (1–9) | **Green** when run with `PYTHONPATH=.` |
| Service unit tests (ai + health) | **Green** |
| Auth unit tests | **Red** — missing dependency in audit environment |
| Live demo path | **Not validated** — environment not provisioned |
| Regression from uncommitted work | **No evidence** of ML test regressions |

**Recommendation:** Before tagging a release baseline, re-run full suite inside a project venv with all `requirements.txt` files installed and document the command in `reproducibility-gap-analysis.md`.
