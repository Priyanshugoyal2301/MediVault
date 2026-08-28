# Benchmark Results Index

| Phase | Report | Metrics artifact |
|-------|--------|------------------|
| Plan B | `docs/ML_PLAN_B_RESULTS.md` | (historic) |
| Plan C | `docs/PLAN_C_REPORT.md` | `data/datasets/plan_c/results_latest.json` |
| **Phase 1 OCR** | [`docs/benchmark_phase1.md`](./benchmark_phase1.md) | `datasets/evaluation/ocr_phase1_latest.json` |
| **Phase 5 Forecast** | [`docs/benchmark_phase5.md`](./benchmark_phase5.md) | `datasets/evaluation/forecast_phase5_latest.json` |
| **Phase 6 Health score** | [`docs/benchmark_phase6.md`](./benchmark_phase6.md) | `datasets/evaluation/health_score_phase6_latest.json` |
| **Phase 7 Anomaly** | [`docs/benchmark_phase7.md`](./benchmark_phase7.md) | `datasets/evaluation/anomaly_phase7_latest.json` |
| **Phase 8 Image quality** | [`docs/benchmark_phase8.md`](./benchmark_phase8.md) | `datasets/evaluation/image_quality_phase8_latest.json` |

Latest Phase 1 headliners (text fixtures, offline):

- Legacy field F1 ≈ **0.97**  
- Unlimited postprocess field F1 ≈ **0.16** (no normalizer; VLM weights not loaded)  
- Flag default remains **off**

Phase 5 headliners (synthetic longitudinal, offline LightGBM):

- Macro MAE ≈ **4.6** (mixed units — use per-biomarker)  
- HbA1c MAE ≈ **0.14**  
- Flag default remains **off** (`USE_FORECAST_MODEL=0`)

Phase 6 headliners (synthetic health score, offline XGBoost + SHAP):

- MAE ≈ **2.0**, R² ≈ **0.99** (synthetic heuristic labels — not clinical)  
- Flag default remains **off** (`USE_HEALTH_SCORE_MODEL=0`)
