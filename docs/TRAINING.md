# Training

## Platform (Phase 9) — no new models

Optional experiment logging (default off):

```python
from models.platform.experiment_tracking import experiment_run
with experiment_run("my_run") as exp:
    exp.log_params({"seed": 42})
    exp.log_metrics({"mae": 1.2})
```

Set `ML_EXPERIMENT_TRACKING=1` and `ML_EXPERIMENT_BACKEND=mlflow|wandb` only for offline research runs.

## Phase 8 Document Image Quality

```bash
python models/image_quality/train.py
python models/image_quality/train.py --backend mobilenet_v3
python models/image_quality/train.py --backend efficientnet_lite0
python models/image_quality/train.py --backend opencv_rules
python models/image_quality/evaluate.py
```

Optional: `pip install torch torchvision pillow pypdfium2`  
Pixel CNN: `IMAGE_QUALITY_TRAIN_PIXELS=1`

## Phase 7 Lab Anomaly Detection

```bash
python models/anomaly_detection/train.py
python models/anomaly_detection/train.py --backend isolation_forest
python models/anomaly_detection/train.py --backend lof
python models/anomaly_detection/evaluate.py
```

## Phase 6 Personalized Health Score

```bash
python models/health_score/train.py
python models/health_score/train.py --backend xgboost
python models/health_score/train.py --backend lightgbm
python models/health_score/evaluate.py
```

Optional: `pip install xgboost lightgbm shap`

## Phase 5 Biomarker Forecasting

```bash
python models/forecasting/train.py
python models/forecasting/train.py --backend lightgbm
python models/forecasting/train.py --backend xgboost
python models/forecasting/evaluate.py
```

Optional: `pip install lightgbm xgboost` (falls back to sklearn / linear if missing).

## Phase 4 Disease Risk

```bash
python models/risk_prediction/train.py
python models/risk_prediction/train.py --backend xgboost
python models/risk_prediction/evaluate.py
```

Optional: `pip install xgboost lightgbm`

## Phase 3 Retrieval / Phase 2 Normalizer / Phase 1 OCR

See respective `models/*/README.md`.
