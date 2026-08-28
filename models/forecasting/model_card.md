# Model Card — Biomarker Forecaster (Phase 5)

| Field | Value |
|-------|-------|
| Name | BiomarkerForecastEngine |
| Primary | LightGBM Regressor |
| Fallback | XGBoost Regressor |
| Baseline | Linear Regression |
| Flag | `USE_FORECAST_MODEL` (default off) |

## Intended use

Statistical forecasting of lab values from irregular longitudinal history.

**Not** diagnosis, not treatment advice.

## Data

Synthetic longitudinal labs shipped. MIMIC/eICU/NHANES optional offline paths only.

## Caveats

- Synthetic metrics are not clinical performance.
- Prediction intervals from residual std (approx. 90% under normality).
- Requires ≥2 historical points for model path; otherwise persistence + low confidence.
