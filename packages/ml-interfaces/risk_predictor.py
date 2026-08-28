"""RiskPredictor — non-diagnostic risk signals from structured metrics."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .types import RiskPredictionResult


@runtime_checkable
class RiskPredictor(Protocol):
    """
    Predict relative risk *signals* from structured lab metrics.

    CRITICAL product constraint: never emit diagnoses. Output is advisory
    framing only ("may be worth discussing with a clinician").

    Default: UnavailableRiskPredictor (no-op / unavailable).
    Future: trained model under models/risk_prediction/ when USE_RISK_MODEL=1
    (alias USE_DISEASE_RISK_MODEL).
    """

    def predict(self, metrics: list[dict[str, Any]]) -> RiskPredictionResult:
        """
        Args:
            metrics: Owner-scoped list of report value dicts
                     (test_name, value_numeric, unit, date_of_test, panel, ...).
        """
        ...
