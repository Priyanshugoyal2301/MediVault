"""Phase 4 — Disease risk prediction tests."""

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


SAMPLE_METRICS = [
    {"test_name": "Haemoglobin", "value_numeric": 10.2},
    {"test_name": "HbA1c", "value_numeric": 7.8},
    {"test_name": "Creatinine", "value_numeric": 1.8},
    {"test_name": "ALT", "value_numeric": 90},
    {"test_name": "TSH", "value_numeric": 8.5},
    {"test_name": "Fasting Glucose", "value_numeric": 140},
]


class TestPreprocess:
    def test_missing_graceful(self):
        from models.risk_prediction.preprocess import metrics_to_feature_dict

        fd = metrics_to_feature_dict([])
        assert fd["missing_fraction"] is not None
        assert fd["missing_fraction"] > 0.5


class TestEngine:
    def test_loads_and_predicts(self):
        from models.risk_prediction.infer import DiseaseRiskEngine

        eng = DiseaseRiskEngine()
        conds = eng.predict_conditions(
            SAMPLE_METRICS, demographics={"age": 55, "sex": "female"}
        )
        assert len(conds) == 5
        for c in conds:
            assert 0.0 <= c.risk_probability <= 1.0
            assert c.risk_category in ("low", "moderate", "high")
            assert 0.0 <= c.confidence <= 1.0

    def test_summary_safety_language(self):
        from models.risk_prediction.infer import DiseaseRiskEngine

        s = DiseaseRiskEngine().predict_summary(SAMPLE_METRICS)
        text = s["summary_en"].lower()
        assert "risk estimate only" in text or "not a medical diagnosis" in text
        assert "you have diabetes" not in text
        assert s["risk_score"] is not None

    def test_confidence_present(self):
        from models.risk_prediction.infer import DiseaseRiskEngine

        c = DiseaseRiskEngine().predict_conditions(SAMPLE_METRICS)[0]
        assert c.confidence >= 0.35


class TestFeatureFlag:
    def test_flag_off_unavailable(self, monkeypatch):
        monkeypatch.setenv("USE_RISK_MODEL", "0")
        monkeypatch.delenv("USE_DISEASE_RISK_MODEL", raising=False)
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_risk_predictor, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_risk_predictor().predict(SAMPLE_METRICS)
        assert r.risk_band == "unavailable"

    def test_flag_on_ml(self, monkeypatch):
        monkeypatch.setenv("USE_RISK_MODEL", "1")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_risk_predictor, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_risk_predictor().predict(SAMPLE_METRICS)
        assert r.risk_band != "unavailable"
        assert r.risk_score is not None
        assert "diagnosis" in r.summary_en.lower() or "risk" in r.summary_en.lower()
        assert r.conditions

    def test_alias_flag(self, monkeypatch):
        monkeypatch.setenv("USE_RISK_MODEL", "0")
        monkeypatch.setenv("USE_DISEASE_RISK_MODEL", "1")
        from services.ai_service.core.feature_flags import (
            get_feature_flags,
            reset_feature_flags_cache,
        )

        reset_feature_flags_cache()
        assert get_feature_flags().use_risk_model is True


class TestRuleBaseline:
    def test_rule_predictor(self):
        from services.ai_service.adapters.risk_predictor import RuleBasedRiskPredictor

        r = RuleBasedRiskPredictor().predict(SAMPLE_METRICS)
        assert r.method == "rule_thresholds"
        assert "not a medical diagnosis" in r.summary_en.lower()


class TestFallback:
    def test_ml_fail(self):
        from services.ai_service.adapters.risk_predictor import (
            FallbackRiskPredictor,
            UnavailableRiskPredictor,
        )

        class Boom:
            def predict(self, metrics):
                raise RuntimeError("x")

        fb = FallbackRiskPredictor(Boom(), UnavailableRiskPredictor())
        r = fb.predict(SAMPLE_METRICS)
        assert r.risk_band == "unavailable"
        assert fb.last_path == "fallback"


class TestPerformance:
    def test_latency(self):
        from models.risk_prediction.infer import DiseaseRiskEngine

        eng = DiseaseRiskEngine()
        t0 = time.perf_counter()
        for _ in range(20):
            eng.predict_conditions(SAMPLE_METRICS)
        assert (time.perf_counter() - t0) < 10.0


class TestCalibrationHelpers:
    def test_ece(self):
        from models.risk_prediction.metrics import expected_calibration_error, roc_auc

        y = [0, 0, 1, 1]
        p = [0.1, 0.2, 0.8, 0.9]
        assert expected_calibration_error(y, p) < 0.5
        assert roc_auc(y, p) > 0.9


class TestRegression:
    def test_default_flag_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        assert get_feature_flags().use_risk_model is False

    def test_ml_infra_unavailable(self):
        from services.ai_service.core.registry import get_risk_predictor, reset_registry_cache

        reset_registry_cache()
        assert get_risk_predictor().predict([]).risk_band == "unavailable"
