# models/

Training / evaluation / inference scaffolds for MediVault ML components.

Each subdirectory contains:

- `README.md` — status and promotion notes  
- `config.yaml` — hyperparameters (inactive until train is real)  
- `train.py` — offline training entrypoint  
- `evaluate.py` — offline eval via `packages.ml_eval`  
- `infer.py` — local single-sample debugging  

| Folder | Protocol | Feature flag |
|--------|----------|--------------|
| `ocr/` | DocumentParser / OCR backend | `USE_UNLIMITED_OCR` |
| `normalizer/` | Normalizer | `USE_ML_NORMALIZER` |
| `quality/` | (scaffold) → use `image_quality/` | `USE_IMAGE_QUALITY_MODEL` |
| `image_quality/` | Document image quality (Phase 8) | `USE_IMAGE_QUALITY_MODEL` |
| `anomaly/` | (scaffold) → use `anomaly_detection/` | `USE_ANOMALY_MODEL` |
| `anomaly_detection/` | Lab anomaly (Phase 7) | `USE_ANOMALY_MODEL` / `USE_OUTLIER_MODEL` |
| `retrieval/` | Retriever | `USE_EMBEDDING_SEARCH` |
| `risk/` → use `risk_prediction/` | Disease risk (Phase 4) | `USE_RISK_MODEL` |
| `forecasting/` | Biomarker forecast (Phase 5) | `USE_FORECAST_MODEL` |
| `health_score/` | Personalized health score (Phase 6) | `USE_HEALTH_SCORE_MODEL` |
| `explainability/` | Shared SHAP / attribution helpers | (used by Phase 6+) |
| `platform/` | Audit · unified benchmark · e2e · experiment tracking (Phase 9) | `ML_EXPERIMENT_TRACKING` (default 0) |

Artifacts for phases 2–8 may be generated under each package (`artifacts/`). Live default traffic uses `services/ai-service/adapters/*` with flags off.

**Platform hardening:**

```bash
python models/platform/audit.py
python models/platform/benchmark_suite.py
python models/platform/e2e_validate.py
```

See [docs/MODEL_REGISTRY.md](../docs/MODEL_REGISTRY.md), [docs/benchmark_complete.md](../docs/benchmark_complete.md), [docs/KNOWN_LIMITATIONS.md](../docs/KNOWN_LIMITATIONS.md).
