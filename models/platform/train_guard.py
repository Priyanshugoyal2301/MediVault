"""Pre-training guard — automatic safe decisions before any train.py runs.

Policy (best-practice defaults):
  - Never flip production USE_* ML flags to on
  - Prefer offline-safe backends (no HF / no multi-GB OCR weights)
  - Keep experiment tracking off unless explicitly offline
  - Only train phases that have real offline train.py + synthetic data
  - Block if critical datasets, disk, or repo layout are missing
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Production flags that must remain off during guarded auto-train
_PRODUCTION_FLAGS = (
    "USE_UNLIMITED_OCR",
    "USE_ML_NORMALIZER",
    "USE_EMBEDDING_SEARCH",
    "MEDIVAULT_USE_DENSE",
    "USE_RISK_MODEL",
    "USE_DISEASE_RISK_MODEL",
    "USE_FORECAST_MODEL",
    "USE_HEALTH_SCORE_MODEL",
    "USE_ANOMALY_MODEL",
    "USE_OUTLIER_MODEL",
    "USE_IMAGE_QUALITY_MODEL",
)

_HF_OPT_INS = (
    "NORMALIZER_ALLOW_HF",
    "RETRIEVAL_ALLOW_HF",
    "UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS",
    "UNLIMITED_OCR_ALLOW_LOCAL_DOWNLOAD",
)

_MIN_FREE_MB = 400


@dataclass
class PhasePlan:
    id: str
    phase: str
    train_script: str
    evaluate_script: str
    backend: str | None
    dataset_globs: list[str]
    skip_reason: str | None = None


@dataclass
class GuardReport:
    ok: bool
    decisions: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    env_overrides: dict[str, str] = field(default_factory=dict)
    phases: list[PhasePlan] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}


def _pick_boosting_backend(prefer: str = "xgboost") -> str:
    """Prefer tree boosters when installed; fall back to sklearn."""
    order = [prefer]
    if prefer == "xgboost":
        order += ["lightgbm", "sklearn_gb", "logistic"]
    elif prefer == "lightgbm":
        order += ["xgboost", "sklearn_gb", "linear"]
    else:
        order += ["xgboost", "lightgbm", "sklearn_gb"]

    for name in order:
        if name in ("xgboost",) and _has_module("xgboost"):
            return "xgboost"
        if name in ("lightgbm",) and _has_module("lightgbm"):
            return "lightgbm"
        if name in ("sklearn_gb", "logistic", "linear"):
            return "sklearn_gb" if name == "sklearn_gb" else name
    return "sklearn_gb"


def _pick_image_backend() -> str:
    # Offline-safe first; torch CNNs only if torch is importable for training pixels
    if _has_module("torch") and _has_module("torchvision"):
        return "mobilenet_v3"
    if _has_module("sklearn"):
        return "feature_ml"
    return "opencv_rules"


def _check_disk(root: Path) -> tuple[bool, str]:
    usage = shutil.disk_usage(root)
    free_mb = usage.free / (1024 * 1024)
    if free_mb < _MIN_FREE_MB:
        return False, f"Only {free_mb:.0f} MB free (need ≥ {_MIN_FREE_MB} MB)"
    return True, f"{free_mb:.0f} MB free"


def build_guard_plan(*, enforce_offline: bool = True) -> GuardReport:
    report = GuardReport(ok=True)
    report.decisions["repo_root"] = str(_ROOT)
    report.decisions["policy"] = "offline_safe_auto_train"
    report.decisions["never_enable_production_flags"] = True

    # --- layout ---
    if not (_ROOT / "models").is_dir() or not (_ROOT / "datasets").is_dir():
        report.blockers.append("Repo root missing models/ or datasets/")
        report.ok = False
        return report

    disk_ok, disk_msg = _check_disk(_ROOT)
    report.decisions["disk"] = disk_msg
    if not disk_ok:
        report.blockers.append(disk_msg)
        report.ok = False

    # --- force safe env for this process ---
    overrides: dict[str, str] = {
        "ML_EXPERIMENT_TRACKING": "0",
        "ML_EXPERIMENT_BACKEND": "none",
        "NORMALIZER_ALLOW_HF": "0",
        "RETRIEVAL_ALLOW_HF": "0",
        "UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS": "0",
        "UNLIMITED_OCR_ALLOW_LOCAL_DOWNLOAD": "0",
        "USE_UNLIMITED_OCR": "0",
    }
    if enforce_offline:
        for flag in _PRODUCTION_FLAGS:
            overrides[flag] = "0"

    for key, val in overrides.items():
        prev = os.environ.get(key)
        if prev is not None and prev != val and _truthy(prev):
            report.warnings.append(
                f"Guard overrides {key}={prev!r} → {val!r} for this training process only"
            )
        os.environ[key] = val
    report.env_overrides = overrides

    # warn if operator had HF opt-ins in environment (we cleared them)
    for key in _HF_OPT_INS:
        if _truthy(os.environ.get(key)):
            report.warnings.append(f"{key} unexpectedly truthy after override")

    # --- dependency probes ---
    deps = {
        "numpy": _has_module("numpy"),
        "sklearn": _has_module("sklearn"),
        "xgboost": _has_module("xgboost"),
        "lightgbm": _has_module("lightgbm"),
        "torch": _has_module("torch"),
        "shap": _has_module("shap"),
    }
    report.decisions["dependencies"] = deps
    if not deps["numpy"] or not deps["sklearn"]:
        report.blockers.append("numpy and scikit-learn are required for offline training")
        report.ok = False

    risk_backend = _pick_boosting_backend("xgboost")
    forecast_backend = _pick_boosting_backend("lightgbm")
    health_backend = _pick_boosting_backend("xgboost")
    image_backend = _pick_image_backend()

    report.decisions["backends"] = {
        "normalizer": "char_tfidf",
        "retrieval": "char_tfidf",
        "risk_prediction": risk_backend,
        "forecasting": forecast_backend,
        "health_score": health_backend,
        "anomaly_detection": "isolation_forest",
        "image_quality": image_backend,
        "ocr": "SKIP — no offline train (external VLM)",
    }

    phases: list[PhasePlan] = [
        PhasePlan(
            id="normalizer",
            phase="2",
            train_script="models/normalizer/train.py",
            evaluate_script="models/normalizer/evaluate.py",
            backend="char_tfidf",
            dataset_globs=["datasets/test_normalization/*.jsonl"],
        ),
        PhasePlan(
            id="retrieval",
            phase="3",
            train_script="models/retrieval/train.py",
            evaluate_script="models/retrieval/evaluate.py",
            backend=None,  # train.py has no --backend; config + env decide
            dataset_globs=["datasets/retrieval/*.jsonl", "data/knowledge-base/*.txt"],
        ),
        PhasePlan(
            id="risk_prediction",
            phase="4",
            train_script="models/risk_prediction/train.py",
            evaluate_script="models/risk_prediction/evaluate.py",
            backend=risk_backend,
            dataset_globs=["datasets/risk_prediction/*.jsonl"],
        ),
        PhasePlan(
            id="forecasting",
            phase="5",
            train_script="models/forecasting/train.py",
            evaluate_script="models/forecasting/evaluate.py",
            backend=forecast_backend,
            dataset_globs=["datasets/forecasting/*.jsonl"],
        ),
        PhasePlan(
            id="health_score",
            phase="6",
            train_script="models/health_score/train.py",
            evaluate_script="models/health_score/evaluate.py",
            backend=health_backend,
            dataset_globs=["datasets/health_score/*.jsonl"],
        ),
        PhasePlan(
            id="anomaly_detection",
            phase="7",
            train_script="models/anomaly_detection/train.py",
            evaluate_script="models/anomaly_detection/evaluate.py",
            backend="isolation_forest",
            dataset_globs=["datasets/anomaly_detection/*.jsonl"],
        ),
        PhasePlan(
            id="image_quality",
            phase="8",
            train_script="models/image_quality/train.py",
            evaluate_script="models/image_quality/evaluate.py",
            backend=image_backend,
            dataset_globs=[],  # may synthesize on the fly
        ),
    ]

    # OCR explicitly skipped
    report.decisions["skipped"] = [
        {
            "id": "ocr",
            "phase": "1/1A",
            "reason": "Unlimited-OCR has no offline weight training; scaffold only",
        }
    ]

    for plan in phases:
        train_path = _ROOT / plan.train_script
        if not train_path.is_file():
            plan.skip_reason = f"missing {plan.train_script}"
            report.warnings.append(plan.skip_reason)
            continue
        missing_data = []
        for pattern in plan.dataset_globs:
            matches = list(_ROOT.glob(pattern))
            if not matches:
                missing_data.append(pattern)
        if missing_data and plan.id != "image_quality":
            # Most packages can regenerate synthetic data; warn only
            report.warnings.append(
                f"{plan.id}: dataset glob empty {missing_data} — train.py may regenerate"
            )
        report.phases.append(plan)

    if not report.phases:
        report.blockers.append("No trainable phases found")
        report.ok = False

    report.decisions["phase_count"] = len(
        [p for p in report.phases if not p.skip_reason]
    )
    return report


def write_report(report: GuardReport, path: Path | None = None) -> Path:
    out = path or (_ROOT / "datasets" / "evaluation" / "safe_train_guard_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return out


def main() -> int:
    report = build_guard_plan()
    path = write_report(report)
    print(json.dumps(report.to_dict(), indent=2))
    print(f"\nWrote {path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
