"""Evaluate image quality backends."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    import conftest  # noqa: F401
except Exception:
    pass


def evaluate(config_path: Path | None = None) -> dict:
    import numpy as np

    from models.image_quality.backends import create_backend, describe_backends
    from models.image_quality.config_loader import load_config, resolve_path
    from models.image_quality.dataset import load_eval_arrays, load_train_arrays
    from models.image_quality.infer import ImageQualityEngine
    from models.image_quality.labels import ALL_LABELS, READY_LABEL
    from models.image_quality.metrics import (
        accuracy_multilabel,
        confusion_ready,
        f1_macro,
        precision_macro,
        recall_macro,
        roc_auc_binary,
    )

    cfg = load_config(config_path, validate=True)
    _, Xtr, ytr = load_train_arrays(n=160)
    images_ev, Xev, yev = load_eval_arrays(n=60)
    imgs_tr, _, _ = load_train_arrays(n=160)

    comparison = {}
    for kind in ("mobilenet_v3", "efficientnet_lite0", "opencv_rules"):
        m = create_backend(kind, seed=42, epochs=2)
        t0 = time.perf_counter()
        # Match production default: feature-head train (picklable, stable metrics)
        m.fit(Xtr, ytr, images=None)
        fit_ms = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        proba = m.predict_proba(Xev, images=None)
        pred = (proba >= 0.5).astype(int)
        inf_ms = (time.perf_counter() - t1) * 1000
        ready_i = ALL_LABELS.index(READY_LABEL)
        comparison[kind] = {
            "subset_accuracy": accuracy_multilabel(yev, pred),
            "f1_macro": f1_macro(yev, pred),
            "precision_macro": precision_macro(yev, pred),
            "recall_macro": recall_macro(yev, pred),
            "ready_roc_auc": roc_auc_binary(yev[:, ready_i], proba[:, ready_i]),
            "ready_confusion": confusion_ready(yev[:, ready_i], pred[:, ready_i]),
            "fit_ms": fit_ms,
            "infer_batch_ms": inf_ms,
            "latency_ms_per_image": inf_ms / max(1, len(yev)),
        }

    eng = ImageQualityEngine(cfg, auto_train_if_missing=True)
    # e2e on synthetic bytes
    from models.image_quality.augmentations import make_clean_lab_image, apply_degradation
    import io
    from PIL import Image

    rng = np.random.default_rng(0)
    clean = make_clean_lab_image(rng)
    blur, _ = apply_degradation(clean, "blurry", rng)
    buf = io.BytesIO()
    Image.fromarray(blur).save(buf, format="PNG")
    t2 = time.perf_counter()
    out = eng.assess_bytes(buf.getvalue(), "image/png")
    e2e = (time.perf_counter() - t2) * 1000

    report = {
        "model": "document_image_quality",
        "active_backend": eng.backend_name,
        "available_backends": describe_backends(),
        "n_eval": int(len(yev)),
        "comparison": comparison,
        "e2e_assess_ms": e2e,
        "sample_blur": {
            "ok": out["ok"],
            "quality_score": out["quality_score"],
            "category": out["category"],
            "problems": out["problems"],
            "recommendation": out["recommendation"],
        },
        "notes": [
            "Synthetic degraded lab pages only.",
            "Primary MobileNetV3-Small (or feature proxy if torch missing).",
            "Fallback EfficientNet-B0/Lite0-compatible; baseline OpenCV rules.",
            "DocLayNet/PubLayNet/RVL-CDIP optional offline paths only.",
        ],
    }
    out_path = resolve_path(cfg["paths"]["evaluation_out"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "active": report["active_backend"],
                "e2e_ms": e2e,
                "comparison_keys": list(comparison.keys()),
                "written": str(out_path),
            },
            indent=2,
        )
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=None)
    args = p.parse_args()
    evaluate(args.config)


if __name__ == "__main__":
    main()
