"""BiomarkerForecaster — longitudinal lab value forecasting (non-diagnostic)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .types import BiomarkerForecastBatch


@runtime_checkable
class BiomarkerForecaster(Protocol):
    """
    Forecast future biomarker values from a patient history series.

    NEVER diagnose. Output point forecasts + intervals only.
    Default: UnavailableBiomarkerForecaster when USE_FORECAST_MODEL=0.
    """

    def forecast(
        self,
        history: list[dict[str, Any]],
        *,
        horizon_days: int = 180,
        biomarkers: list[str] | None = None,
        demographics: dict[str, Any] | None = None,
    ) -> BiomarkerForecastBatch:
        """
        Args:
            history: chronological (or mixed) metrics dicts with
                     test_name, value_numeric, date_of_test (optional).
            horizon_days: forecast horizon (default 6 months ≈ 180d).
            biomarkers: optional subset of keys to forecast.
            demographics: age, sex, optional lifestyle fields.
        """
        ...
