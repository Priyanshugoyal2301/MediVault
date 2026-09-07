# ML Platform tooling (Phase 9)

## Commands

```bash
python models/platform/audit.py
python models/platform/benchmark_suite.py
python models/platform/e2e_validate.py

# Guarded offline auto-train (recommended)
python models/platform/safe_train.py
# Guard decisions only (no train):
python models/platform/train_guard.py
```

`safe_train.py` runs a **pre-training protector** that:

- Keeps all production `USE_*` ML flags **off** for the training process
- Blocks HF / Unlimited-OCR local-weight downloads
- Picks offline-safe backends automatically (e.g. `char_tfidf`, XGBoost/LightGBM when installed)
- Skips Phase 1 OCR (no offline weight training)
- Then trains + evaluates Phases 2–8

Reports: `datasets/evaluation/safe_train_guard_report.json`, `safe_train_run_report.json`


## Experiment tracking (optional)

```bash
# disabled by default
ML_EXPERIMENT_TRACKING=0

# MLflow
ML_EXPERIMENT_TRACKING=1
ML_EXPERIMENT_BACKEND=mlflow
MLFLOW_TRACKING_URI=file:./mlruns

# W&B
ML_EXPERIMENT_TRACKING=1
ML_EXPERIMENT_BACKEND=wandb
WANDB_MODE=offline
```

```python
from models.platform.experiment_tracking import experiment_run

with experiment_run("train_risk", {"backend": "xgboost"}) as exp:
    exp.log_metrics({"auc": 0.9})
```
