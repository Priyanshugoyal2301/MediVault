# Developer Guide — Medical Test Normalizer (Phase 2)

1. Default: `USE_ML_NORMALIZER=0` (rules).  
2. Train offline: `python models/normalizer/train.py`  
3. Smoke: `python -m models.normalizer.infer_cli HGB SGPT --json`  
4. Enable ML: `USE_ML_NORMALIZER=1` then **restart** ai-service.  
5. Tests: `python -m pytest tests/phase2 -q`  
6. Do not start Phase 3 until validation accepted.
