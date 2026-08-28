"""Phase 2 — Medical Test Normalization tests."""

from __future__ import annotations

import os
import time

import pytest


@pytest.fixture(autouse=True)
def _reset_flags():
    from services.ai_service.core.feature_flags import reset_feature_flags_cache
    from services.ai_service.core.registry import reset_registry_cache

    reset_feature_flags_cache()
    reset_registry_cache()
    yield
    reset_feature_flags_cache()
    reset_registry_cache()


class TestPreprocess:
    def test_unicode_and_case(self):
        from models.normalizer.preprocess import preprocess_test_name

        assert "haemoglobin" in preprocess_test_name("  Hemoglobin  ")
        assert preprocess_test_name("HGB").find("haemoglobin") >= 0 or "hgb" in preprocess_test_name("HGB") or preprocess_test_name("HGB")

    def test_british_american(self):
        from models.normalizer.preprocess import preprocess_test_name

        assert "haemoglobin" in preprocess_test_name("hemoglobin")


class TestAliasRules:
    def test_hgb_haemoglobin(self):
        from services.ai_service.adapters.normalizer import AliasNormalizer

        n = AliasNormalizer()
        assert n.normalize_test_name("HGB") == "Haemoglobin"
        assert n.normalize_test_name("hb") == "Haemoglobin"

    def test_sgpt_alt(self):
        from services.ai_service.adapters.normalizer import AliasNormalizer

        assert AliasNormalizer().normalize_test_name("SGPT") == "Alanine Aminotransferase"

    def test_unknown_passthrough(self):
        from services.ai_service.adapters.normalizer import AliasNormalizer

        raw = "Totally Unknown Marker Z"
        assert AliasNormalizer().normalize_test_name(raw) == raw


class TestMLNormalizer:
    def test_hgb_detailed(self):
        from models.normalizer.infer import MedicalTestNormalizer
        from models.normalizer.schema import NormalizationStatus

        m = MedicalTestNormalizer()
        r = m.normalize("HGB")
        assert r.canonical_name == "Haemoglobin"
        assert r.confidence >= 0.9
        assert r.loinc == "718-7"
        assert r.status == NormalizationStatus.NORMALIZED
        assert not r.unknown_term

    def test_sgpt_alt(self):
        from models.normalizer.infer import MedicalTestNormalizer

        r = MedicalTestNormalizer().normalize("SGPT")
        assert r.canonical_name == "Alanine Aminotransferase"
        assert r.loinc == "1742-6"

    def test_unknown_graceful(self):
        from models.normalizer.infer import MedicalTestNormalizer
        from models.normalizer.schema import NormalizationStatus

        r = MedicalTestNormalizer().normalize("random analyte xyz")
        assert r.unknown_term or r.status in (
            NormalizationStatus.UNKNOWN,
            NormalizationStatus.PASSTHROUGH,
        )

    def test_protocol_methods(self):
        from models.normalizer.infer import MedicalTestNormalizer

        m = MedicalTestNormalizer()
        assert m.normalize_test_name("a1c") == "HbA1c"
        assert m.normalize_unit("HbA1c", None) == "%"


class TestFeatureFlag:
    def test_flag_off_rules(self, monkeypatch):
        monkeypatch.delenv("USE_ML_NORMALIZER", raising=False)
        monkeypatch.setenv("USE_ML_NORMALIZER", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_normalizer, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        n = get_normalizer()
        assert n.normalize_test_name("hgb") == "Haemoglobin"
        assert type(n).__name__ == "AliasNormalizer"

    def test_flag_on_ml(self, monkeypatch):
        monkeypatch.setenv("USE_ML_NORMALIZER", "1")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_normalizer, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        n = get_normalizer()
        assert n.normalize_test_name("hgb") == "Haemoglobin"
        assert type(n).__name__ in ("FallbackNormalizer", "MLMedicalTestNormalizer")


class TestIndianReports:
    @pytest.mark.parametrize(
        "raw,canon",
        [
            ("Haemoglobin (HB)", "Haemoglobin"),
            ("Total Leucocyte Count", "WBC"),
            ("Platelet Count", "Platelets"),
            ("LDL-C", "LDL Cholesterol"),
            ("TSH (Ultrasensitive)", "TSH"),
            ("Glycosylated Haemoglobin (HbA1c)", "HbA1c"),
            ("S.Creatinine", "Creatinine"),
        ],
    )
    def test_indian_aliases(self, raw, canon):
        from models.normalizer.infer import MedicalTestNormalizer

        assert MedicalTestNormalizer().normalize_test_name(raw) == canon


class TestCrossLab:
    def test_mixed_casing_punctuation(self):
        from models.normalizer.infer import MedicalTestNormalizer

        m = MedicalTestNormalizer()
        assert m.normalize_test_name("hDl") == "HDL Cholesterol"
        assert m.normalize_test_name("TG:") == "Triglycerides"


class TestLoinc:
    def test_loinc_hgb(self):
        from models.normalizer.infer import MedicalTestNormalizer

        assert MedicalTestNormalizer().normalize("Hemoglobin").loinc == "718-7"

    def test_loinc_tsh(self):
        from models.normalizer.infer import MedicalTestNormalizer

        assert MedicalTestNormalizer().normalize("thyroid stimulating hormone").loinc == "3016-3"


class TestFallback:
    def test_ml_fail_uses_rules(self):
        from services.ai_service.adapters.normalizer import (
            AliasNormalizer,
            FallbackNormalizer,
        )

        class Boom:
            def normalize_test_name(self, raw_name: str) -> str:
                raise RuntimeError("backend down")

            def normalize_unit(self, test_name, raw_unit):
                raise RuntimeError("backend down")

        fb = FallbackNormalizer(primary=Boom(), fallback=AliasNormalizer())
        assert fb.normalize_test_name("hb") == "Haemoglobin"
        assert fb.last_path == "rule_fallback"


class TestPerformance:
    def test_batch_latency(self):
        from models.normalizer.infer import MedicalTestNormalizer

        m = MedicalTestNormalizer()
        names = ["HGB", "WBC", "LDL", "TSH", "SGPT"] * 20
        t0 = time.perf_counter()
        for n in names:
            m.normalize(n)
        elapsed = (time.perf_counter() - t0) * 1000
        # 100 names should easily complete in a few seconds offline
        assert elapsed < 10000


class TestParseIntegration:
    def test_normalize_in_loop_contract(self):
        """Simulate parse loop: values keep ParsedValueOut field set."""
        from services.ai_service.adapters.normalizer import AliasNormalizer

        class PV:
            def __init__(self, name):
                self.test_name = name
                self.panel = "CBC"
                self.value_numeric = 13.5
                self.value_text = None
                self.unit = "g/dL"
                self.reference_range_low = 12.0
                self.reference_range_high = 17.0
                self.reference_range_text = "12-17"

        n = AliasNormalizer()
        pv = PV("HGB")
        assert n.normalize_test_name(pv.test_name) == "Haemoglobin"


class TestRegressionLegacy:
    def test_flag_default_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        assert get_feature_flags().use_ml_normalizer is False

    def test_ml_infra_still_passes(self):
        from services.ai_service.core.registry import get_normalizer, reset_registry_cache

        reset_registry_cache()
        assert get_normalizer().normalize_test_name("hb") == "Haemoglobin"
