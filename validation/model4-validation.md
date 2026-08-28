# model4-validation — Phase 4 Disease Risk Prediction

**Auditor role:** Independent Machine Learning Validation Engineer  
**Scope:** Phase 4 only (read-only; no fixes, no retrain, no refactors)  
**Date:** 2026-08-11  
**Verdict:** **PASS WITH OBSERVATIONS**

---

## Executive Summary

The Disease Risk Prediction Engine is **implemented, flag-gated, non-diagnostic, and deploy-safe** with production default **off**. XGBoost is operational on this environment; LightGBM and logistic regression backends instantiate correctly; offline sklearn HistGradientBoosting remains a hard fallback. Benchmarks, tests, and documentation exist.

The phase does **not** fail on production safety, backward compatibility, or core functional gates. Several requirements are only **partially** met relative to the full Phase 4 / validation charters (notably dataset sources and flag-off “rule path” wiring). Those are documented as **observations**, not blocking defects for demo deployability.

**Do not treat synthetic ROC-AUC ≈ 0.98 as clinical validation.**

---

## 1. Architecture Review

| Check | Result | Evidence |
|-------|--------|----------|
| Disease Risk module exists | **Pass** | `models/risk_prediction/` (infer, train, evaluate, datasets, classifiers, preprocess, metrics, config) |
| Modular architecture | **Pass** | ClassifierBackend ABC; DiseaseRiskEngine; adapters in ai-service |
| Model abstraction | **Pass** | Swappable via `RISK_MODEL_BACKEND` / `create_backend()` |
| XGBoost present | **Pass** | `XGBoostBackend` in `classifiers.py`; artifacts `meta.json` backend=`xgboost` |
| LightGBM fallback present | **Pass** | `LightGBMBackend`; probe `create_backend("lightgbm")` → `lightgbm` |
| Logistic baseline | **Pass** | `LogisticBackend`; probe → `logistic_regression` |
| No duplicated business logic (material) | **Pass w/ note** | Rules live in `rules.py`; ML in engine; adapter thin. Dual flags/docs (`models/risk` redirects) intentional. |
| Circular dependencies | **Pass** | No cycles found among train/infer/adapters |
| No hardcoded secrets | **Pass** | None observed |
| Config-driven paths | **Pass** | `config.yaml` + env overrides in `config_loader.py` |
| Absolute business paths | **Pass** | Relative to package; resolved by loader |

**Artifact health (observed):**  
`models/risk_prediction/artifacts/` ~458 KB trained models; meta lists 5 diseases, 27 features, backend `xgboost`.

---

## 2. Feature Flag Validation

| Flag / behavior | Result |
|-----------------|--------|
| Production default | **OFF** — `use_risk_model=False`, `get_risk_predictor()` → `UnavailableRiskPredictor`, `risk_band=unavailable` |
| `USE_RISK_MODEL=1` | **ML path** — registry logs `risk_predictor=ml_disease`, backend xgboost on this host |
| `USE_DISEASE_RISK_MODEL=1` (with `USE_RISK_MODEL=0`) | **Honored as alias** — feature_flags maps to `use_risk_model=True` |
| Zero-code rollback | **Pass** — toggle env + restart (registry `@lru_cache`) |
| Flag-off = “rule-based insights” per validation Step 2 | **Gap (observation O-01)** — flag-off returns **Unavailable**, not `RuleBasedRiskPredictor`. Rule heuristics exist and are used in **evaluation**, not live flag-off path |

`.env.example` documents both flags default `0`.

---

## 3. Dataset Review

