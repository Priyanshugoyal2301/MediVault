# System Design — Risk / Forecast / Health Score

```
Caller (internal) → get_risk_predictor()
  flag off: UnavailableRiskPredictor
  flag on:  DiseaseRiskEngine → RiskPredictionResult + non-dx disclaimer

Caller (internal) → get_biomarker_forecaster()
  USE_FORECAST_MODEL=0: UnavailableBiomarkerForecaster
  USE_FORECAST_MODEL=1: BiomarkerForecastEngine
       → BiomarkerForecastBatch (value, PI, confidence, trend) + disclaimer

Caller (internal) → get_health_scorer()
  USE_HEALTH_SCORE_MODEL=0: UnavailableHealthScorer
  USE_HEALTH_SCORE_MODEL=1: HealthScoreEngine + SHAP explain
       → HealthScoreResult (score, band, confidence, ± contributors)

Caller → POST /anomaly/detect (schema unchanged)
  → get_anomaly_detector()
  USE_ANOMALY_MODEL=0: StatisticalAnomalyDetector
  USE_ANOMALY_MODEL=1: LabAnomalyEngine (Isolation Forest) + stats fallback
       → language: anomalous laboratory pattern only

Caller → POST /parse (schema unchanged)
  → get_quality_checker()
  USE_IMAGE_QUALITY_MODEL=0: PassThrough (always ok)
  USE_IMAGE_QUALITY_MODEL=1: ImageQualityEngine (MobileNetV3 / OpenCV)
       → if not ok: empty values (existing soft fail)
       → else: DocumentParser (OCR path unchanged)
```

No public response schema changes. No frontend hooks.

### Platform tools (Phase 9)

Offline only — do not change HTTP APIs:

```
audit.py → reproducibility_audit.json
benchmark_suite.py → benchmark_complete.md
e2e_validate.py → platform_e2e_validation.json (flags-off safe path)
experiment_tracking.py → optional MLflow/W&B (ML_EXPERIMENT_TRACKING=0)
```
