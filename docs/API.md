# API notes

**Existing APIs unchanged in Phases 4–6.**

### Disease risk (Phase 4) — registry only

```python
from services.ai_service.core.registry import get_risk_predictor
result = get_risk_predictor().predict(metrics)
# result.risk_score, risk_band, drivers, summary_*, conditions, disclaimer_en
```

Enable with `USE_RISK_MODEL=1` (or `USE_DISEASE_RISK_MODEL=1`) and restart ai-service.

### Biomarker forecast (Phase 5) — registry only

```python
from services.ai_service.core.registry import get_biomarker_forecaster
batch = get_biomarker_forecaster().forecast(
    history,  # list of metrics with date_of_test
    horizon_days=180,
    demographics={"age": 48, "sex": "female"},
)
# batch.forecasts[*].predicted_value, lower_bound, upper_bound, confidence, trend_direction
```

Enable with `USE_FORECAST_MODEL=1` and restart ai-service. No new public HTTP route.

### Health score (Phase 6) — registry only

```python
from services.ai_service.core.registry import get_health_scorer
result = get_health_scorer().score(metrics)
# result.score, level, risk_band, confidence
# result.positive_contributors, negative_contributors, top_features, global_importance
```

Enable with `USE_HEALTH_SCORE_MODEL=1` and restart ai-service. No new public HTTP route.

### Lab anomaly (Phase 7) — existing `/anomaly/detect` (schema unchanged)

```python
from services.ai_service.core.registry import get_anomaly_detector
result = get_anomaly_detector().detect(test_name, data_points, unit=unit)
# same fields: is_anomaly, anomaly_score, trend, summary_*
# ML path methods: method like ml_anomaly:isolation_forest
```

Enable with `USE_ANOMALY_MODEL=1` (or `USE_OUTLIER_MODEL=1`). Default remains statistical.

### Image quality (Phase 8) — used by existing `/parse` (schema unchanged)

```python
from services.ai_service.core.registry import get_quality_checker
q = get_quality_checker().check(file_bytes, mime_type)
# q.ok, q.score, q.reasons; metadata: quality_score, category, recommendation
```

Default passthrough always `ok=True`. Enable with `USE_IMAGE_QUALITY_MODEL=1`.

### Platform validation (Phase 9) — offline only

No new public HTTP routes. Registry and HTTP schemas for Phases 1–8 are **stable**.

Ops: `GET /health` may expose `ml_feature_flags` for flag dump (read-only observability).