| Resource | Integrated as shipped data? | Notes |
|----------|----------------------------|--------|
| Synthetic educational loaders | **Yes** | `train_synthetic.jsonl` (~900), `eval_synthetic.jsonl` (~250) |
| MIMIC-IV | **No** (optional path only) | `MIMIC_RISK_PATH`; not redistributed — licensing OK |
| NHANES | **No** (optional) | `NHANES_RISK_PATH` |
| UCI Heart / Pima | **No** (optional) | docs mention `PIMA_PATH` / UCI; eICU not auto-merged |
| eICU | **No** | Documented only |
| Proprietary PHI committed | **Not found** | LICENSING.md present |
| Train/eval separation | **Pass** | Separate seed-controlled synthetic files (not random split of one file at runtime) |
| Label mapping | **Pass** | Multi-label dicts per disease id |

**Observation O-02:** Charter listed MIMIC/NHANES/Pima/etc. as “primary/secondary datasets.” Implementation **honestly** ships synthetic data + offline env loaders. This is **licensing-correct** but **not** full source integration. Benchmark numbers apply only to synthetic distribution.

---

## 4. Feature Engineering Review

| Item | Result |
|------|--------|
| Missing handling | **Pass** — median impute from train (`impute.json`); `missing_fraction` feature |
| Name normalization / synonyms | **Pass** — `TEST_NAME_SYNONYMS` + latest-value collapse |
| Derived ratios | **Pass** — AST/ALT, TC/HDL, non-HDL |
| Encoding (sex) | **Pass** — `sex_female` 0 / 1 / 0.5 |
| Train=infer feature set | **Pass** — shared `FEATURE_COLUMNS` |
| Feature selection | **Partial** | Non-constant helper exists; not a full selection pipeline in prod path |
| Data leakage | **Pass (synthetic)** | Labels generated with explicit disease bias; no target columns in features |
| Config-driven FE | **Partial** | Thresholds/backends config-driven; synonym table is code constants |
| Scaling | **Pass for logistic** | Pipeline StandardScaler; trees unscaled (appropriate) |

---

## 5. Model Validation

| Item | Result |
|------|--------|
| Model loads | **Pass** — engine loads pickled per-disease models |
| Probabilities in [0,1] | **Pass** — clamped |
| Categories low/moderate/high | **Pass** — thresholds 0.33 / 0.66 |
| Confidence | **Pass** — heuristic from missingness + probability margin (not Platt/isotonic) |
| Multi-condition detail | **Pass** — `conditions` on `RiskPredictionResult` |
| Calibration metrics in eval | **Pass** — ECE reported per disease in JSON |
| Aggregate `risk_score` vs `risk_band` | **Observation O-03** — `risk_score` is **mean** of 5 probs; `risk_band` follows **max** condition. Probe: alias path `risk_score≈0.085` with `risk_band=moderate` (band driven by highest condition). Can confuse API consumers |
| sklearn_gb feature importance | **Observation O-04** — returns zero-ish placeholders when HistGB path used |

**Probe (flag on, HbA1c=8 + Hb=10):** multi-condition summary present; 5 conditions returned.

---

## 6. Safety Validation

| Requirement | Result |
|-------------|--------|
| “Risk estimate only” | **Pass** — in `DISCLAIMER_EN` and summary prefix |
| “Not a medical diagnosis” | **Pass** |
| Informational use | **Pass** |
| “You have diabetes / kidney disease” | **Not observed** — probe `you have? False`; unit test asserts against “you have diabetes” |
| Probabilistic framing | **Pass** — “≈ X%”, “Increased statistical risk only” |

---

## 7. API & Backward Compatibility

| Check | Result |
|-------|--------|
| Existing HTTP APIs | **Pass** — no `/risk` router; `get_risk_predictor` internal/registry only |
| Frontend | **Pass** — no FE coupling found |
| Database | **Pass** — no schema changes for Phase 4 |
| OCR / Normalizer / Retrieval packages | **Not re-audited as full phases** — Phase 4 grep shows no intentional edits required for risk; regression suite includes phase2/3 + unit infra |
| Public response schemas | **Pass** — unchanged; optional `conditions`/`disclaimer_en` on DTO are additive with defaults |

---

## 8. Performance Benchmarks

