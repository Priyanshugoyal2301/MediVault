# Developer guide — Health score

1. Keep `USE_HEALTH_SCORE_MODEL=0` for demos.  
2. Train: `python models/health_score/train.py`  
3. Eval: `python models/health_score/evaluate.py`  
4. Optional: `pip install shap` for TreeExplainer (fallback works without).  
5. Smoke: enable flag, `get_health_scorer().score(metrics)`  
6. Never present score as a diagnosis.  
7. Reuse `models/explainability` for other models’ local attributions.
