"""
HealthScorer adapters.

UnavailableHealthScorer — default when USE_HEALTH_SCORE_MODEL=0.
MLHealthScorer — Phase 6 engine + SHAP explanations.
"""

from __future__ import annotations

from typing import Any

from packages.ml_interfaces.types import HealthScoreResult
from packages.shared_utils import get_logger

logger = get_logger(__name__)

_DISCLAIMER = (
    "Health score estimate only. This is not a medical diagnosis or "
    "treatment recommendation. For informational purposes only."
)


class UnavailableHealthScorer:
    """Default: no aggregate health score model."""

    def score(self, metrics: list[dict[str, Any]]) -> HealthScoreResult:
        _ = metrics
        return HealthScoreResult(
            score=None,
            level="unavailable",
            components={},
            summary_en=(
                "Health score model is not active. Individual metrics and trends "
                "remain available on the timeline. "
                f"{_DISCLAIMER}"
            ),
            summary_hi=(
                "स्वास्थ्य स्कोर मॉडल सक्रिय नहीं है। व्यक्तिगत मेट्रिक और "
                "रुझान समयरेखा पर उपलब्ध रहते हैं।"
            ),
            method="unavailable",
            confidence=None,
            risk_band="Unavailable",
            disclaimer_en=_DISCLAIMER,
        )


class MLHealthScorer:
    """Phase 6 ML engine implementing HealthScorer Protocol."""

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from models.health_score.infer import HealthScoreEngine

            engine = HealthScoreEngine()
        self._engine = engine

    def score(self, metrics: list[dict[str, Any]]) -> HealthScoreResult:
        demo = None
        for m in metrics or []:
            tn = (m.get("test_name") or "").lower()
            if tn == "age":
                demo = demo or {}
                demo["age"] = m.get("value_numeric")
            if tn in ("sex", "gender"):
                demo = demo or {}
                demo["sex"] = m.get("value_text") or m.get("value_numeric")
        raw = self._engine.score(metrics, demographics=demo)
        return HealthScoreResult(
            score=raw.get("score"),
            level=str(raw.get("level") or "unavailable"),
            components=dict(raw.get("components") or {}),
            summary_en=str(raw.get("summary_en") or ""),
            summary_hi=str(raw.get("summary_hi") or ""),
            method=str(raw.get("method") or "health_score"),
            confidence=raw.get("confidence"),
            risk_band=str(raw.get("risk_band") or ""),
            positive_contributors=tuple(raw.get("positive_contributors") or ()),
            negative_contributors=tuple(raw.get("negative_contributors") or ()),
            top_features=tuple(raw.get("top_features") or ()),
            global_importance=tuple(raw.get("global_importance") or ()),
            explanation_method=str(raw.get("explanation_method") or "none"),
            disclaimer_en=str(raw.get("disclaimer_en") or _DISCLAIMER),
        )


class FallbackHealthScorer:
    def __init__(
        self, primary: Any, fallback: UnavailableHealthScorer | None = None
    ) -> None:
        self.primary = primary
        self.fallback = fallback or UnavailableHealthScorer()
        self.last_path = "unset"

    def score(self, metrics: list[dict[str, Any]]) -> HealthScoreResult:
        try:
            r = self.primary.score(metrics)
            self.last_path = "ml"
            return r
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ML health scorer failed (%s); falling back to unavailable",
                type(exc).__name__,
            )
            self.last_path = "fallback"
            return self.fallback.score(metrics)
