"""Config loader for anomaly detection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


class AnomalyConfigError(ValueError):
    pass


def load_config(path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = path or (_ROOT / "config.yaml")
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    if os.getenv("ANOMALY_MODEL_BACKEND"):
        data["active_backend"] = os.getenv("ANOMALY_MODEL_BACKEND")
    if os.getenv("ANOMALY_ARTIFACTS_DIR"):
        data.setdefault("paths", {})["artifacts"] = os.getenv("ANOMALY_ARTIFACTS_DIR")
    if os.getenv("ANOMALY_CONTAMINATION"):
        data["contamination"] = float(os.getenv("ANOMALY_CONTAMINATION", "0.08"))

    data.setdefault("model_name", "lab_anomaly_detector")
    data.setdefault("version", "7.0.0")
    data.setdefault("primary_architecture", "isolation_forest")
    data.setdefault("fallback_architecture", "lof")
    data.setdefault("baseline_architecture", "robust_z")
    data.setdefault("future_architectures", ["autoencoder", "one_class_svm"])
    data.setdefault("active_backend", "auto")
    data.setdefault("contamination", 0.08)
    data.setdefault("score_threshold", 0.55)
    data.setdefault("seed", 42)
    _repo = _ROOT.parents[1]
    data.setdefault(
        "paths",
        {
            "train_data": str((_repo / "datasets" / "anomaly_detection").as_posix()),
            "artifacts": str((_ROOT / "artifacts").as_posix()),
            "evaluation_out": str(
                (
                    _repo
                    / "datasets"
                    / "evaluation"
                    / "anomaly_phase7_latest.json"
                ).as_posix()
            ),
        },
    )

    if validate:
        be = (data.get("active_backend") or "auto").lower()
        allowed = {
            "auto",
            "isolation_forest",
            "iforest",
            "if",
            "lof",
            "local_outlier_factor",
            "robust_z",
            "zscore",
            "baseline",
            "autoencoder",
            "ocsvm",
            "one_class_svm",
        }
        if be not in allowed:
            raise AnomalyConfigError(f"Invalid ANOMALY_MODEL_BACKEND: {be}")
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
