"""Config for personalized health score."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


class HealthScoreConfigError(ValueError):
    pass


def load_config(path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = path or (_ROOT / "config.yaml")
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    if os.getenv("HEALTH_SCORE_BACKEND"):
        data["active_backend"] = os.getenv("HEALTH_SCORE_BACKEND")
    if os.getenv("HEALTH_SCORE_ARTIFACTS_DIR"):
        data.setdefault("paths", {})["artifacts"] = os.getenv(
            "HEALTH_SCORE_ARTIFACTS_DIR"
        )

    data.setdefault("model_name", "personalized_health_score")
    data.setdefault("version", "6.0.0")
    data.setdefault("primary_architecture", "xgboost")
    data.setdefault("fallback_architecture", "lightgbm")
    data.setdefault("baseline_architecture", "linear_regression")
    data.setdefault("active_backend", "auto")
    data.setdefault("seed", 42)
    data.setdefault("top_k_explain", 8)
    _repo = _ROOT.parents[1]
    data.setdefault(
        "paths",
        {
            "train_data": str((_repo / "datasets" / "health_score").as_posix()),
            "artifacts": str((_ROOT / "artifacts").as_posix()),
            "evaluation_out": str(
                (
                    _repo
                    / "datasets"
                    / "evaluation"
                    / "health_score_phase6_latest.json"
                ).as_posix()
            ),
        },
    )

    if validate:
        be = (data.get("active_backend") or "auto").lower()
        allowed = {
            "auto",
            "xgboost",
            "xgb",
            "lightgbm",
            "lgbm",
            "linear",
            "linear_regression",
            "baseline",
            "sklearn_gb",
        }
        if be not in allowed:
            raise HealthScoreConfigError(f"Invalid HEALTH_SCORE_BACKEND: {be}")
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
