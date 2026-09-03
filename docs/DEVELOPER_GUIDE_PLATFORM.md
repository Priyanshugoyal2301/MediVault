# Developer Guide — Platform Hardening (Phase 9)

## Goals

Reproducibility, unified benchmarks, docs, deploy checklist — **no new models**.

## Commands

```bash
# Repo root
python models/platform/audit.py
python models/platform/benchmark_suite.py
python models/platform/e2e_validate.py
pytest tests/phase9 -q
```

## Experiment tracking

```python
from models.platform.experiment_tracking import experiment_run, tracking_enabled

assert tracking_enabled() is False  # default
# ML_EXPERIMENT_TRACKING=1 ML_EXPERIMENT_BACKEND=mlflow
with experiment_run("train_risk") as exp:
    exp.log_params({"backend": "xgboost"})
    exp.log_metrics({"auc": 0.9})
```

## Conftest for standalone scripts

Platform tools import `conftest` so `services.ai_service` resolves to hyphenated folders. Always run from **repo root**.

## Deliverables map

| File | Purpose |
|------|---------|
| `docs/benchmark_complete.md` | Unified metrics |
| `validation/platform-validation.md` | Gate verdict |
| `docs/MODEL_REGISTRY.md` | Model inventory |
| `docs/KNOWN_LIMITATIONS.md` | Platform limits |
| `docs/DEPLOYMENT.md` | Deploy notes |

## Do not

- Add ML models  
- Change public APIs or frontend  
- Enable tracking / ML flags in production by default  
