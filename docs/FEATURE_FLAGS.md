# Feature Flag Reference

| Variable | Default | Effect when **1** | Rollback |
|----------|---------|-------------------|----------|
| `USE_UNLIMITED_OCR` | `0` | Unlimited-OCR + legacy fallback | `0` → legacy only |
| `USE_ML_NORMALIZER` | `0` | ML normalizer + alias fallback | `0` → alias rules |
| `USE_EMBEDDING_SEARCH` | `0` | Semantic + BM25 fallback | `0` → BM25 |
| `MEDIVAULT_USE_DENSE` | `0` | Alias → embedding search | unset |
| `USE_RISK_MODEL` | `0` | Disease risk ML | `0` → unavailable |
| `USE_DISEASE_RISK_MODEL` | `0` | Alias of risk | unset |
| `USE_FORECAST_MODEL` | `0` | Biomarker forecast ML | `0` → unavailable |
| `USE_HEALTH_SCORE_MODEL` | `0` | Health score + SHAP | `0` → unavailable |
| `USE_ANOMALY_MODEL` | `0` | Isolation Forest anomaly | `0` → statistical |
| `USE_OUTLIER_MODEL` | `0` | Alias of anomaly | unset |
| `USE_IMAGE_QUALITY_MODEL` | `0` | Pre-OCR quality gate | `0` → passthrough |

## Backend knobs (examples)

See `.env.example` for: `NORMALIZER_BACKEND`, `RETRIEVAL_*`, `RISK_MODEL_BACKEND`, `FORECAST_MODEL_BACKEND`, `HEALTH_SCORE_BACKEND`, `ANOMALY_MODEL_BACKEND`, `IMAGE_QUALITY_BACKEND`, Unlimited-OCR and tracking vars.

## Experiment tracking

| Variable | Default | Meaning |
|----------|---------|---------|
| `ML_EXPERIMENT_TRACKING` | `0` | Enable MLflow/W&B logging |
| `ML_EXPERIMENT_BACKEND` | `none` | `mlflow` \| `wandb` \| `none` |

**Restart ai-service after flag changes** (registry is process-cached).
