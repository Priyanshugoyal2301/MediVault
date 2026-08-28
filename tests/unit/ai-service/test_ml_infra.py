"""Unit tests for ML feature flags + registry defaults (Phase 0)."""

from __future__ import annotations


def test_feature_flags_default_off():
    from services.ai_service.core.feature_flags import (
        reset_feature_flags_cache,
        get_feature_flags,
    )

    reset_feature_flags_cache()
    flags = get_feature_flags()
    assert flags.use_unlimited_ocr is False
    assert flags.use_ml_normalizer is False
    assert flags.use_risk_model is False
    assert flags.use_forecast_model is False
    assert flags.use_embedding_search is False
    assert flags.use_health_score_model is False
    assert flags.use_anomaly_model is False
    assert flags.use_outlier_model is False
    assert flags.use_image_quality_model is False


def test_registry_returns_default_adapters():
    from services.ai_service.core.registry import (
        reset_registry_cache,
        get_document_parser,
        get_anomaly_detector,
        get_retriever,
        get_quality_checker,
        get_normalizer,
        get_risk_predictor,
        get_biomarker_forecaster,
        get_health_scorer,
    )

    reset_registry_cache()
    assert get_document_parser() is not None
    assert get_anomaly_detector() is not None
    assert get_retriever() is not None
    assert get_quality_checker().check(b"%PDF", "application/pdf").ok is True
    assert get_normalizer().normalize_test_name("hb") == "Haemoglobin"
    assert get_risk_predictor().predict([]).risk_band == "unavailable"
    assert get_biomarker_forecaster().forecast([]).method == "unavailable"
    assert get_health_scorer().score([]).level == "unavailable"


def test_statistical_anomaly_adapter_matches_detector():
    from datetime import date, timedelta

    from services.ai_service.anomaly.detector import detect
    from services.ai_service.adapters.anomaly_detector import StatisticalAnomalyDetector

    base = date(2024, 1, 1)
    pts = [(base + timedelta(days=i * 30), 13.0 + 0.05 * i) for i in range(5)]
    direct = detect("Haemoglobin", pts, unit="g/dL")
    via = StatisticalAnomalyDetector().detect("Haemoglobin", pts, unit="g/dL")
    assert via.trend == direct.trend
    assert via.is_anomaly == direct.is_anomaly
    assert via.method == direct.method
    assert abs(via.anomaly_score - direct.anomaly_score) < 1e-9


def test_ml_eval_classify_metrics():
    from packages.ml_eval import classify_metrics

    m = classify_metrics([True, True, False, False], [True, False, False, False])
    assert "precision" in m and "recall" in m and "f1" in m and "accuracy" in m
    assert m["accuracy"] == 0.75
