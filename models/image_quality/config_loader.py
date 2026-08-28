"""Config loader for image quality."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


class ImageQualityConfigError(ValueError):
    pass


def load_config(path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = path or (_ROOT / "config.yaml")
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    if os.getenv("IMAGE_QUALITY_BACKEND"):
        data["active_backend"] = os.getenv("IMAGE_QUALITY_BACKEND")
    if os.getenv("IMAGE_QUALITY_ARTIFACTS_DIR"):
        data.setdefault("paths", {})["artifacts"] = os.getenv("IMAGE_QUALITY_ARTIFACTS_DIR")

    data.setdefault("model_name", "document_image_quality")
    data.setdefault("version", "8.0.0")
    data.setdefault("primary_architecture", "mobilenet_v3")
    data.setdefault("fallback_architecture", "efficientnet_lite0")
    data.setdefault("baseline_architecture", "opencv_rules")
    data.setdefault("active_backend", "auto")
    data.setdefault("seed", 42)
    data.setdefault("epochs", 3)
    data.setdefault("ready_threshold_score", 70)
    data.setdefault("label_threshold", 0.45)
    _repo = _ROOT.parents[1]
    data.setdefault(
        "paths",
        {
            "train_data": str((_repo / "datasets" / "image_quality").as_posix()),
            "artifacts": str((_ROOT / "artifacts").as_posix()),
            "evaluation_out": str(
                (
                    _repo
                    / "datasets"
                    / "evaluation"
                    / "image_quality_phase8_latest.json"
                ).as_posix()
            ),
        },
    )

    if validate:
        be = (data.get("active_backend") or "auto").lower()
        allowed = {
            "auto",
            "mobilenet",
            "mobilenet_v3",
            "mobilenetv3",
            "efficientnet",
            "efficientnet_lite0",
            "efficientnet_b0",
            "opencv",
            "opencv_rules",
            "baseline",
            "sklearn",
            "feature_ml",
        }
        if be not in allowed:
            raise ImageQualityConfigError(f"Invalid IMAGE_QUALITY_BACKEND: {be}")
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
