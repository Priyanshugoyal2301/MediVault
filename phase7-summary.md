# Phase 7 Summary — ML Anomaly Detection

## Status

**PHASE 7 COMPLETE** — validation **PASS WITH OBSERVATIONS**

## Architecture

```
USE_ANOMALY_MODEL=0 (default) → StatisticalAnomalyDetector (existing)
USE_ANOMALY_MODEL=1 (or USE_OUTLIER_MODEL=1)
  → Isolation Forest (primary) | LOF | Robust Z
  → detect(series) for /anomaly/detect
  → score_profile(multi-marker) for internal multi-lab use
  → language: "Anomalous laboratory pattern detected"
```

## Files created

- `models/anomaly_detection/*`
- `tests/phase7/`
- `datasets/anomaly_detection/`
- `datasets/evaluation/anomaly_phase7_latest.json`
- `docs/benchmark_phase7.md`, model card, architecture / developer guides
- `validation/model7-validation.md`, `phase7-summary.md`

## Files modified

- `services/ai-service/adapters/anomaly_detector.py` — ML + fallback
- `services/ai-service/core/feature_flags.py` — `USE_ANOMALY_MODEL` + alias
- `services/ai-service/core/registry.py` — wire ML anomaly
- `packages/ml-interfaces/types.py` — optional Phase 7 fields on result
- `.env.example`, affected docs, `tests/unit/ai-service/test_ml_infra.py`

## Not modified

OCR, normalizer, retrieval, risk, forecasting, health score engines; public response schemas; frontend.

## Feature engineering

Robust scaling, impute, ratios, temporal series stats, soft risk/forecast/score proxies, missing handling.

## Benchmarks

See `docs/benchmark_phase7.md` (IF / LOF / Z comparison).

## Validation

PASS WITH OBSERVATIONS.

## Known limitations

- Synthetic labels  
- Single-series API under-uses multi-marker features unless profile scoring used  
- Score ≠ calibrated probability  

## Repository health score

**9.0 / 10** for Phase 7 software goals.

## Definition of Done

| Criterion | Met |
|-----------|-----|
| Isolation Forest | ✅ |
| LOF fallback | ✅ |
| Feature flag | ✅ |
| Train / eval | ✅ |
| Benchmarks | ✅ |
| Tests | ✅ |
| Validation PASS/PWO | ✅ |
| Docs | ✅ |
| Deployable | ✅ |

**Do not begin Phase 8.**
