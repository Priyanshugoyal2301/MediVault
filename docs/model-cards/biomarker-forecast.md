# Model Card — Biomarker Forecaster

| Field | Value |
|-------|-------|
| Name | BiomarkerForecastEngine |
| Phase | 5 |
| Primary | LightGBM Regressor |
| Fallback | XGBoost Regressor |
| Baseline | Linear / Ridge Regression |
| Flag | `USE_FORECAST_MODEL` (default **off**) |
| Package | `models/forecasting/` |

## Intended use

Statistical forecasts of future lab values from irregular longitudinal history, with prediction intervals and trend direction.

## Out of scope

Diagnosis, treatment recommendations, population screening claims.

## Training data

Synthetic longitudinal series in-repo. Optional MIMIC / eICU / NHANES paths offline only.

## Metrics

Offline synthetic eval (see `docs/benchmark_phase5.md`). **Not** clinical certification.

## Safety

Mandatory disclaimer EN/HI. Registry default unavailable until flag on.