Source: `datasets/evaluation/risk_phase4_latest.json` (backend **xgboost**, n=250).

### Macro

| System | Macro ROC-AUC | Mean latency |
|--------|--------------:|-------------:|
| Rule thresholds | 0.962 | ~0.008 ms |
| **ML (XGBoost)** | **0.984** | ~2.67 ms |

### type2_diabetes (illustrative per-metric block)

| Metric | Rule | ML |
|--------|-----:|---:|
| Accuracy | 0.816 | 0.972 |
| Precision | 0.550 | 1.000 |
| Recall / Sensitivity | 0.982 | 0.875 |
| Specificity | 0.768 | 1.000 |
| F1 | 0.705 | 0.933 |
| ROC-AUC | 0.966 | 0.997 |
| PR-AUC | 0.927 | 0.973 |
| ECE | 0.245 | 0.030 |

(Full per-disease tables live in the JSON artifact + `docs/benchmark_phase4.md`.)

| Resource | Observed |
|----------|----------|
| Artifact tree size | ~458 KB |
| Memory / GPU peak | Not instrumented in suite (O-05) |

**Observation O-05:** Memory usage / model RSS not measured in automated benchmark; claim of “Memory Usage / Model Size” only partially covered (disk size only).

---

## 9. Error Handling

| Input | Behavior | Assessment |
|-------|----------|------------|
| Empty metrics `[]` | Returns 5 low probs (impute) | Graceful |
| Invalid numeric strings | Skipped in extract; no crash | Graceful |
| Out-of-range values | No crash; scores still returned | Graceful; **no hard medical bounds** (O-06) |
| Incomplete report | Impute + confidence down-weighting | Graceful |
| `metrics=None` | Treated as empty (`metrics or []`) — **does not raise** | Graceful but silent (O-07) |
| ML init failure | Registry falls back to Unavailable | Pass |

---

## 10. Test Coverage

**Command (read-only):**  
`pytest tests/phase4 tests/unit/ai-service/test_ml_infra.py tests/phase2 tests/phase3 -q`

| Suite focus | Result |
|-------------|--------|
| Total (this run) | **58 passed**, 0 failed |
| phase4 unit/flag/safety/perf | Included (`tests/phase4/test_risk.py`) |
| Integration (registry flag on/off) | Present |
| Regression adjacent phases | phase2 + phase3 green in same run |
| Coverage % (line coverage tools) | **Not measured** (no `coverage.py` report in validation session) — O-08 |

Phase4 classes observed: preprocess, engine, safety language, flags, alias, rule baseline, fallback, performance, ECE helper, default-off regression.

---

## 11. Documentation Review

| Document | Present / accurate? |
|----------|---------------------|
| `docs/benchmark_phase4.md` / `benchmark_phase4.md` | Yes |
| `phase4-summary.md` | Yes |
| `docs/model-cards/disease-risk.md` | Yes |
| `docs/CONFIGURATION.md` flags | Yes |
| `docs/MODEL_REGISTRY.md` | Yes |
| `docs/ML_ARCHITECTURE.md`, `SYSTEM_DESIGN.md`, `API.md`, `TRAINING.md`, `ROADMAP.md`, `CHANGELOG.md` | Yes |
| `docs/ARCHITECTURE_RISK.md`, `DEVELOPER_GUIDE_RISK.md` | Yes |
| `docs/ml-migration-plan.md` | Mostly; **O-09** still has legacy “Phase 7 RiskPredictor planned” style row near older plan text (stale table noise) |
| `.env.example` | Yes |

Docs correctly state synthetic data limits and non-diagnosis policy.

---

## 12. Regression Review

| Area | Assessment |
|------|------------|
| Flag-off risk path | Demo-safe **unavailable** (no fabricated risk) |
| OCR / normalizer / retrieval | No Phase-4 test failures; independent unit/phase tests passed |
| Breaking API changes | None found |
| Performance regression for default demo | None — risk models not invoked when flag off |
| Side effects | Optional `RiskPredictionResult` fields additive |

