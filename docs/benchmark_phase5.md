# Benchmark — Phase 5 Biomarker Forecasting

**Date:** 2026-08-11  
**Backend (this host):** LightGBM (primary); XGBoost + linear available  
**Data:** Synthetic longitudinal labs only (`datasets/forecasting/`)  
**Horizon:** 180 days (~6 months)

## Headline metrics

| Metric | Value |
|--------|-------|
| Macro MAE | **4.59** (mixed units — interpret per biomarker) |
| Macro RMSE | **17.21** |
| Mean lag/pred latency | **~0.93 ms** |
| E2E full-patient forecast | **~13 ms** |
| Flag default | `USE_FORECAST_MODEL=0` |

### Per-biomarker (selected)

| Biomarker | MAE | RMSE | MAPE % | R² | PI cov. | Trend acc. |
|-----------|-----|------|--------|-----|---------|------------|
| HbA1c | 0.14 | 0.21 | 2.5 | 0.80 | 0.83 | 0.40 |
| Fasting glucose | 4.34 | 13.6 | 3.5 | 0.40 | 0.75 | 0.38 |
| Creatinine | (see full JSON) | | | | | |
| eGFR | 3.93 | 8.07 | 4.4 | 0.78 | 0.77 | 0.44 |
| ALT | 1.84 | 2.79 | 13.8 | 0.90 | 0.94 | 0.37 |
| TSH | (see full JSON) | | | | | |
| Hemoglobin | (see full JSON) | | | | | |

Full machine report: `datasets/evaluation/forecast_phase5_latest.json`.

## Forecast comparison

| Backend | Role | Status |
|---------|------|--------|
| LightGBM | Primary | Operational (used in auto) |
| XGBoost | Fallback | Operational code path |
| Linear / Ridge | Baseline | Operational |
| LSTM / Temporal Transformer | Future | Pluggable stubs |

## Error analysis

- **Synthetic targets** mix next-visit labels and slope-projected horizons → macro RMSE inflated by high-range labs (lipids/glucose) vs tight HbA1c/creatinine MAE.
- **PI coverage** often 0.75–0.95 vs nominal ~90% residual-normal assumption — residual std fitted on train is approximate calibration, not conformal.
- **Trend accuracy ~0.35–0.45** — noisy synthetic drift; direction labels use relative epsilon; not clinical trend ground truth.

## Failure cases

1. **n_history &lt; 2** → persistence / low confidence; not full ML path.  
2. **Unknown biomarker alias** → skipped from series map.  
3. **Empty history** → null/low-confidence forecasts + disclaimer.  
4. **Missing LightGBM/XGBoost wheels** → sklearn HistGB / linear auto chain (still online).

## Recommendations

1. Keep **production `USE_FORECAST_MODEL=0`** until real MIMIC/eICU/NHANES-aligned series and clinical review.  
2. Prefer **per-biomarker metrics**, not macro MAE/RMSE, when reporting.  
3. Replace residual-std PIs with **quantile regression or conformal intervals**.  
4. Improve trend labels with clinician-agreed thresholds per biomarker.  
5. Wearable fusion is reserved as future optional feature channels (not implemented).

## Memory / latency

- CPU inference, multi-model pickle load once per process when flag on.  
- E2E patient forecast &lt; 50 ms on synthetic history (dev host).

---

**Artifact:** regenerate with `python models/forecasting/evaluate.py`
