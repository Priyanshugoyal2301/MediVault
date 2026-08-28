"""HealthScorer — aggregate longitudinal health literacy score."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .types import HealthScoreResult


@runtime_checkable
class HealthScorer(Protocol):
    """
    Aggregate non-diagnostic health *orientation* score across recent metrics.

    Not present in current product APIs. Interface reserved for
    USE_HEALTH_SCORE_MODEL rollout without API contract churn.

    Default: UnavailableHealthScorer.
    """

    def score(self, metrics: list[dict[str, Any]]) -> HealthScoreResult:
        ...
