### Evaluation (image quality Phase 8)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/image_quality_phase8_latest.json` | MobileNet / EfficientNet / OpenCV comparison |
| `docs/benchmark_phase8.md` | Analysis |

### Evaluation (anomaly Phase 7)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/anomaly_phase7_latest.json` | IF vs LOF vs Robust Z + latency |
| `docs/benchmark_phase7.md` | Analysis |

### Evaluation (health score Phase 6)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/health_score_phase6_latest.json` | MAE/RMSE/R²/calibration/SHAP + latency |
| `docs/benchmark_phase6.md` | Analysis |

### Evaluation (forecast Phase 5)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/forecast_phase5_latest.json` | MAE/RMSE/MAPE/R²/PI coverage/trend per biomarker |
| `docs/benchmark_phase5.md` | Analysis |

### Evaluation (risk Phase 4)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/risk_phase4_latest.json` | Rule vs ML ROC/PR/ECE per disease |
| `docs/benchmark_phase4.md` | Analysis |

### Evaluation (retrieval Phase 3)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/retrieval_phase3_latest.json` | BM25 vs semantic Recall/MRR/nDCG/latency |
| `docs/benchmark_phase3.md` | Written analysis |

### Evaluation (normalizer)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/normalizer_phase2_latest.json` | Rule vs ML top-1/top-3/LOINC/latency |
| `docs/benchmark_phase2.md` | Written analysis |

---

# Evaluation notes (OCR)

| Artifact | Meaning |
|----------|---------|
| `datasets/evaluation/ocr_phase1_latest.json` | Plan C text bake-off: **legacy regex** vs **postprocess** (not live VLM decode) |
| `datasets/evaluation/ocr_phase1a_bench.json` | Phase 1A engineering timings (no weights) |

Do **not** present `unlimited_ocr_postprocess` F1 as baidu/Unlimited-OCR model accuracy (O-12).
True VLM quality requires a warm `UNLIMITED_OCR_ENDPOINT` and labeled scan gold.
