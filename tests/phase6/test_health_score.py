"""Phase 6 — Personalized health score + SHAP tests."""

from __future__ import annotations

import time

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


SAMPLE = [
    {"test_name": "HbA1c", "value_numeric": 5.8, "date_of_test": "2023-01-01"},
    {"test_name": "HbA1c", "value_numeric": 6.1, "date_of_test": "2023-06-01"},
    {"test_name": "Creatinine", "value_numeric": 1.0, "date_of_test": "2023-06-01"},
    {"test_name": "HDL", "value_numeric": 55, "date_of_test": "2023-06-01"},
    {"test_name": "LDL", "value_numeric": 130, "date_of_test": "2023-06-01"},
    {"test_name": "Hemoglobin", "value_numeric": 13.2, "date_of_test": "2023-06-01"},
    {"test_name": "ALT", "value_numeric": 35, "date_of_test": "2023-01-01"},
    {"test_name": "ALT", "value_numeric": 48, "date_of_test": "2023-06-01"},
    {"test_name": "age", "value_numeric": 48, "date_of_test": "2023-06-01"},
]


class TestFeatureEngineering:
    def test_missing_graceful(self):
        from models.health_score.feature_engineering import metrics_to_feature_dict

        fd = metrics_to_feature_dict([])
        assert fd["missing_fraction"] is not None
        assert fd["missing_fraction"] > 0.5

    def test_temporal_slopes(self):
        from models.health_score.feature_engineering import metrics_to_feature_dict

        fd = metrics_to_feature_dict(SAMPLE)
        assert fd["hba1c"] == 6.1
        assert fd["hba1c_slope"] is not None


class TestEngine:
    def test_score_range_and_band(self):
        from models.health_score.infer import HealthScoreEngine

        out = HealthScoreEngine().score(SAMPLE, demographics={"sex": "female"})
        assert out["score"] is not None
        assert 0 <= out["score"] <= 100
        assert out["level"] in ("excellent", "good", "fair", "watch", "elevated")
        assert out["risk_band"]
        assert out["confidence"] is not None
        assert 0.0 <= out["confidence"] <= 1.0

    def test_explanations_present(self):
        from models.health_score.infer import HealthScoreEngine

        out = HealthScoreEngine().score(SAMPLE)
        assert out["top_features"]
        assert out["global_importance"]
        assert out["explanation_method"] in (
            "shap_tree",
            "fallback_centered",
            "linear_coef",
        )
        assert "diagnosis" in out["disclaimer_en"].lower()

    def test_safety_language(self):
        from models.health_score.infer import HealthScoreEngine

        s = HealthScoreEngine().score(SAMPLE)["summary_en"].lower()
        assert "not a medical diagnosis" in s or "estimate only" in s


class TestFeatureFlag:
    def test_flag_off(self, monkeypatch):
        monkeypatch.setenv("USE_HEALTH_SCORE_MODEL", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_health_scorer, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_health_scorer().score(SAMPLE)
        assert r.level == "unavailable"
        assert r.score is None

    def test_flag_on(self, monkeypatch):
        monkeypatch.setenv("USE_HEALTH_SCORE_MODEL", "1")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_health_scorer, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_health_scorer().score(SAMPLE)
        assert r.level != "unavailable"
        assert r.score is not None
        assert r.confidence is not None
        assert r.top_features or r.positive_contributors or r.negative_contributors


class TestSHAP:
    def test_explain_tree_or_fallback(self):
        from models.explainability import explain_tree_model, shap_available
        from models.health_score.infer import HealthScoreEngine
        from models.health_score.schema import FEATURE_COLUMNS
        import numpy as np

        eng = HealthScoreEngine()
        x = np.zeros((1, len(FEATURE_COLUMNS)))
        bundle = explain_tree_model(
            eng.model.raw_model(), x, FEATURE_COLUMNS, background=eng.background
        )
        assert bundle.method in ("shap_tree", "fallback_centered")
        assert bundle.local or bundle.global_importance
        _ = shap_available()  # should not raise


class TestFallback:
    def test_ml_fail(self):
        from services.ai_service.adapters.health_scorer import (
            FallbackHealthScorer,
            UnavailableHealthScorer,
        )

        class Boom:
            def score(self, metrics):
                raise RuntimeError("x")

        fb = FallbackHealthScorer(Boom(), UnavailableHealthScorer())
        r = fb.score(SAMPLE)
        assert r.level == "unavailable"
        assert fb.last_path == "fallback"


class TestRegressors:
    def test_xgboost_or_fallback(self):
        from models.health_score.regressors import create_backend
        import numpy as np

        reg = create_backend("xgboost")
        X = np.random.randn(40, 6)
        y = 70 + X[:, 0] * 3
        reg.fit(X, y)
        assert len(reg.predict(X[:2])) == 2

    def test_lightgbm_or_fallback(self):
        from models.health_score.regressors import create_backend
        import numpy as np

        reg = create_backend("lightgbm")
        X = np.random.randn(40, 6)
        y = 70 + X[:, 0]
        reg.fit(X, y)
        assert len(reg.predict(X[:1])) == 1


class TestPerformance:
    def test_latency(self):
        from models.health_score.infer import HealthScoreEngine

        eng = HealthScoreEngine()
        t0 = time.perf_counter()
        for _ in range(10):
            eng.score(SAMPLE)
        assert (time.perf_counter() - t0) < 20.0


class TestRegression:
    def test_default_flag_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        assert get_feature_flags().use_health_score_model is False

    def test_prior_phases_default_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        f = get_feature_flags()
        assert f.use_unlimited_ocr is False
        assert f.use_risk_model is False
        assert f.use_forecast_model is False


class TestMetrics:
    def test_mae(self):
        from models.health_score.metrics import mae, feature_stability

        assert mae([1, 2], [1, 3]) == 0.5
        assert feature_stability([3, 2, 1], [3, 1, 2]) > 0
