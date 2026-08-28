"""
RiskPredictor adapters.

UnavailableRiskPredictor — default when flag off.
MLDiseaseRiskPredictor — Phase 4 multi-condition engine.
RuleBasedRiskPredictor — simple threshold baseline (eval / comparison).
"""

from __future__ import annotations

from typing import Any

from packages.ml_interfaces.types import RiskPredictionResult
from packages.shared_utils import get_logger

logger = get_logger(__name__)


class UnavailableRiskPredictor:
    """Default: no risk model. Explicitly unavailable, never fabricates risk."""

    def predict(self, metrics: list[dict[str, Any]]) -> RiskPredictionResult:
        _ = metrics
        return RiskPredictionResult(
            risk_score=None,
            risk_band="unavailable",
            drivers=(),
            summary_en=(
                "Risk model is not active. This product does not provide "
                "population risk scores until a validated model is enabled. "
                "Risk estimate only. This is not a medical diagnosis."
            ),
            summary_hi=(
                "जोखिम मॉडल सक्रिय नहीं है। सत्यापित मॉडल सक्षम होने तक "
                "यह उत्पाद जनसंख्या जोखिम स्कोर प्रदान नहीं करता।"
            ),
            method="unavailable",
        )


class RuleBasedRiskPredictor:
    """Heuristic biomarker thresholds → statistical risk signals only."""

    def predict(self, metrics: list[dict[str, Any]]) -> RiskPredictionResult:
        from models.risk_prediction.preprocess import metrics_to_feature_dict
        from models.risk_prediction.rules import rule_based_probs
        from models.risk_prediction.diseases import DISCLAIMER_EN, DISCLAIMER_HI, DISEASES

        fd = metrics_to_feature_dict(metrics)
        feats = {k: fd.get(k) for k in fd}
        probs = rule_based_probs(feats)
        top_id = max(probs, key=lambda k: probs[k])
        top_p = probs[top_id]
        band = "low" if top_p < 0.33 else ("moderate" if top_p < 0.66 else "high")
        name = next((d["name_en"] for d in DISEASES if d["id"] == top_id), top_id)
        return RiskPredictionResult(
            risk_score=float(sum(probs.values()) / max(1, len(probs))),
            risk_band=band,
            drivers=tuple(k for k, v in sorted(feats.items(), key=lambda x: -(x[1] or 0)) if v)[:5],
            summary_en=(
                f"{DISCLAIMER_EN} Increased statistical risk for {name} "
                f"≈ {top_p:.0%} ({band}). Not a diagnosis."
            ),
            summary_hi=f"{DISCLAIMER_HI} सांख्यिकीय जोखिम अनुमान — निदान नहीं।",
            method="rule_thresholds",
            conditions=tuple(
                {
                    "disease_id": did,
                    "risk_probability": float(p),
                    "risk_category": "low" if p < 0.33 else ("moderate" if p < 0.66 else "high"),
                }
                for did, p in probs.items()
            ),
        )


class MLDiseaseRiskPredictor:
    """Phase 4 ML engine implementing RiskPredictor Protocol."""

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from models.risk_prediction.infer import DiseaseRiskEngine

            engine = DiseaseRiskEngine()
        self._engine = engine

    def predict(self, metrics: list[dict[str, Any]]) -> RiskPredictionResult:
        demo = None
        # extract age/sex if present as special metrics
        for m in metrics or []:
            tn = (m.get("test_name") or "").lower()
            if tn == "age":
                demo = demo or {}
                demo["age"] = m.get("value_numeric")
            if tn in ("sex", "gender"):
                demo = demo or {}
                demo["sex"] = m.get("value_text") or m.get("value_numeric")
        summary = self._engine.predict_summary(metrics, demographics=demo)
        conds = summary.get("conditions") or []
        return RiskPredictionResult(
            risk_score=summary.get("risk_score"),
            risk_band=str(summary.get("risk_band") or "unavailable"),
            drivers=tuple(summary.get("drivers") or ()),
            summary_en=str(summary.get("summary_en") or ""),
            summary_hi=str(summary.get("summary_hi") or ""),
            method=str(summary.get("method") or "disease_risk"),
            conditions=tuple(conds),
            disclaimer_en=str(
                summary.get("disclaimer_en")
                or "Risk estimate only. This is not a medical diagnosis."
            ),
        )


class FallbackRiskPredictor:
    """ML primary → unavailable/rule on hard failure."""

    def __init__(self, primary: Any, fallback: UnavailableRiskPredictor | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or UnavailableRiskPredictor()
        self.last_path = "unset"

    def predict(self, metrics: list[dict[str, Any]]) -> RiskPredictionResult:
        try:
            r = self.primary.predict(metrics)
            self.last_path = "ml"
            return r
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ML risk predictor failed (%s); falling back to unavailable",
                type(exc).__name__,
            )
            self.last_path = "fallback"
            return self.fallback.predict(metrics)
