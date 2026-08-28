# Model Card — Personalized Health Score

| Field | Value |
|-------|-------|
| Name | HealthScoreEngine |
| Phase | 6 |
| Primary | XGBoost Regressor |
| Fallback | LightGBM Regressor |
| Flag | `USE_HEALTH_SCORE_MODEL` (default **off**) |
| Explainability | SHAP TreeExplainer (+ fallback in `models/explainability`) |

## Intended use

0–100 non-diagnostic health orientation score with contributor explanations.

## Out of scope

Diagnosis, treatment, triage claims.

## Training data

Synthetic series in-repo. NHANES/MIMIC offline optional only.

## Safety

Mandatory disclaimer. Registry unavailable when flag off.
