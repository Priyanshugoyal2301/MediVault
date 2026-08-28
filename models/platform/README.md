# ML Platform tooling (Phase 9)

## Commands

```bash
python models/platform/audit.py
python models/platform/benchmark_suite.py
python models/platform/e2e_validate.py
```

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
