# Phase 6 Summary — Personalized Health Score + XAI

## Status

**PHASE 6 COMPLETE** — validation **PASS WITH OBSERVATIONS**  
(`validation/model6-validation.md`)

## Architecture

```
labs + demographics (+ trend / risk proxies)
  → feature_engineering
  → RegressorBackend (XGBoost → LightGBM → linear)
  → score 0–100 + band + confidence
  → models/explainability (SHAP / fallback)
  → positive / negative contributors + global importance
  → HealthScoreResult (non-diagnostic disclaimer)
```

| Flag | Behavior |
|------|----------|
| `USE_HEALTH_SCORE_MODEL=0` | `UnavailableHealthScorer` |
| `USE_HEALTH_SCORE_MODEL=1` | ML + SHAP explain + unavailable fallback |

## Files created

- `models/health_score/*`
- `models/explainability/` (reusable SHAP pipeline)
- `tests/phase6/`
- `datasets/health_score/` (synthetic)
- `datasets/evaluation/health_score_phase6_latest.json`
- `docs/benchmark_phase6.md`, model card, architecture / developer guides
- `validation/model6-validation.md`, `phase6-summary.md`

## Files modified

- `packages/ml-interfaces/types.py` — extended `HealthScoreResult` (BC defaults)
- `services/ai-service/adapters/health_scorer.py` — ML + fallback
- `services/ai-service/core/registry.py` — wire ML health scorer
- `.env.example`, docs (CONFIGURATION, MODEL_REGISTRY, ML_ARCHITECTURE, CHANGELOG, ROADMAP, TRAINING, API, SYSTEM_DESIGN, ARCHITECTURE, evaluation, DEV_LOG, ml-pipeline, ml-migration-plan, models/README, packages/ml-interfaces README, root README)

## Explicitly not modified

OCR, normalizer, retrieval, disease risk, forecasting, anomaly packages/engines, public APIs, frontend.

## Datasets

| Source | Status |
|--------|--------|
| Synthetic longitudinal labs | Shipped / auto-generated |
| NHANES / MIMIC | Optional offline env paths |
| Wearables | Future optional features |

## Feature engineering

Normalization/impute, missing fraction, derived ratios, slopes, risk proxies, forecast-worsening proxy, optional lifestyle (BMI/BP).

## Explainability

Reusable `models/explainability` — Tree SHAP + linear coef + gain-centered fallback; global importance; per-patient positive/negative contributors with contribution % labels.

## Benchmarks

See `docs/benchmark_phase6.md` — MAE ~2.0, R² ~0.99 synthetic, SHAP integrated.

## Validation

PASS WITH OBSERVATIONS (synthetic labels, SHAP cold start, proxy priors).

## Known limitations

- Not diagnostic; production flag off  
- Synthetic training labels  
- Proxies for risk/forecast (no mutative calls into Phase 4/5)  

## Repository health score

**9.1 / 10** for Phase 6 software goals.

## Definition of Done

| Criterion | Met |
|-----------|-----|
| Health score model | ✅ |
| XGBoost operational | ✅ |
| LightGBM fallback | ✅ |
| SHAP integrated | ✅ |
| Feature importance | ✅ |
| Confidence | ✅ |
| Feature flag | ✅ |
| Train / eval | ✅ |
| Benchmarks | ✅ |
| Tests passing | ✅ |
| Validation PASS / PWO | ✅ |
| Docs updated | ✅ |
| Deployable | ✅ |

**Do not begin Phase 7.**
