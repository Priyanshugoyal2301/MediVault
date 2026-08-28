# Architecture — Personalized Health Score (Phase 6)

```
Caller (internal) → get_health_scorer()
  USE_HEALTH_SCORE_MODEL=0: UnavailableHealthScorer
  USE_HEALTH_SCORE_MODEL=1: HealthScoreEngine
       features → XGBoost|LightGBM|Linear
       → score, band, confidence
       → models/explainability (SHAP)
       → HealthScoreResult + positive/negative factors
```

No existing public HTTP routes. No frontend hooks.

### Sequence

```
User metrics list
  → MLHealthScorer.score
  → HealthScoreEngine.score
  → feature_engineering.metrics_to_feature_dict
  → model.predict
  → explain_tree_model (SHAP)
  → HealthScoreResult
```
