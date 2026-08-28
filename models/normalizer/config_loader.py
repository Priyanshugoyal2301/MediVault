"""Load models/normalizer/config.yaml + environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


class NormalizerConfigError(ValueError):
    pass


def _default_config_path() -> Path:
    return _ROOT / "config.yaml"


def load_config(path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = path or _default_config_path()
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    if os.getenv("NORMALIZER_BACKEND"):
        data["active_backend"] = os.getenv("NORMALIZER_BACKEND")
    if os.getenv("NORMALIZER_ARTIFACTS_DIR"):
        data.setdefault("paths", {})["artifacts"] = os.getenv("NORMALIZER_ARTIFACTS_DIR")
    if os.getenv("NORMALIZER_MIN_CONFIDENCE"):
        data["min_confidence"] = float(os.getenv("NORMALIZER_MIN_CONFIDENCE", "0.55"))
    if os.getenv("NORMALIZER_ALLOW_HF"):
        data["allow_hf_download"] = os.getenv("NORMALIZER_ALLOW_HF", "0") in (
            "1",
            "true",
            "True",
            "yes",
        )
    if os.getenv("MODERNBERT_MODEL_ID"):
        data["modernbert_model_id"] = os.getenv("MODERNBERT_MODEL_ID")
    if os.getenv("CLINICALBERT_MODEL_ID"):
        data["clinicalbert_model_id"] = os.getenv("CLINICALBERT_MODEL_ID")

    data.setdefault("model_name", "medical_test_normalizer")
    data.setdefault("version", "2.0.0")
    data.setdefault("primary_architecture", "modernbert")
    data.setdefault("fallback_architecture", "clinicalbert")
    data.setdefault("offline_architecture", "char_tfidf")
    data.setdefault("active_backend", "char_tfidf")
    data.setdefault("min_confidence", 0.55)
    data.setdefault("allow_hf_download", False)
    data.setdefault("device", "cpu")
    data.setdefault(
        "paths",
        {
            "train_data": str(
                (_ROOT.parents[2] / "datasets" / "test_normalization").as_posix()
            ),
            "artifacts": str((_ROOT / "artifacts").as_posix()),
            "evaluation_out": str(
                (
                    _ROOT.parents[2]
                    / "datasets"
                    / "evaluation"
                    / "normalizer_phase2_latest.json"
                ).as_posix()
            ),
        },
    )

    if validate:
        validate_config(data)
    return data


def validate_config(cfg: dict[str, Any]) -> None:
    backend = (cfg.get("active_backend") or "").lower()
    allowed = {
        "char_tfidf",
        "tfidf",
        "sklearn",
        "offline",
        "modernbert",
        "clinicalbert",
        "primary",
        "fallback_hf",
    }
    if backend not in allowed:
        raise NormalizerConfigError(
            f"Invalid NORMALIZER_BACKEND / active_backend: {backend}"
        )
    mc = float(cfg.get("min_confidence") or 0)
    if not 0.0 <= mc <= 1.0:
        raise NormalizerConfigError("min_confidence must be in [0, 1]")


def artifacts_dir(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config(validate=False)
    p = Path(cfg["paths"]["artifacts"])
    if not p.is_absolute():
        p = (_ROOT / p).resolve()
    return p
