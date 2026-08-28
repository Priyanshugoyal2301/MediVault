# Phase 5 — Forecast validation report

**Verdict: PASS WITH OBSERVATIONS**

Date: 2026-08-11

## Checklist

| Item | Result |
|------|--------|
| Forecast model loads | ✓ LightGBM artifacts under `models/forecasting/artifacts/` |
| Feature flag works | ✓ `USE_FORECAST_MODEL=0` → unavailable; `=1` → ML + fallback |
| Historical sequence handled | ✓ temporal order, lags, slope, irregular intervals |
| Missing history handled | ✓ n&lt;2 → persistence / low confidence; empty history → safe batch |
| Prediction intervals generated | ✓ lower/upper + confidence on model path |
| APIs unchanged | ✓ no new public routes; registry-only |
| Frontend unchanged | ✓ |
| No regressions (flags default off) | ✓ OCR / normalizer / retrieval / risk defaults preserved |
| LightGBM operational | ✓ primary `auto` backend this host |
| XGBoost fallback path | ✓ `create_backend("xgboost")` operational |
| Linear baseline | ✓ |
| Tests | ✓ `tests/phase5` + ml_infra (21 related phase5 file all green) |
| Benchmarks | ✓ `docs/benchmark_phase5.md` |

## Observations

| ID | Severity | Note |
|----|----------|------|
| **O-01** | Medium | Eval on **synthetic** longitudinal data only; MIMIC/eICU/NHANES optional env paths, not shipped. Metrics ≠ clinical performance. |
| **O-02** | Low | Prediction intervals = residual-std × z (≈90% normal), not conformal; coverage imperfect. |
| **O-03** | Low | Trend accuracy moderate on synthetic labels (~0.4); directional forecasts should not be user-facing without review. |
| **O-04** | Info | Macro MAE/RMSE mix units across biomarkers — always slice per analyte. |

## Gate decision

**PASS WITH OBSERVATIONS** — Phase 5 complete for software delivery (flag-off default, pluggable regressors, train/eval, tests, docs). **Not** clinical certification.

If any later change breaks default-off or public APIs → re-open as **FAIL**.
