"""Config loader for disease risk models."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


class RiskConfigError(ValueError):
    pass


def load_config(path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = path or (_ROOT / "config.yaml")
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    if os.getenv("RISK_MODEL_BACKEND"):
        data["active_backend"] = os.getenv("RISK_MODEL_BACKEND")
    if os.getenv("RISK_ARTIFACTS_DIR"):
        data.setdefault("paths", {})["artifacts"] = os.getenv("RISK_ARTIFACTS_DIR")
    if os.getenv("RISK_MIN_CONFIDENCE"):
        data["min_confidence"] = float(os.getenv("RISK_MIN_CONFIDENCE", "0.5"))

    data.setdefault("model_name", "disease_risk_predictor")
    data.setdefault("version", "4.0.0")
    data.setdefault("primary_architecture", "xgboost")
    data.setdefault("fallback_architecture", "lightgbm")
    data.setdefault("baseline_architecture", "logistic_regression")
    data.setdefault("active_backend", "auto")  # auto|xgboost|lightgbm|logistic
    data.setdefault("min_confidence", 0.45)
    data.setdefault("seed", 42)
    data.setdefault(
        "thresholds",
        {"low": 0.33, "moderate": 0.66},  # probability → band
    )
    data.setdefault(
        "paths",
        {
            "train_data": str(
                (_ROOT.parents[2] / "datasets" / "risk_prediction").as_posix()
            ),
            "artifacts": str((_ROOT / "artifacts").as_posix()),
            "evaluation_out": str(
                (
                    _ROOT.parents[2]
                    / "datasets"
                    / "evaluation"
                    / "risk_phase4_latest.json"
                ).as_posix()
            ),
        },
    )

    if validate:
        validate_config(data)
    return data


def validate_config(cfg: dict[str, Any]) -> None:
    be = (cfg.get("active_backend") or "auto").lower()
    if be not in {
        "auto",
        "xgboost",
        "xgb",
        "lightgbm",
        "lgbm",
        "logistic",
        "logistic_regression",
        "baseline",
        "sklearn_gb",
    }:
        raise RiskConfigError(f"Invalid RISK_MODEL_BACKEND: {be}")


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
    # config paths are relative to models/risk_prediction/
    return (_ROOT / p).resolve()
