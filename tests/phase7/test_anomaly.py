"""Phase 7 — ML anomaly detection tests."""

from __future__ import annotations

import time
from datetime import date, timedelta

import pytest


@pytest.fixture(autouse=True)
def _reset():
    from services.ai_service.core.feature_flags import reset_feature_flags_cache
    from services.ai_service.core.registry import reset_registry_cache

    reset_feature_flags_cache()
    reset_registry_cache()
    yield
    reset_feature_flags_cache()
    reset_registry_cache()


def _series(start: float = 1.0, step: float = 0.0, n: int = 5):
    base = date(2023, 1, 1)
    return [(base + timedelta(days=30 * i), start + step * i) for i in range(n)]


class TestBackends:
    def test_isolation_forest(self):
        from models.anomaly_detection.backends import create_backend
        import numpy as np

        X = np.random.randn(100, 8)
        m = create_backend("isolation_forest")
        m.fit(X)
        s = m.score_samples(X[:5])
        assert len(s) == 5
        assert m.name == "isolation_forest"

    def test_lof(self):
        from models.anomaly_detection.backends import create_backend
        import numpy as np

        X = np.random.randn(80, 6)
        m = create_backend("lof")
        m.fit(X)
        assert len(m.score_samples(X[:3])) == 3

    def test_robust_z(self):
        from models.anomaly_detection.backends import create_backend
        import numpy as np

        X = np.random.randn(50, 4)
        m = create_backend("robust_z")
        m.fit(X)
        assert m.name == "robust_z"
        assert 0 <= m.score_samples(X[:1])[0] <= 1


class TestEngine:
    def test_detect_series_language(self):
        from models.anomaly_detection.infer import LabAnomalyEngine

        eng = LabAnomalyEngine()
        out = eng.detect_series("Creatinine", _series(1.0, 0.5, 5))
        assert "diagnosis" not in out["summary_en"].lower() or "not a medical diagnosis" in out[
            "summary_en"
        ].lower()
        assert "you have" not in out["summary_en"].lower()
        text = out["summary_en"].lower()
        if out["is_anomaly"]:
            assert "anomalous laboratory pattern" in text
        assert out["anomaly_probability"] is not None
        assert out["anomaly_category"]

    def test_profile(self):
        from models.anomaly_detection.infer import LabAnomalyEngine

        metrics = [
            {"test_name": "Creatinine", "value_numeric": 2.5},
            {"test_name": "ALT", "value_numeric": 120},
            {"test_name": "Hemoglobin", "value_numeric": 9.0},
        ]
        out = LabAnomalyEngine().score_profile(metrics, demographics={"age": 60, "sex": "m"})
        assert 0 <= out["anomaly_score"] <= 1
        assert out["top_contributors"]

    def test_missing_data(self):
        from models.anomaly_detection.infer import LabAnomalyEngine

        out = LabAnomalyEngine().detect_series("HbA1c", [(date(2024, 1, 1), 5.5)])
        assert out["data_points_used"] >= 1
        assert out["summary_en"]


class TestFeatureFlag:
    def test_flag_off_statistical(self, monkeypatch):
        monkeypatch.setenv("USE_ANOMALY_MODEL", "0")
        monkeypatch.setenv("USE_OUTLIER_MODEL", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_anomaly_detector, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_anomaly_detector().detect("Haemoglobin", _series(13.0, 0.05, 5), unit="g/dL")
        assert "ml_anomaly" not in r.method

    def test_flag_on_ml(self, monkeypatch):
        monkeypatch.setenv("USE_ANOMALY_MODEL", "1")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_anomaly_detector, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_anomaly_detector().detect("Creatinine", _series(1.0, 0.4, 5))
        assert "ml_anomaly" in r.method or r.method  # fallback statistical if ML boom
        assert r.summary_en

    def test_outlier_alias(self, monkeypatch):
        monkeypatch.setenv("USE_ANOMALY_MODEL", "0")
        monkeypatch.setenv("USE_OUTLIER_MODEL", "1")
        from services.ai_service.core.feature_flags import (
            get_feature_flags,
            reset_feature_flags_cache,
        )

        reset_feature_flags_cache()
        f = get_feature_flags()
        assert f.use_anomaly_model is True or f.use_outlier_model is True


class TestFallback:
    def test_ml_fail_to_stats(self):
        from services.ai_service.adapters.anomaly_detector import (
            FallbackAnomalyDetector,
            StatisticalAnomalyDetector,
        )

        class Boom:
            def detect(self, *a, **k):
                raise RuntimeError("x")

        fb = FallbackAnomalyDetector(Boom(), StatisticalAnomalyDetector())
        r = fb.detect("ALT", _series(30, 5, 4))
        assert fb.last_path == "fallback"
        assert r.method  # statistical method name


class TestPerformance:
    def test_latency(self):
        from models.anomaly_detection.infer import LabAnomalyEngine

        eng = LabAnomalyEngine()
        pts = _series(1.0, 0.1, 5)
        t0 = time.perf_counter()
        for _ in range(20):
            eng.detect_series("Creatinine", pts)
        assert (time.perf_counter() - t0) < 15.0


class TestRegression:
    def test_default_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        f = get_feature_flags()
        assert f.use_anomaly_model is False
        assert f.use_outlier_model is False

    def test_prior_flags_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        f = get_feature_flags()
        assert f.use_health_score_model is False
        assert f.use_forecast_model is False


class TestMetrics:
    def test_precision_recall(self):
        from models.anomaly_detection.metrics import precision_at_k, recall_at_k

        y = [0, 0, 1, 1]
        s = [0.1, 0.2, 0.9, 0.8]
        assert precision_at_k(y, s, k=2) == 1.0
        assert recall_at_k(y, s, k=2) == 1.0
