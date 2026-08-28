# ML Architecture (MediVault)

```
OCR (Phase 1/1A)     → flag USE_UNLIMITED_OCR
Normalizer (Phase 2) → flag USE_ML_NORMALIZER
Retrieval (Phase 3)  → flag USE_EMBEDDING_SEARCH
Risk (Phase 4)       → flag USE_RISK_MODEL / USE_DISEASE_RISK_MODEL
  backends: XGBoost | LightGBM | Logistic | sklearn_gb
  outputs: per-condition probability, category, confidence, drivers
  language: non-diagnostic only

Forecast (Phase 5)   → flag USE_FORECAST_MODEL
  backends: LightGBM | XGBoost | Linear | LSTM/TT stubs
  outputs: predicted value, PI, confidence, trend, horizon
  language: forecast estimate only — never diagnosis

Health score (Phase 6) → flag USE_HEALTH_SCORE_MODEL
  backends: XGBoost | LightGBM | Linear
  explain: SHAP (models/explainability) + fallback
  outputs: score 0–100, band, confidence, top ± contributors
  language: health score estimate only — never diagnosis

Anomaly (Phase 7)    → flag USE_ANOMALY_MODEL / USE_OUTLIER_MODEL
  backends: Isolation Forest | LOF | Robust Z | AE/OCSVM stubs
  outputs: anomaly score/prob, category, contributors, confidence
  language: "Anomalous laboratory pattern detected" — never diagnosis
  default path: statistical z/CUSUM monitor

Image quality (Phase 8) → flag USE_IMAGE_QUALITY_MODEL
  backends: MobileNetV3-Small | EfficientNet Lite0/B0 | OpenCV rules
  outputs: quality score, category, problems, confidence, OCR recommendation
  default path: passthrough (always ok — OCR unchanged)

Platform (Phase 9) → tools only (no new models)
  audit · benchmark_suite · e2e_validate · experiment_tracking (default off)
  registry: docs/MODEL_REGISTRY.md · unified: benchmark_complete.md
```

All paths wire through `services/ai-service/core/registry.py` with production-safe defaults.
