"""
QualityChecker adapters.

PassThrough — default (flag off).
MLImageQualityChecker — Phase 8 MobileNet / OpenCV stack.
"""

from __future__ import annotations

from typing import Any

from packages.ml_interfaces.types import QualityCheckResult
from packages.shared_utils import get_logger

logger = get_logger(__name__)


class PassThroughQualityChecker:
    """No-op quality gate — preserves current pipeline when flag off."""

    def check(self, file_bytes: bytes, mime_type: str) -> QualityCheckResult:
        return QualityCheckResult(
            ok=True,
            score=1.0,
            reasons=(),
            metadata={
                "mime_type": mime_type,
                "bytes": len(file_bytes),
                "method": "passthrough",
                "category": "Ready for OCR",
                "recommendation": "Proceed with OCR",
            },
        )


class OpenCVQualityChecker:
    """Rule baseline only (no learned weights)."""

    def check(self, file_bytes: bytes, mime_type: str) -> QualityCheckResult:
        from models.image_quality.features import compute_features, opencv_rule_predict
        from models.image_quality.image_io import decode_image
        from models.image_quality.labels import (
            category_from_score,
            display_label,
            recommendation,
        )

        rgb = decode_image(file_bytes, mime_type)
        raw = opencv_rule_predict(compute_features(rgb))
        score_100 = float(raw["quality_score"])
        problems = [display_label(p) for p in raw["problems"]]
        ok = bool(raw["ready"])
        return QualityCheckResult(
            ok=ok,
            score=score_100 / 100.0,
            reasons=tuple(problems),
            metadata={
                "mime_type": mime_type,
                "bytes": len(file_bytes),
                "method": "opencv_rules",
                "quality_score": score_100,
                "category": category_from_score(score_100) if not ok else "Ready for OCR",
                "confidence": raw.get("confidence"),
                "recommendation": recommendation(score_100, list(raw["problems"])),
            },
        )


class MLImageQualityChecker:
    """Phase 8 ImageQualityEngine."""

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from models.image_quality.infer import ImageQualityEngine

            engine = ImageQualityEngine()
        self._engine = engine

    def check(self, file_bytes: bytes, mime_type: str) -> QualityCheckResult:
        raw = self._engine.assess_bytes(file_bytes, mime_type)
        return QualityCheckResult(
            ok=bool(raw["ok"]),
            score=float(raw["score"]),
            reasons=tuple(raw.get("reasons") or ()),
            metadata=dict(raw.get("metadata") or {}),
        )


class FallbackQualityChecker:
    def __init__(self, primary: Any, fallback: Any | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or PassThroughQualityChecker()
        self.last_path = "unset"

    def check(self, file_bytes: bytes, mime_type: str) -> QualityCheckResult:
        try:
            r = self.primary.check(file_bytes, mime_type)
            self.last_path = "ml"
            return r
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ML image quality failed (%s); falling back",
                type(exc).__name__,
            )
            self.last_path = "fallback"
            return self.fallback.check(file_bytes, mime_type)
