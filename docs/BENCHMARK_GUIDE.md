# Benchmark Guide

## Per-phase

| Phase | Command | Report |
|-------|---------|--------|
| 1 OCR | `python models/ocr/evaluate.py` | `docs/benchmark_phase1.md` |
| 2 Norm | `python models/normalizer/evaluate.py` | `docs/benchmark_phase2.md` |
| 3 Retrieval | `python models/retrieval/evaluate.py` | `docs/benchmark_phase3.md` |
| 4 Risk | `python models/risk_prediction/evaluate.py` | `docs/benchmark_phase4.md` |
| 5 Forecast | `python models/forecasting/evaluate.py` | `docs/benchmark_phase5.md` |
| 6 Health | `python models/health_score/evaluate.py` | `docs/benchmark_phase6.md` |
| 7 Anomaly | `python models/anomaly_detection/evaluate.py` | `docs/benchmark_phase7.md` |
| 8 Quality | `python models/image_quality/evaluate.py` | `docs/benchmark_phase8.md` |

## Unified

```bash
python models/platform/benchmark_suite.py
```

Outputs:

- `benchmark_complete.md`
- `docs/benchmark_complete.md`
- `datasets/evaluation/platform_benchmark_complete.json`

## Interpreting results

- Prefer **per-biomarker / per-label** metrics over mixed-unit macros.
- Synthetic ROC/R² ≠ clinical performance.
- Default-path latency in the unified report is **flags OFF** (production-safe).
