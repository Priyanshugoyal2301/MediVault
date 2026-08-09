"""
tests/unit/ai-service/test_anomaly.py

Unit tests for the anomaly detection engine.

Test groups:
  A. Z-score (zscore.py)
     - Returns INSUFFICIENT_DATA for < 3 points
     - Correctly classifies rising / falling / stable trends
     - Computes correct out-of-range streak

  B. Model (model.py)
     - zscore_fallback used for < 5 data points
     - IsolationForest path used for >= 5 points (sklearn not required in fallback path)
     - Normalised anomaly score stays in [-1, +1]

  C. Detector (detector.py)
     - End-to-end DetectionResult contains all expected fields
     - Bilingual summaries (EN + HI) always present
     - TONE RULE: summaries must NOT contain forbidden diagnostic phrases

  D. Anomaly endpoint
     - POST /anomaly/detect returns 200 with correct schema
     - POST /anomaly/detect with 0 data_points returns 422
     - Sorts unsorted input before analysis
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# A. Z-score tests
# ---------------------------------------------------------------------------

class TestZScore:
    def _make_points(self, values: list[float]) -> list[tuple[date, float]]:
        base = date(2024, 1, 1)
        return [(date(2024, 1, i + 1), v) for i, v in enumerate(values)]

    def test_insufficient_data_below_3_points(self):
        from services.ai_service.anomaly.zscore import compute_zscore, TrendDirection  # type: ignore
        result = compute_zscore(self._make_points([12.0, 13.0]))
        assert result.trend == TrendDirection.INSUFFICIENT_DATA
        assert result.z_score is None
        assert result.data_points_used == 2

    def test_exactly_3_points_returns_result(self):
        from services.ai_service.anomaly.zscore import compute_zscore, TrendDirection  # type: ignore
        result = compute_zscore(self._make_points([12.0, 13.0, 14.0]))
        assert result.trend != TrendDirection.INSUFFICIENT_DATA
        assert result.z_score is not None
        assert result.data_points_used == 3

    def test_rising_trend_detected(self):
        from services.ai_service.anomaly.zscore import compute_zscore, TrendDirection  # type: ignore
        # Steadily increasing values → rising
        result = compute_zscore(self._make_points([10.0, 12.0, 14.0, 16.0, 18.0]))
        assert result.trend == TrendDirection.RISING

    def test_falling_trend_detected(self):
        from services.ai_service.anomaly.zscore import compute_zscore, TrendDirection  # type: ignore
        result = compute_zscore(self._make_points([18.0, 16.0, 14.0, 12.0, 10.0]))
        assert result.trend == TrendDirection.FALLING

    def test_stable_trend_detected(self):
        from services.ai_service.anomaly.zscore import compute_zscore, TrendDirection  # type: ignore
        # All values equal → stable (std_dev=0, slope=0)
        result = compute_zscore(self._make_points([13.5, 13.5, 13.5, 13.5, 13.5]))
        assert result.trend == TrendDirection.STABLE

    def test_out_of_range_streak_counted_correctly(self):
        from services.ai_service.anomaly.zscore import compute_zscore  # type: ignore
        # One normal point then a large spike — last point anomalous, streak=1
        pts = self._make_points([13.5, 13.4, 13.6, 13.5, 13.3, 25.0])  # 25.0 is way off
        result = compute_zscore(pts)
        assert result.out_of_range_streak >= 1

    def test_z_score_for_flat_series_is_zero(self):
        from services.ai_service.anomaly.zscore import compute_zscore  # type: ignore
        result = compute_zscore(self._make_points([13.5, 13.5, 13.5, 13.5]))
        # std_dev == 0 → all z_scores set to 0.0
        assert result.z_score == 0.0


# ---------------------------------------------------------------------------
# B. Model scorer tests
# ---------------------------------------------------------------------------

class TestModelScorer:
    def _pts(self, values: list[float]) -> list[tuple[date, float]]:
        return [(date(2024, 1, i + 1), v) for i, v in enumerate(values)]

    def test_zscore_fallback_used_for_small_dataset(self):
        from services.ai_service.anomaly.model import score_anomaly  # type: ignore
        pts = self._pts([12.0, 13.0, 14.0])  # only 3 points < MIN_SAMPLES_FOR_MODEL(5)
        result = score_anomaly(pts, z_score=0.1)
        assert result.method == "zscore_fallback"

    def test_anomaly_score_in_valid_range(self):
        from services.ai_service.anomaly.model import score_anomaly  # type: ignore
        pts = self._pts([13.5] * 8)
        result = score_anomaly(pts, z_score=0.0)
        assert -1.0 <= result.anomaly_score <= 1.0

    def test_large_zscore_flags_anomaly_in_fallback(self):
        from services.ai_service.anomaly.model import score_anomaly  # type: ignore
        # |z| = 3 → should flag as anomaly in fallback path
        pts = self._pts([12.0, 13.0, 14.0])
        result = score_anomaly(pts, z_score=3.0)
        assert result.is_anomaly is True

    def test_small_zscore_does_not_flag_anomaly_in_fallback(self):
        from services.ai_service.anomaly.model import score_anomaly  # type: ignore
        pts = self._pts([12.0, 13.0, 14.0])
        result = score_anomaly(pts, z_score=0.5)
        assert result.is_anomaly is False

    def test_none_z_score_returns_neutral_score(self):
        from services.ai_service.anomaly.model import score_anomaly  # type: ignore
        pts = self._pts([13.0, 13.5])  # < 5 points, z_score=None
        result = score_anomaly(pts, z_score=None)
        assert result.anomaly_score == 0.0
        assert result.is_anomaly is False


# ---------------------------------------------------------------------------
# C. Detector end-to-end tests
# ---------------------------------------------------------------------------

# ─── TONE RULES (must not appear in any summary) ────────────────────────────
_FORBIDDEN_PHRASES_EN = [
    "you have ",
    "you are diagnosed",
    "diagnosed with",
    "you are sick",
    "critical",
    "dangerous",
    "alarming",
]
_FORBIDDEN_PHRASES_HI = [
    "आपको कैंसर",
    "आपको बीमारी है",
    "खतरनाक",
    "घातक",
]
# ────────────────────────────────────────────────────────────────────────────


class TestDetector:
    def _pts(self, values: list[float]) -> list[tuple[date, float]]:
        return [(date(2024, 1, i + 1), v) for i, v in enumerate(values)]

    def test_result_has_all_required_fields(self):
        from services.ai_service.anomaly.detector import detect  # type: ignore
        result = detect("Haemoglobin", self._pts([13.5] * 5), unit="g/dL")
        assert result.test_name == "Haemoglobin"
        assert result.trend in ("rising", "falling", "stable", "insufficient_data")
        assert isinstance(result.anomaly_score, float)
        assert isinstance(result.is_anomaly, bool)
        assert isinstance(result.summary_en, str)
        assert isinstance(result.summary_hi, str)
        assert result.data_points_used == 5

    def test_insufficient_data_summary_mentions_count(self):
        from services.ai_service.anomaly.detector import detect  # type: ignore
        result = detect("WBC", self._pts([7.0, 7.5]))
        assert result.trend == "insufficient_data"
        assert "2" in result.summary_en

    def test_bilingual_summaries_both_present(self):
        from services.ai_service.anomaly.detector import detect  # type: ignore
        result = detect("Platelets", self._pts([150000.0] * 5))
        assert len(result.summary_en) > 10
        assert len(result.summary_hi) > 10

    @pytest.mark.parametrize("phrase", _FORBIDDEN_PHRASES_EN)
    def test_english_summary_tone_rule(self, phrase: str):
        """English summary must NOT contain forbidden diagnostic phrases."""
        from services.ai_service.anomaly.detector import detect  # type: ignore
        # Use a scenario that would trigger anomaly (large spike)
        values = [13.5, 13.4, 13.6, 13.5, 25.0]
        result = detect("Haemoglobin", self._pts(values))
        assert phrase.lower() not in result.summary_en.lower(), (
            f"Forbidden phrase '{phrase}' found in EN summary: {result.summary_en!r}"
        )

    @pytest.mark.parametrize("phrase", _FORBIDDEN_PHRASES_HI)
    def test_hindi_summary_tone_rule(self, phrase: str):
        """Hindi summary must NOT contain forbidden diagnostic phrases."""
        from services.ai_service.anomaly.detector import detect  # type: ignore
        values = [13.5, 13.4, 13.6, 13.5, 25.0]
        result = detect("Haemoglobin", self._pts(values))
        assert phrase not in result.summary_hi, (
            f"Forbidden phrase '{phrase}' found in HI summary: {result.summary_hi!r}"
        )

    def test_rising_series_returns_rising_trend(self):
        from services.ai_service.anomaly.detector import detect  # type: ignore
        result = detect("Cholesterol", self._pts([150.0, 165.0, 180.0, 195.0, 210.0]))
        assert result.trend == "rising"

    def test_doctor_consult_mentioned_on_anomaly(self):
        """When is_anomaly=True the summary should suggest consulting a doctor."""
        from services.ai_service.anomaly.detector import detect  # type: ignore
        # Mock the model so it always returns is_anomaly=True regardless of data
        with patch(
            "services.ai_service.anomaly.detector.score_anomaly"
        ) as mock_score:
            from services.ai_service.anomaly.model import ModelAnomalyResult  # type: ignore
            mock_score.return_value = ModelAnomalyResult(
                anomaly_score=-0.8,
                is_anomaly=True,
                method="isolation_forest",
                data_points_used=5,
            )
            result = detect("Haemoglobin", self._pts([13.5] * 5))

        assert "doctor" in result.summary_en.lower()


# ---------------------------------------------------------------------------
# D. Anomaly endpoint tests
# ---------------------------------------------------------------------------

@pytest.fixture
def anomaly_app():
    from fastapi import FastAPI
    from services.ai_service.routers.anomaly import router as anomaly_router  # type: ignore

    app = FastAPI()
    app.include_router(anomaly_router)
    return app


class TestAnomalyEndpoint:
    def _payload(self, n: int = 5, value: float = 13.5) -> dict:
        return {
            "test_name": "Haemoglobin",
            "unit": "g/dL",
            "data_points": [
                {"date": f"2024-0{i+1}-01", "value": value}
                for i in range(n)
            ],
        }

    def test_detect_returns_200_schema(self, anomaly_app):
        from fastapi.testclient import TestClient

        with TestClient(anomaly_app) as client:
            resp = client.post("/anomaly/detect", json=self._payload())
        assert resp.status_code == 200
        data = resp.json()
        assert "trend" in data
        assert "anomaly_score" in data
        assert "is_anomaly" in data
        assert "summary_en" in data
        assert "summary_hi" in data

    def test_detect_empty_data_points_returns_422(self, anomaly_app):
        from fastapi.testclient import TestClient

        payload = {"test_name": "Haemoglobin", "data_points": []}
        with TestClient(anomaly_app) as client:
            resp = client.post("/anomaly/detect", json=payload)
        assert resp.status_code == 422

    def test_detect_blank_test_name_returns_422(self, anomaly_app):
        from fastapi.testclient import TestClient

        payload = self._payload()
        payload["test_name"] = "   "
        with TestClient(anomaly_app) as client:
            resp = client.post("/anomaly/detect", json=payload)
        assert resp.status_code == 422

    def test_detect_sorts_unsorted_input(self, anomaly_app):
        """Endpoint should sort data_points by date before analysis."""
        from fastapi.testclient import TestClient

        payload = {
            "test_name": "Haemoglobin",
            "data_points": [
                {"date": "2024-03-01", "value": 14.0},
                {"date": "2024-01-01", "value": 12.0},
                {"date": "2024-02-01", "value": 13.0},
                {"date": "2024-04-01", "value": 15.0},
                {"date": "2024-05-01", "value": 16.0},
            ],
        }
        with TestClient(anomaly_app) as client:
            resp = client.post("/anomaly/detect", json=payload)
        assert resp.status_code == 200
        # Rising series: 12 → 13 → 14 → 15 → 16 should be detected as rising
        assert resp.json()["trend"] == "rising"
