"""Phase 5 — Biomarker forecasting tests."""

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


def _history(n_points: int = 4, start_hba1c: float = 5.8) -> list[dict]:
    base = date(2023, 1, 15)
    rows = []
    for i in range(n_points):
        d = base + timedelta(days=40 * i)
        rows.append(
            {
                "test_name": "HbA1c",
                "value_numeric": round(start_hba1c + 0.1 * i, 2),
                "date_of_test": d.isoformat(),
            }
        )
        rows.append(
            {
                "test_name": "Creatinine",
                "value_numeric": round(1.0 + 0.05 * i, 2),
                "date_of_test": d.isoformat(),
            }
        )
        rows.append(
            {
                "test_name": "age_marker",
                "value_numeric": 45 + i * 0.1,
                "date_of_test": d.isoformat(),
            }
        )
    return rows


class TestFeatureEngineering:
    def test_lags_and_slope(self):
        from models.forecasting.feature_engineering import (
            build_point_features,
            history_to_series,
        )

        series_map = history_to_series(_history(4))
        series = series_map["hba1c"]
        f = build_point_features(series, horizon_days=180, age=50.0, sex_female=0.0)
        assert f["n_obs"] >= 3
        assert f["lag1"] > 0
        assert "slope_per_day" in f

    def test_irregular_intervals(self):
        from models.forecasting.feature_engineering import history_to_series

        hist = [
            {"test_name": "HbA1c", "value_numeric": 5.5, "date_of_test": "2022-01-01"},
            {"test_name": "HbA1c", "value_numeric": 5.7, "date_of_test": "2022-06-15"},
            {"test_name": "HbA1c", "value_numeric": 5.9, "date_of_test": "2023-03-01"},
        ]
        s = history_to_series(hist)["hba1c"]
        assert len(s) == 3
        assert s[0][0] < s[-1][0]


class TestMetrics:
    def test_mae_rmse(self):
        from models.forecasting.metrics import mae, rmse, interval_coverage

        y = [1.0, 2.0, 3.0]
        p = [1.1, 1.9, 3.2]
        assert mae(y, p) < 0.2
        assert rmse(y, p) < 0.3
        assert interval_coverage(y, [0, 1, 2], [2, 3, 4]) == 1.0


class TestEngine:
    def test_loads_and_forecasts(self):
        from models.forecasting.infer import BiomarkerForecastEngine

        eng = BiomarkerForecastEngine()
        out = eng.forecast(
            _history(4),
            horizon_days=180,
            demographics={"age": 48, "sex": "female"},
        )
        assert out["forecasts"]
        hb = next(f for f in out["forecasts"] if f["biomarker_id"] == "hba1c")
        assert hb["predicted_value"] is not None
        assert hb["lower_bound"] is not None
        assert hb["upper_bound"] is not None
        assert hb["lower_bound"] <= hb["upper_bound"]
        assert 0.0 <= hb["confidence"] <= 1.0
        assert hb["trend_direction"] in (
            "increasing",
            "decreasing",
            "stable",
            "unknown",
        )
        assert "diagnosis" not in (out.get("summary_en") or "").lower() or "not a medical diagnosis" in (
            out.get("disclaimer_en") or ""
        ).lower()

    def test_prediction_intervals(self):
        from models.forecasting.infer import BiomarkerForecastEngine

        out = BiomarkerForecastEngine().forecast(_history(5), biomarkers=["hba1c"])
        f = out["forecasts"][0]
        assert f["lower_bound"] is not None and f["upper_bound"] is not None


class TestMissingHistory:
    def test_single_point_still_returns(self):
        from models.forecasting.infer import BiomarkerForecastEngine

        hist = [
            {
                "test_name": "HbA1c",
                "value_numeric": 5.9,
                "date_of_test": "2024-01-01",
            }
        ]
        out = BiomarkerForecastEngine().forecast(hist, biomarkers=["hba1c"])
        assert len(out["forecasts"]) == 1
        f = out["forecasts"][0]
        assert f["current_value"] == 5.9
        # low confidence path or persistence
        assert f["confidence"] <= 0.7 or f["n_history"] < 2

    def test_empty_history(self):
        from models.forecasting.infer import BiomarkerForecastEngine

        out = BiomarkerForecastEngine().forecast([], biomarkers=["creatinine"])
        assert out["forecasts"]
        assert out["forecasts"][0]["predicted_value"] is None or out["forecasts"][0][
            "confidence"
        ] < 0.5


