"""Train disease risk models (config-driven)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    import conftest  # noqa: F401
except Exception:
    pass


def train(config_path: Path | None = None, backend: str | None = None) -> Path:
    from models.risk_prediction.config_loader import load_config
    from models.risk_prediction.dataset import ensure_dataset_files
    from models.risk_prediction.infer import DiseaseRiskEngine
    from models.risk_prediction.config_loader import resolve_path
    from models.risk_prediction.classifiers import describe_backends

    cfg = load_config(config_path, validate=True)
    if backend:
        cfg["active_backend"] = backend
    ensure_dataset_files(resolve_path(cfg["paths"]["train_data"]))
    eng = DiseaseRiskEngine(cfg, auto_train_if_missing=False)
    art = eng.train()
    print(
        json.dumps(
            {
                "artifacts": str(art),
                "backend": eng.backend_name,
                "available_backends": describe_backends(),
                "diseases": list(eng.models.keys()),
            },
            indent=2,
        )
    )
    return art


def main() -> None:
    p = argparse.ArgumentParser(description="Train disease risk models")
    p.add_argument("--config", type=Path, default=None)
    p.add_argument(
        "--backend",
        default=None,
        help="auto|xgboost|lightgbm|logistic|sklearn_gb",
    )
    args = p.parse_args()
    train(args.config, args.backend)


if __name__ == "__main__":
    main()