---

## Known Issues / Observations (non-blocking)

| ID | Severity | Issue |
|----|----------|--------|
| **O-01** | Medium | Flag **off** is `UnavailableRiskPredictor`, not live `RuleBasedRiskPredictor`, despite validation wording “rule-based insight path.” Rule path exists but is eval/adapter only. |
| **O-02** | Medium | MIMIC/NHANES/Pima/UCI/eICU **not** integrated as primary corpora; synthetic only + optional JSONL env paths. |
| **O-03** | Medium | Aggregate `risk_score` (mean) inconsistent with `risk_band` (from max condition). |
| **O-04** | Low | `sklearn_gb` feature_importance stub returns zeros. |
| **O-05** | Low | Peak memory / GPU not in benchmark suite. |
| **O-06** | Low | No physiologic bounds; extreme lab values accepted. |
| **O-07** | Low | `None` metrics treated as empty list (silent). |
| **O-08** | Low | Line coverage % not produced. |
| **O-09** | Low | Migration plan still contains legacy “future risk” plan noise. |
| **O-10** | Info | Confidence is heuristic, not full probability calibration at inference. |
| **O-11** | Info | Synthetic ROC **must not** be marketed as clinical readiness. |

---

## Recommendations (for implementers — **not applied** by this audit)

1. Wire flag-off to `RuleBasedRiskPredictor` **or** update product charter to explicitly say “unavailable until validated ML.”  
2. Align `risk_score` with max condition probability (or document mean aggregation).  
3. Integrate licensed real datasets offline before any clinical claim; keep synthetic as unit smoke only.  
4. Add coverage report + memory benchmark.  
5. Bound-check extreme biomarker values with soft warnings in metadata.

---

## Deployment Readiness

| Criterion | Status |
|-----------|--------|
| Repo deployable with flags default off | **Yes** |
| Demo path unaffected | **Yes** |
| ML risk usable when flag + artifacts present | **Yes** (this host: XGBoost) |
| Clinical production cutover of risk scores | **No** — synthetic only; disclaimers required |

---

## Repository Health Score (Phase 4 surface)

| Dimension | Score / 10 |
|-----------|------------|
| Architecture modularity | 9 |
| Safety language | 9 |
| Flag isolation / deploy safety | 9 |
| Dataset honesty / licensing | 8 |
| Evaluation rigor (synthetic only) | 6 |
| Documentation | 8 |
| Test depth | 7 |
| Charter completeness (all named public datasets) | 5 |
| **Overall Phase 4 audit health** | **7.5 / 10** |

---

## Checklist vs Definition of Pass

| Gate | Met? |
|------|------|
| Disease Risk model implemented | ✅ |
| XGBoost operational | ✅ |
| LightGBM fallback operational | ✅ |
| Logistic baseline available | ✅ |
| Feature flag works | ✅ |
| APIs unchanged | ✅ |
| Frontend unchanged | ✅ |
| Benchmarks generated | ✅ |
| Safety disclaimers present | ✅ |
| Tests passing | ✅ (58 in audit session) |
| Validation report generated | ✅ (this document) |
| Documentation updated | ✅ |
| Repository deployable | ✅ |

---

## Final Decision

# **PASS WITH OBSERVATIONS**

Phase 4 is **approved to remain in-tree and default-off** for production demo safety.

It is **not** approved as a clinically validated disease-risk product surface, and charter gaps (O-01, O-02, O-03) should be accepted or fixed in a follow-up hardening phase **before** marketing risk scores or starting consumer UI work.

**Phase 5:** Proceed only if product owners **accept** this **PASS WITH OBSERVATIONS**. This audit does **not** auto-start Phase 5.

**Blocking FAIL criteria were not met** (no systematic crash, no diagnostic claims in outputs, no default-on ML, no public API break, tests green, XGBoost/LightGBM/logistic present).
