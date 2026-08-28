# model1a-validation — Phase 1A Unlimited-OCR Hardening

**Date:** 2026-08-11  
**Scope:** Engineering fixes only from `validation/model1-validation.md`  
**Verdict:** **PASS**

---

## Observation Status

| ID | Status | Notes |
|----|--------|-------|
| O-01 | **Deferred** | Restart still required for flag flip; documented |
| O-02 | **Not Applicable** (by design) | Flag means “try Unlimited” + fallback |
| O-03 | **Deferred** | Confidence remains internal for API BC |
| O-04 | **Accepted** | Soft empty + logging |
| O-05 | **Deferred** | Accuracy is future ML/Phase 2 |
| O-06 | **Fixed** | `auto` HTTP-only; explicit local allow |
| O-07 | **Fixed** | Empty lab → failure → legacy |
| O-08 | **Fixed** | `tests/phase1a/` e2e-style coverage |
| O-09 | **Mitigated** | Docs + PHI warning on endpoint |
| O-10 | **Fixed** | CONFIG, DEPLOY, ML_ARCH, API, etc. |
| O-11 | **Deferred** | Live VLM bake-off needs ops hardware |
| O-12 | **Fixed** | Evaluation disclaimer docs |
| Arch layering | **Fixed** | `CompatibilityLabValue` |

Review detail: `docs/phase1a-observation-review.md`.

---

## Performance Comparison

| Metric | Phase 1 risk | Phase 1A |
|--------|--------------|----------|
| auto→local hang | Present | **Removed** |
| Empty [] skip fallback | Present | **Fixed** |
| Config load | — | &lt; 50 ms |
| Fallback recovery | unmeasured | ~tens of ms (bench) |
| Accuracy F1 | Unchanged intentionally | Unchanged |

See `docs/benchmark_phase1a.md`.

---

## Regression Analysis

| Suite | Result |
|-------|--------|
| `tests/phase1a` + `tests/phase1` + `tests/unit/ai-service` | **152 passed** |
| Legacy default path | Intact (`USE_UNLIMITED_OCR=0`) |
| Public `/parse` schema | Unchanged |
| Flag default | Remains `0` |
| FE / DB / retrieval / normalizer | Untouched |

---

## Remaining Risks

1. Live VLM quality still unproven on production scans.  
2. Remote HTTP endpoint is a PHI egress surface if misconfigured.  
3. Flag hot-reload still needs process restart.  
4. Without Phase 2 normalizer, Unlimited path remains suboptimal for canonical gold match.

---

## Deployment Readiness

| Item | Status |
|------|--------|
| Default safe path (legacy) | **Yes** |
| Experimental Unlimited with private endpoint | **Yes** (ops) |
| Default cutover to Unlimited | **No** (accuracy gates) |
| Repo deployable | **Yes** |

---

## Repository Health Score

| Dimension | Score / 10 |
|-----------|------------|
| Fallback robustness | 9 |
| Backend safety | 9 |
| Tests | 8 |
| Docs | 8 |
| Production cutover readiness (Unlimited) | 4 |
| **Overall Phase 1A engineering health** | **8.5 / 10** |

---

## Success criteria checklist

- [x] All observations reviewed  
- [x] Engineering fixes for O-06/O-07 + logging/config/tests  
- [x] No regressions in targeted suites  
- [x] Integration tests `tests/phase1a/`  
- [x] Startup validation / health  
- [x] Logging improved  
- [x] Documentation completed for this phase  
- [x] Repository deployable  
- [x] Validation written  

**PHASE 1A: COMPLETE (PASS)**  
**Do not proceed to Phase 2 until product accepts this validation.**
