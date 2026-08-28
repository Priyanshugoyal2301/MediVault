"""Config for biomarker forecasting."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


class ForecastConfigError(ValueError):
    pass


def load_config(path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = path or (_ROOT / "config.yaml")
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    if os.getenv("FORECAST_MODEL_BACKEND"):
        data["active_backend"] = os.getenv("FORECAST_MODEL_BACKEND")
    if os.getenv("FORECAST_HORIZON_DAYS"):
        data["default_horizon_days"] = int(os.getenv("FORECAST_HORIZON_DAYS", "180"))
    if os.getenv("FORECAST_ARTIFACTS_DIR"):
        data.setdefault("paths", {})["artifacts"] = os.getenv("FORECAST_ARTIFACTS_DIR")

    data.setdefault("model_name", "biomarker_forecaster")
    data.setdefault("version", "5.0.0")
    data.setdefault("primary_architecture", "lightgbm")
    data.setdefault("fallback_architecture", "xgboost")
    data.setdefault("baseline_architecture", "linear_regression")
    data.setdefault(
        "future_architectures",
        ["temporal_transformer", "lstm"],
    )
    data.setdefault("active_backend", "auto")  # auto|lightgbm|xgboost|linear|sklearn_gb
    data.setdefault("default_horizon_days", 180)
    data.setdefault("seed", 42)
    data.setdefault("min_history_points", 2)
    data.setdefault("pi_z", 1.645)  # ~90% normal PI
    # _ROOT = models/forecasting → parents[1] = repo root (MediVault)
    _repo = _ROOT.parents[1]
    data.setdefault(
        "paths",
        {
            "train_data": str((_repo / "datasets" / "forecasting").as_posix()),
            "artifacts": str((_ROOT / "artifacts").as_posix()),
            "evaluation_out": str(
                (
                    _repo
                    / "datasets"
                    / "evaluation"
                    / "forecast_phase5_latest.json"
                ).as_posix()
            ),
        },
    )

    if validate:
        be = (data.get("active_backend") or "auto").lower()
        allowed = {
            "auto",
            "lightgbm",
            "lgbm",
            "xgboost",
            "xgb",
            "linear",
            "linear_regression",
            "baseline",
            "sklearn_gb",
            "lstm",
            "temporal_transformer",
        }
        if be not in allowed:
            raise ForecastConfigError(f"Invalid FORECAST_MODEL_BACKEND: {be}")
    return data


def artifacts_dir(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config(validate=False)
    p = Path(cfg["paths"]["artifacts"])
    if not p.is_absolute():
        p = (_ROOT / p).resolve()
    return p


def resolve_path(path_str: str | Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (_ROOT / p).resolve()
