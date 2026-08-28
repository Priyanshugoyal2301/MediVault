# Benchmark — Phase 7 ML Anomaly Detection

**Date:** 2026-08-11  
**Active backend:** Isolation Forest  
**Data:** Synthetic normal + injected anomalies (`datasets/anomaly_detection/`)

## Headline comparison (synthetic holdout)

| Model | PR-AUC | Notes |
|-------|--------|-------|
| Isolation Forest (primary) | **~0.71** | Default `auto` backend |
| LOF (fallback) | **~0.95** | Strong on this synthetic joint structure |
| Robust Z (baseline) | **~0.25** | Weaker on multi-marker rare combos |
| E2E series detect | **~9 ms** | Single Creatinine series |

Full metrics (Precision@20, Recall@20, ROC-AUC, FPR, latency):  
`datasets/evaluation/anomaly_phase7_latest.json`

## Failure analysis

1. **Synthetic labels ≠ clinical rare-disease prevalence.**  
2. LOF can outperform IF on this generator; production still uses **Isolation Forest primary** per architecture charter (LOF is fallback when IF unavailable / via backend config).  
3. Single-analyte series with few points → heavy reliance on series robust-z + imputation of multi-marker slots.  
4. Score calibration to 0–1 is monotone transform of model scores — not calibrated probability.

## Recommendations

1. Keep **`USE_ANOMALY_MODEL=0`** in production until real NHANES/MIMIC eval + FAR review.  
2. Prefer LOF via `ANOMALY_MODEL_BACKEND=lof` only after FAR bake-off on real data.  
3. Tune `contamination` / `score_threshold` for acceptable false positive rate.  
4. Always language: **Anomalous laboratory pattern** — never disease names.

---

Regenerate: `python models/anomaly_detection/evaluate.py`
