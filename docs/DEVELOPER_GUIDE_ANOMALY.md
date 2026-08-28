# Developer guide — Anomaly detection

1. Default `USE_ANOMALY_MODEL=0` keeps statistical path.  
2. Train: `python models/anomaly_detection/train.py`  
3. Eval: `python models/anomaly_detection/evaluate.py`  
4. Smoke: `USE_ANOMALY_MODEL=1` + `get_anomaly_detector().detect(...)`  
5. Never describe results as disease diagnoses.  
6. Multi-marker: `LabAnomalyEngine().score_profile(metrics)`.
