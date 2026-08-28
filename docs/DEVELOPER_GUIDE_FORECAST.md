# Developer guide — Biomarker forecasting

1. Keep `USE_FORECAST_MODEL=0` for demos.  
2. Train: `python models/forecasting/train.py`  
3. Eval: `python models/forecasting/evaluate.py`  
4. Smoke with flag on: `get_biomarker_forecaster().forecast(history, horizon_days=180)`  
5. Never surface outputs as diagnoses.  
6. Prefer per-biomarker metrics over macro MAE.
