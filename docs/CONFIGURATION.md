# CONFIGURATION — ML feature flags

| Variable | Default | Meaning |
|----------|---------|---------|
| `USE_UNLIMITED_OCR` | `0` | Unlimited OCR |
| `USE_ML_NORMALIZER` | `0` | ML test-name normalizer |
| `USE_EMBEDDING_SEARCH` | `0` | Semantic retrieval |
| `USE_RISK_MODEL` | `0` | Disease risk ML |
| `USE_DISEASE_RISK_MODEL` | `0` | Alias for `USE_RISK_MODEL` |
| `RISK_MODEL_BACKEND` | `auto` | auto\|xgboost\|lightgbm\|logistic\|sklearn_gb |
| `USE_FORECAST_MODEL` | `0` | Longitudinal biomarker forecasting ML |
| `FORECAST_MODEL_BACKEND` | `auto` | auto\|lightgbm\|xgboost\|linear\|sklearn_gb\|lstm\|temporal_transformer |
| `FORECAST_HORIZON_DAYS` | `180` | Default forecast horizon |
| `USE_HEALTH_SCORE_MODEL` | `0` | Personalized health score + SHAP |
| `HEALTH_SCORE_BACKEND` | `auto` | auto\|xgboost\|lightgbm\|linear\|sklearn_gb |
| `USE_ANOMALY_MODEL` | `0` | ML lab anomaly detection |
| `USE_OUTLIER_MODEL` | `0` | Alias for `USE_ANOMALY_MODEL` |
| `ANOMALY_MODEL_BACKEND` | `auto` | auto\|isolation_forest\|lof\|robust_z\|autoencoder\|ocsvm |
| `USE_IMAGE_QUALITY_MODEL` | `0` | Pre-OCR document image quality ML |
| `IMAGE_QUALITY_BACKEND` | `auto` | auto\|mobilenet_v3\|efficientnet_lite0\|opencv_rules\|feature_ml |
| `IMAGE_QUALITY_TRAIN_PIXELS` | `0` | Pixel CNN train when 1 |
| `RETRIEVAL_EMBEDDING_BACKEND` | `auto` | Retrieval embed backend |
| `RETRIEVAL_ALLOW_HF` | `0` | HF retrieval weights |
| `ML_EXPERIMENT_TRACKING` | `0` | Optional MLflow/W&B (Phase 9) |
| `ML_EXPERIMENT_BACKEND` | `none` | none \| mlflow \| wandb |

See also Unlimited-OCR / normalizer / retrieval env blocks in `.env.example` and [FEATURE_FLAGS.md](./FEATURE_FLAGS.md).

Artifact / dataset paths are env-overridable per package (`*_ARTIFACTS_DIR`, `*_PATH`) — no production hardcoding required.

**After flag changes:** restart ai-service.
