# Architecture — Biomarker Forecasting (Phase 5)

```
Caller (internal) → get_biomarker_forecaster()
  USE_FORECAST_MODEL=0: UnavailableBiomarkerForecaster
  USE_FORECAST_MODEL=1: BiomarkerForecastEngine
       features → LightGBM|XGBoost|Linear
       → BiomarkerForecastBatch (values, PI, confidence, trend)
```

No existing public HTTP routes. No frontend hooks.
