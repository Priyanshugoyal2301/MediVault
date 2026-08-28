# Model Card — Personalized Health Score (Phase 6)

| Field | Value |
|-------|-------|
| Name | HealthScoreEngine |
| Primary | XGBoost Regressor |
| Fallback | LightGBM Regressor |
| Flag | `USE_HEALTH_SCORE_MODEL` (default off) |
| Explainability | SHAP (+ fallback) |

## Intended use

Aggregate 0–100 non-diagnostic health **orientation** score from labs, demographics, trend proxies, and soft risk/forecast aggregates.

## Data

Synthetic longitudinal series shipped. NHANES/MIMIC optional offline paths only.

## Caveats

- Synthetic metrics ≠ clinical performance.
- SHAP is local estimate; absence of package uses centered/gain fallback.
- Not a diagnosis or treatment guide.