class TestFeatureFlag:
    def test_flag_off_unavailable(self, monkeypatch):
        monkeypatch.setenv("USE_FORECAST_MODEL", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import (
            get_biomarker_forecaster,
            reset_registry_cache,
        )

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_biomarker_forecaster().forecast(_history())
        assert r.method == "unavailable"
        assert r.forecasts == ()

    def test_flag_on_ml(self, monkeypatch):
        monkeypatch.setenv("USE_FORECAST_MODEL", "1")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import (
            get_biomarker_forecaster,
            reset_registry_cache,
        )

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_biomarker_forecaster().forecast(
            _history(4), demographics={"age": 50, "sex": "m"}
        )
        assert r.method != "unavailable"
        assert len(r.forecasts) >= 1
        assert r.forecasts[0].predicted_value is not None
        assert r.forecasts[0].lower_bound is not None
        assert "diagnosis" in r.disclaimer_en.lower() or "forecast" in r.summary_en.lower()


class TestFallback:
    def test_ml_fail(self):
        from services.ai_service.adapters.biomarker_forecaster import (
            FallbackBiomarkerForecaster,
            UnavailableBiomarkerForecaster,
        )

        class Boom:
            def forecast(self, *a, **k):
                raise RuntimeError("x")

        fb = FallbackBiomarkerForecaster(Boom(), UnavailableBiomarkerForecaster())
        r = fb.forecast(_history())
        assert r.method == "unavailable"
        assert fb.last_path == "fallback"


class TestRegressors:
    def test_lightgbm_or_fallback(self):
        from models.forecasting.regressors import create_backend, describe_backends

        b = describe_backends()
        assert b["linear_regression"] is True
        reg = create_backend("lightgbm")
        import numpy as np

        X = np.random.randn(30, 8)
        y = X[:, 0] * 2 + 0.1
        reg.fit(X, y)
        p = reg.predict(X[:3])
        assert len(p) == 3

    def test_xgboost_or_fallback(self):
        from models.forecasting.regressors import create_backend
        import numpy as np

        reg = create_backend("xgboost")
        X = np.random.randn(30, 8)
        y = X[:, 0] * 2
        reg.fit(X, y)
        assert len(reg.predict(X[:2])) == 2

    def test_linear_baseline(self):
        from models.forecasting.regressors import create_backend
        import numpy as np

        reg = create_backend("linear")
        assert reg.name == "linear_regression"
        X = np.random.randn(40, 5)
        y = X.sum(axis=1)
        reg.fit(X, y)
        assert reg.predict(X[:1]).shape == (1,)


class TestPerformance:
    def test_latency(self):
        from models.forecasting.infer import BiomarkerForecastEngine

        eng = BiomarkerForecastEngine()
        hist = _history(5)
        t0 = time.perf_counter()
        for _ in range(10):
            eng.forecast(hist, horizon_days=180)
        assert (time.perf_counter() - t0) < 15.0


class TestRegression:
    def test_default_flag_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        assert get_feature_flags().use_forecast_model is False

    def test_phases_untouched(self):
        """OCR/normalizer/retrieval/risk flags still default off."""
        from services.ai_service.core.feature_flags import get_feature_flags

        f = get_feature_flags()
        assert f.use_unlimited_ocr is False
        assert f.use_ml_normalizer is False
        assert f.use_embedding_search is False
        assert f.use_risk_model is False


class TestDataset:
    def test_synthetic_generation(self):
        from models.forecasting.dataset import ensure_dataset_files, supervised_from_patients, load_train_patients

        paths = ensure_dataset_files()
        assert paths["train"].exists()
        pts = load_train_patients()
        assert len(pts) >= 10
        X, y = supervised_from_patients(pts[:20], horizon_days=180)
        assert X
        assert any(len(v) >= 5 for v in y.values())
