"""
BiomarkerForecaster adapters.

UnavailableBiomarkerForecaster — default when USE_FORECAST_MODEL=0.
MLBiomarkerForecaster — Phase 5 longitudinal engine.
"""

from __future__ import annotations

from typing import Any

from packages.ml_interfaces.types import BiomarkerForecast, BiomarkerForecastBatch
from packages.shared_utils import get_logger

logger = get_logger(__name__)

_DISCLAIMER_EN = (
    "Forecast estimate only. This is not a medical diagnosis or "
    "treatment recommendation. For informational purposes only."
)
_DISCLAIMER_HI = (
    "केवल पूर्वानुमान। यह निदान या उपचार सलाह नहीं है। केवल सूचना के लिए।"
)


class UnavailableBiomarkerForecaster:
    """Default: forecasting inactive. No fabricated values."""

    def forecast(
        self,
        history: list[dict[str, Any]],
        *,
        horizon_days: int = 180,
        biomarkers: list[str] | None = None,
        demographics: dict[str, Any] | None = None,
    ) -> BiomarkerForecastBatch:
        _ = history, biomarkers, demographics
        return BiomarkerForecastBatch(
            forecasts=(),
            horizon_days=horizon_days,
            method="unavailable",
            disclaimer_en=_DISCLAIMER_EN,
            summary_en=(
                "Biomarker forecasting is not active. "
                f"{_DISCLAIMER_EN}"
            ),
            summary_hi=f"बायोमार्कर पूर्वानुमान सक्रिय नहीं है। {_DISCLAIMER_HI}",
        )


class MLBiomarkerForecaster:
    """Phase 5 ML engine implementing BiomarkerForecaster Protocol."""

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from models.forecasting.infer import BiomarkerForecastEngine

            engine = BiomarkerForecastEngine()
        self._engine = engine

    def forecast(
        self,
        history: list[dict[str, Any]],
        *,
        horizon_days: int = 180,
        biomarkers: list[str] | None = None,
        demographics: dict[str, Any] | None = None,
    ) -> BiomarkerForecastBatch:
        raw = self._engine.forecast(
            history,
            horizon_days=horizon_days,
            biomarkers=biomarkers,
            demographics=demographics,
        )
        items = []
        for f in raw.get("forecasts") or []:
            items.append(
                BiomarkerForecast(
                    biomarker=str(f.get("biomarker") or f.get("biomarker_id") or ""),
                    current_value=f.get("current_value"),
                    predicted_value=f.get("predicted_value"),
                    lower_bound=f.get("lower_bound"),
                    upper_bound=f.get("upper_bound"),
                    confidence=float(f.get("confidence") or 0.0),
                    trend_direction=str(f.get("trend_direction") or "unknown"),
                    expected_trend=str(f.get("expected_trend") or ""),
                    horizon_days=int(f.get("horizon_days") or horizon_days),
                    unit=f.get("unit"),
                    method=str(f.get("method") or raw.get("method") or "forecast"),
                    metadata={
                        "biomarker_id": f.get("biomarker_id"),
                        "n_history": f.get("n_history"),
                    },
                )
            )
        return BiomarkerForecastBatch(
            forecasts=tuple(items),
            horizon_days=int(raw.get("horizon_days") or horizon_days),
            method=str(raw.get("method") or "forecast"),
            disclaimer_en=str(raw.get("disclaimer_en") or _DISCLAIMER_EN),
            summary_en=str(raw.get("summary_en") or ""),
            summary_hi=str(raw.get("summary_hi") or ""),
        )


class FallbackBiomarkerForecaster:
    """ML primary → unavailable on hard failure."""

    def __init__(
        self,
        primary: Any,
        fallback: UnavailableBiomarkerForecaster | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or UnavailableBiomarkerForecaster()
        self.last_path = "unset"

    def forecast(
        self,
        history: list[dict[str, Any]],
        *,
        horizon_days: int = 180,
        biomarkers: list[str] | None = None,
        demographics: dict[str, Any] | None = None,
    ) -> BiomarkerForecastBatch:
        try:
            r = self.primary.forecast(
                history,
                horizon_days=horizon_days,
                biomarkers=biomarkers,
                demographics=demographics,
            )
            self.last_path = "ml"
            return r
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ML biomarker forecaster failed (%s); falling back to unavailable",
                type(exc).__name__,
            )
            self.last_path = "fallback"
            return self.fallback.forecast(
                history,
                horizon_days=horizon_days,
                biomarkers=biomarkers,
                demographics=demographics,
            )
