"""Phase 8 — Document image quality tests."""

from __future__ import annotations

import io
import time

import numpy as np
import pytest

try:
    from PIL import Image
except ImportError:
    Image = None


@pytest.fixture(autouse=True)
def _reset():
    from services.ai_service.core.feature_flags import reset_feature_flags_cache
    from services.ai_service.core.registry import reset_registry_cache

    reset_feature_flags_cache()
    reset_registry_cache()
    yield
    reset_feature_flags_cache()
    reset_registry_cache()


def _png_bytes(arr: np.ndarray) -> bytes:
    assert Image is not None
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


class TestAugmentations:
    def test_degrade_blur(self):
        from models.image_quality.augmentations import (
            apply_degradation,
            make_clean_lab_image,
        )

        rng = np.random.default_rng(0)
        clean = make_clean_lab_image(rng)
        img, labels = apply_degradation(clean, "blurry", rng)
        assert img.shape == clean.shape
        assert "blurry" in labels


class TestFeatures:
    def test_opencv_rules_blur(self):
        from models.image_quality.augmentations import apply_degradation, make_clean_lab_image
        from models.image_quality.features import compute_features, opencv_rule_predict

        rng = np.random.default_rng(1)
        clean = make_clean_lab_image(rng)
        blur, _ = apply_degradation(clean, "out_of_focus", rng)
        r = opencv_rule_predict(compute_features(blur))
        assert r["quality_score"] < 90


class TestEngine:
    def test_assess_clean_and_blur(self):
        from models.image_quality.augmentations import apply_degradation, make_clean_lab_image
        from models.image_quality.infer import ImageQualityEngine

        eng = ImageQualityEngine()
        rng = np.random.default_rng(2)
        clean = make_clean_lab_image(rng)
        out_c = eng.assess_array(clean)
        assert 0 <= out_c["quality_score"] <= 100
        assert out_c["recommendation"]

        blur, _ = apply_degradation(clean, "blurry", rng)
        out_b = eng.assess_array(blur)
        assert out_b["quality_score"] <= out_c["quality_score"] + 5


class TestBackends:
    def test_mobilenet_or_proxy(self):
        from models.image_quality.backends import create_backend
        from models.image_quality.dataset import load_train_arrays

        imgs, X, y = load_train_arrays(n=40)
        m = create_backend("mobilenet_v3", seed=0, epochs=1)
        m.fit(X, y, images=None)  # feature path for speed
        p = m.predict_proba(X[:3])
        assert p.shape[0] == 3
        assert m.name in ("mobilenet_v3",) or "mobilenet" in m.name

    def test_efficientnet_or_proxy(self):
        from models.image_quality.backends import create_backend
        from models.image_quality.dataset import load_train_arrays

        _, X, y = load_train_arrays(n=30)
        m = create_backend("efficientnet_lite0", seed=0, epochs=1)
        m.fit(X, y, images=None)
        assert m.predict_proba(X[:2]).shape[0] == 2

    def test_opencv_backend(self):
        from models.image_quality.backends import create_backend
        from models.image_quality.dataset import load_train_arrays

        _, X, y = load_train_arrays(n=20)
        m = create_backend("opencv_rules")
        m.fit(X, y)
        assert m.predict_proba(X[:1]).shape[1] > 1


class TestFeatureFlag:
    def test_off_passthrough(self, monkeypatch):
        monkeypatch.setenv("USE_IMAGE_QUALITY_MODEL", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_quality_checker, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        r = get_quality_checker().check(b"%PDF-1.4 dummy", "application/pdf")
        assert r.ok is True
        assert r.metadata.get("method") == "passthrough"

    def test_on_ml(self, monkeypatch):
        if Image is None:
            pytest.skip("Pillow required")
        monkeypatch.setenv("USE_IMAGE_QUALITY_MODEL", "1")
        from models.image_quality.augmentations import make_clean_lab_image
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_quality_checker, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        rng = np.random.default_rng(3)
        r = get_quality_checker().check(_png_bytes(make_clean_lab_image(rng)), "image/png")
        assert r.score is not None
        assert r.metadata.get("method") != "passthrough"


class TestFallback:
    def test_ml_fail(self):
        from services.ai_service.adapters.quality_checker import (
            FallbackQualityChecker,
            PassThroughQualityChecker,
        )

        class Boom:
            def check(self, *a, **k):
                raise RuntimeError("x")

        fb = FallbackQualityChecker(Boom(), PassThroughQualityChecker())
        r = fb.check(b"x", "image/jpeg")
        assert r.ok is True
        assert fb.last_path == "fallback"


class TestPerformance:
    def test_latency(self):
        from models.image_quality.augmentations import make_clean_lab_image
        from models.image_quality.infer import ImageQualityEngine

        eng = ImageQualityEngine()
        img = make_clean_lab_image(np.random.default_rng(4))
        t0 = time.perf_counter()
        for _ in range(10):
            eng.assess_array(img)
        assert (time.perf_counter() - t0) < 30.0


class TestRegression:
    def test_default_flag_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        assert get_feature_flags().use_image_quality_model is False

    def test_prior_flags(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        f = get_feature_flags()
        assert f.use_anomaly_model is False
        assert f.use_unlimited_ocr is False
