# models/forecasting — Longitudinal Biomarker Forecasting (Phase 5)

## Status

| Flag | Path |
|------|------|
| `USE_FORECAST_MODEL=0` (default) | Unavailable forecaster |
| `USE_FORECAST_MODEL=1` | ML forecast + unavailable fallback |

## Architecture

| Role | Model |
|------|-------|
| Primary | LightGBM Regressor |
| Fallback | XGBoost Regressor |
| Baseline | Linear / Ridge Regression |
| Future | LSTM / Temporal Transformer **stubs** (pluggable) |

## Biomarkers

HbA1c, Fasting/Random Glucose, Creatinine, eGFR, ALT, AST, Chol, LDL, HDL, TG, TSH, Hemoglobin (configurable).

## Safety

Forecasts only — never diagnoses. Mandatory disclaimer on batches.

## Commands

```bash
python models/forecasting/train.py
python models/forecasting/evaluate.py
```
