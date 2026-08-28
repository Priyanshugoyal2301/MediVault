# Benchmark — Phase 6 Personalized Health Score

**Date:** 2026-08-11  
**Backend:** XGBoost (primary); LightGBM & linear available  
**Data:** Synthetic longitudinal labs (`datasets/health_score/`)  
**Explainability:** SHAP TreeExplainer (library installed) + fallback attributions in `models/explainability/`

## Headline metrics (synthetic holdout)

| Metric | Value |
|--------|-------|
| MAE | **~2.00** |
| RMSE | **~2.44** |
| MAPE | (see JSON) |
| R² | **~0.991** |
| Residual calibration error | (see JSON) |
| E2E score + explain | **~1.3 s** first SHAP path; subsequent faster |
| Flag default | `USE_HEALTH_SCORE_MODEL=0` |

Artifact: `datasets/evaluation/health_score_phase6_latest.json`.

## Feature importance (global, train)

| Rank | Feature | Importance (gain-norm) |
|------|---------|------------------------|
| 1 | hba1c | ~0.81 |
| 2 | ldl | ~0.09 |
| 3 | egfr | ~0.02 |
| 4 | forecast_worsening_proxy | ~0.02 |
| 5+ | lipids, risk proxies, hdl, … | residual |

## SHAP summary

- Local per-patient attributions via **SHAP TreeExplainer** on XGBoost.
- Positive contributors raise score (supports); negative lower score (attention areas).
- Humanized labels (e.g. Elevated HbA1c, High LDL, Normal Hemoglobin).
- If `shap` missing, **centered × gain fallback** still yields explanations.

## Failure analysis

1. **Synthetic circularity** — labels from heuristic formula → high R² not clinical validity.  
2. **Cold SHAP** — first TreeExplainer build can be ~1s on CPU.  
3. **Sparse labs** — high missing fraction → lower confidence, more imputation.  
4. **Missing SHAP package** — fallback method; still non-diagnostic.

## Recommendations

1. Keep production **`USE_HEALTH_SCORE_MODEL=0`** until NHANES/MIMIC-aligned labels + clinician review.  
2. Pin `shap` in deploy images for consistent XAI.  
3. Cache TreeExplainer on process warm-up after flag on.  
4. Recalibrate confidence on real residuals (not synthetic).  
5. Future wearables as optional feature columns only.

---

Regenerate: `python models/health_score/evaluate.py`
