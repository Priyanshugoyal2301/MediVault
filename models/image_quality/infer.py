"""Document Image Quality Engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .backends import QualityBackend, create_backend, describe_backends, probs_to_result
from .config_loader import artifacts_dir, load_config
from .features import compute_features, feature_vector, opencv_rule_predict
from .image_io import decode_image
from .labels import (
    DISCLAIMER,
    category_from_score,
    display_label,
    recommendation,
)


class ImageQualityEngine:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        auto_train_if_missing: bool = True,
    ) -> None:
        self.config = config or load_config(validate=True)
        self.model: QualityBackend | None = None
        self.backend_name = "uninitialized"
        self._load_or_train(auto_train_if_missing=auto_train_if_missing)

    def _load_or_train(self, *, auto_train_if_missing: bool) -> None:
        art = artifacts_dir(self.config)
        meta = art / "meta.json"
        model_p = art / "model.pkl"
        if meta.exists() and model_p.exists():
            try:
                meta_obj = json.loads(meta.read_text(encoding="utf-8"))
                self.backend_name = meta_obj.get("backend", "loaded")
                self.model = QualityBackend.load(model_p)
                return
            except Exception:
                self.model = None
        if auto_train_if_missing:
            self.train()

    def train(self) -> Path:
        from .dataset import load_train_arrays

        images, X, y = load_train_arrays(n=int(self.config.get("train_n") or 200))
        kind = self.config.get("active_backend") or "auto"
        seed = int(self.config.get("seed") or 42)
        epochs = int(self.config.get("epochs") or 3)
        model = create_backend(kind, seed=seed, epochs=epochs)
        # Prefer feature-only training for speed stability; torch paths use images when backend needs
        use_imgs = False  # feature training is default for speed/stability
        # Full CNN pixel train when backend explicitly torch-capable and env set
        import os

        if os.getenv("IMAGE_QUALITY_TRAIN_PIXELS", "0") in ("1", "true", "yes"):
            use_imgs = model.name in ("mobilenet_v3", "efficientnet_lite0") and describe_backends().get(
                "torch"
            )
        model.fit(X, y, images=images if use_imgs else None)
        # Ensure name reflects architecture even if feature proxy
        if model.name.startswith("mobilenet") or getattr(model, "name", "") == "mobilenet_v3":
            self.backend_name = model.name
        else:
            self.backend_name = model.name
        self.model = model
        self.backend_name = model.name

        art = artifacts_dir(self.config)
        art.mkdir(parents=True, exist_ok=True)
        model.save(art / "model.pkl")
        (art / "meta.json").write_text(
            json.dumps(
                {
                    "backend": self.backend_name,
                    "n_train": int(len(y)),
                    "primary": self.config.get("primary_architecture"),
                    "fallback": self.config.get("fallback_architecture"),
                    "baseline": self.config.get("baseline_architecture"),
                    "available": describe_backends(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return art

    def assess_array(self, rgb: np.ndarray) -> dict[str, Any]:
        if self.model is None:
            self.train()
        assert self.model is not None
        feats = compute_features(rgb)
        x = feature_vector(feats).reshape(1, -1)
        try:
            proba = self.model.predict_proba(x, images=[rgb])[0]
            raw = probs_to_result(
                proba, thr=float(self.config.get("label_threshold") or 0.45)
            )
            method = f"quality:{self.backend_name}"
        except Exception:
            raw = opencv_rule_predict(feats)
            method = "quality:opencv_rules_fallback"

        score_100 = float(raw["quality_score"])
        problems = [display_label(p) for p in raw.get("problems") or []]
        raw_problems = list(raw.get("problems") or [])
        thr = float(self.config.get("ready_threshold_score") or 70)
        ready = bool(raw.get("ready")) or score_100 >= thr and not raw_problems
        if score_100 < thr:
            ready = False
        category = category_from_score(score_100) if not ready else "Ready for OCR"
        if ready:
            category = "Ready for OCR"
        conf = float(raw.get("confidence") or 0.7)
        rec = recommendation(score_100, raw_problems)
        return {
            "ok": ready,
            "score": score_100 / 100.0,  # QualityCheckResult expects ~0-1
            "quality_score": score_100,
            "category": category,
            "problems": problems,
            "reasons": tuple(problems),
            "confidence": conf,
            "recommendation": rec,
            "method": method,
            "disclaimer": DISCLAIMER,
            "metadata": {
                "quality_score": score_100,
                "category": category,
                "problems": problems,
                "confidence": conf,
                "recommendation": rec,
                "method": method,
                "backend": self.backend_name,
            },
        }

    def assess_bytes(self, file_bytes: bytes, mime_type: str = "") -> dict[str, Any]:
        rgb = decode_image(file_bytes, mime_type)
        out = self.assess_array(rgb)
        out["metadata"]["mime_type"] = mime_type
        out["metadata"]["bytes"] = len(file_bytes)
        return out
