# models/health_score — Personalized Health Score + XAI (Phase 6)

## Status

| Flag | Path |
|------|------|
| `USE_HEALTH_SCORE_MODEL=0` (default) | Unavailable scorer |
| `USE_HEALTH_SCORE_MODEL=1` | ML score + SHAP explain + fallback |

## Architecture

| Role | Model |
|------|-------|
| Primary | XGBoost Regressor |
| Fallback | LightGBM Regressor |
| Baseline | Linear / Ridge |

Explainability: `models/explainability` (SHAP TreeExplainer + fallback attributions).

## Safety

Score is an orientation estimate — **never a diagnosis**. Mandatory disclaimer.

## Commands

```bash
python models/health_score/train.py
python models/health_score/evaluate.py
```
