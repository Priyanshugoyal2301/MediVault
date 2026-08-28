"""Phase 1A hardening tests — fallback, backend safety, integration-style probes."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

SAMPLE_LAB = """
Haemoglobin : 13.5 g/dL (12.0-17.0)
WBC : 7200 /uL (4000-11000)
"""


def _png(size=(100, 80), color=(250, 250, 250)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, format="PNG")
    return b.getvalue()


def _jpeg() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (90, 70), (240, 240, 240)).save(b, format="JPEG")
    return b.getvalue()


def _multipage_pdf() -> bytes:
    import fitz

    doc = fitz.open()
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i+1}\nHaemoglobin : 1{i}.5 g/dL")
    data = doc.tobytes()
    doc.close()
    return data


class TestConfigValidation:
    def test_invalid_backend(self):
        from models.ocr.config_loader import UnlimitedOCRConfigError, validate_config

        with pytest.raises(UnlimitedOCRConfigError):
            validate_config({"backend": "bogus", "http": {"timeout_s": 30}, "local": {}})

    def test_http_requires_endpoint(self):
        from models.ocr.config_loader import UnlimitedOCRConfigError, validate_config

        with pytest.raises(UnlimitedOCRConfigError):
            validate_config({"backend": "http", "http": {"endpoint": "", "timeout_s": 30}, "local": {}})

    def test_local_requires_allow_flag(self):
        from models.ocr.config_loader import UnlimitedOCRConfigError, validate_config

        with pytest.raises(UnlimitedOCRConfigError):
            validate_config(
                {
                    "backend": "local",
                    "http": {"timeout_s": 30},
                    "local": {"allow_local_weights": False},
                }
            )

    def test_auto_without_endpoint_readiness(self):
        from models.ocr.config_loader import readiness_check

        r = readiness_check(
            {
                "backend": "auto",
                "http": {"endpoint": "", "timeout_s": 30},
                "local": {},
            }
        )
        assert r["ready"] is False
        assert r["mode"] == "auto-unready"


class TestAutoNeverLoadsLocal:
    def test_auto_without_endpoint_raises_not_local(self):
        from models.ocr.client import UnlimitedOCRClient, UnlimitedOCRError
        from models.ocr.preprocess import PageImage
        from PIL import Image

        client = UnlimitedOCRClient(
            {"backend": "auto", "http": {"endpoint": ""}, "local": {}}
        )
        page = PageImage(
            image=Image.new("RGB", (40, 40), (255, 255, 255)),
            page_number=1,
            source_mime="image/png",
        )
        with pytest.raises(UnlimitedOCRError) as ei:
            client.run([page])
        assert "local" not in str(ei.value).lower() or "no" in str(ei.value).lower()
        assert client._resolve_backends() == []


class TestFallbackEmptyAndCrash:
    def test_empty_structured_triggers_legacy(self):
        from services.ai_service.adapters.document_parser import FallbackDocumentParser

        class PrimaryEmpty:
            last_medical_json = None

            def parse_as_legacy(self, *a, **k):
                return []

        class LegacySpy:
            called = False

            def parse_as_legacy(self, *a, **k):
                LegacySpy.called = True
                from services.ai_service.parsers.report_parser import ReportParser

                class _P:
                    def extract_text(self, b, m):
                        return SAMPLE_LAB

                return ReportParser(_P()).parse(b"x", "text/plain")

        fb = FallbackDocumentParser(PrimaryEmpty(), LegacySpy())
        out = fb.parse_as_legacy(_png(), "image/png")
        assert fb.last_path == "legacy_fallback"
        assert LegacySpy.called is True
        assert any(v.test_name == "Haemoglobin" for v in out)
        assert fb.last_request_log.get("fallback_triggered") is True

    def test_exception_triggers_legacy(self):
        from services.ai_service.adapters.document_parser import FallbackDocumentParser

        class Boom:
            last_medical_json = None

            def parse_as_legacy(self, *a, **k):
                raise TimeoutError("simulated timeout")

        class LegacyOK:
            def parse_as_legacy(self, *a, **k):
                from services.ai_service.parsers.report_parser import ReportParser

                class _P:
                    def extract_text(self, b, m):
                        return SAMPLE_LAB

                return ReportParser(_P()).parse(b"x", "text/plain")

        fb = FallbackDocumentParser(Boom(), LegacyOK())
        out = fb.parse_as_legacy(_png(), "image/png")
        assert fb.last_path == "legacy_fallback"
        assert "TimeoutError" in (fb.last_error or "")
        assert len(out) >= 1


class TestUnlimitedEmptyLabRaises:
    def test_empty_lab_is_failure(self):
        from models.ocr.client import OCRPageResult
        from models.ocr.config_loader import load_config
        from models.ocr.infer import UnlimitedOCRParser
        from models.ocr.client import UnlimitedOCRError

        cfg = load_config(validate=False)
        cfg["backend"] = "stub"
        cfg["treat_empty_lab_as_failure"] = True
        cfg["http"] = {"timeout_s": 30, "endpoint": ""}
        cfg["local"] = {"allow_local_weights": False}
        # fix validation for stub
        from models.ocr.config_loader import validate_config

        validate_config(cfg)

        parser = UnlimitedOCRParser(config=cfg)

        def _fake_run(pages):
            return [
                OCRPageResult(page_number=1, raw_text="no lab numbers here", ocr_confidence=0.5)
            ]

        parser._client.run = _fake_run  # type: ignore[method-assign]
        with pytest.raises(UnlimitedOCRError) as ei:
            parser.parse_document(_png(), "image/png")
        assert "Empty structured" in str(ei.value)


class TestHTTPMalformedJson:
    def test_malformed_json_raises(self):
        from models.ocr.client import UnlimitedOCRClient, UnlimitedOCRError
        from models.ocr.preprocess import PageImage
        from PIL import Image
        from unittest.mock import MagicMock

        client = UnlimitedOCRClient(
            {
                "backend": "http",
                "http": {
                    "endpoint": "http://127.0.0.1:9/v1/chat/completions",
                    "timeout_s": 1,
                },
                "local": {},
            }
        )
        page = PageImage(
            image=Image.new("RGB", (20, 20)),
            page_number=1,
            source_mime="image/png",
        )

        class Resp:
            def read(self):
                return b"not-json{"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with patch("models.ocr.client.urlrequest.urlopen", return_value=Resp()):
            with pytest.raises(UnlimitedOCRError) as ei:
                client._run_http([page])
            assert "malformed JSON" in str(ei.value)


class TestFormatsAndMultiPage:
    def test_png_jpeg_preprocess(self):
        from models.ocr.preprocess import preprocess_document

        assert len(preprocess_document(_png(), "image/png")) == 1
        assert len(preprocess_document(_jpeg(), "image/jpeg")) == 1

    def test_multipage_pdf_preprocess(self):
        from models.ocr.preprocess import preprocess_document

        pages = preprocess_document(_multipage_pdf(), "application/pdf")
        assert len(pages) == 2

    def test_corrupt_and_empty(self):
        from models.ocr.preprocess import preprocess_document
        from models.ocr.infer import UnlimitedOCRParser
        from models.ocr.client import UnlimitedOCRError
        from models.ocr.config_loader import load_config, validate_config

        with pytest.raises(Exception):
            preprocess_document(b"NOTANIMAGE", "image/png")

        cfg = load_config(validate=False)
        cfg["backend"] = "stub"
        cfg["http"] = {"timeout_s": 30, "endpoint": ""}
        cfg["local"] = {}
        validate_config(cfg)
        with pytest.raises(UnlimitedOCRError):
            UnlimitedOCRParser(cfg).parse_document(b"", "image/png")

    def test_large_image_preprocess_resizes(self):
        from models.ocr.preprocess import preprocess_document

        pages = preprocess_document(
            _png(size=(4000, 3000)),
            "image/png",
            config={"max_page_side": 800, "enable_deskew": False},
        )
        assert max(pages[0].image.size) <= 800


class TestFeatureFlagStillWorks:
    def test_flag_off_legacy(self, monkeypatch):
        monkeypatch.setenv("USE_UNLIMITED_OCR", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import (
            get_document_parser,
            reset_registry_cache,
        )

        reset_feature_flags_cache()
        reset_registry_cache()
        assert get_document_parser().__class__.__name__ == "RegexDocumentParser"
        monkeypatch.setenv("USE_UNLIMITED_OCR", "0")
        reset_feature_flags_cache()
        reset_registry_cache()


class TestEndToEndFallbackChain:
    """Simulates backend unavailable → fallback → labs extracted by legacy."""

    def test_auto_unavailable_via_fallback_parser(self):
        from models.ocr.config_loader import load_config, validate_config
        from models.ocr.infer import UnlimitedOCRParser
        from services.ai_service.adapters.document_parser import (
            FallbackDocumentParser,
            UnlimitedOCRDocumentParser,
        )
        from services.ai_service.parsers.report_parser import ReportParser

        cfg = load_config(validate=False)
        cfg["backend"] = "auto"
        cfg["http"] = {"endpoint": "", "timeout_s": 5}
        cfg["local"] = {"allow_local_weights": False}
        validate_config(cfg)

        primary = UnlimitedOCRDocumentParser(config=cfg)

        class TextLegacy:
            def parse_as_legacy(self, file_bytes, mime_type):
                class _P:
                    def extract_text(self, b, m):
                        return SAMPLE_LAB

                return ReportParser(_P()).parse(b"x", "text/plain")

            def parse(self, *a, **k):
                return []

        fb = FallbackDocumentParser(primary, TextLegacy())
        out = fb.parse_as_legacy(_png(), "image/png")
        assert fb.last_path == "legacy_fallback"
        assert any(getattr(v, "test_name", None) == "Haemoglobin" for v in out)


class TestLegacyIndependence:
    def test_compatibility_values_no_service_import_needed(self):
        from models.ocr.postprocess import (
            medical_json_to_legacy_values,
            postprocess_to_medical_json,
        )

        doc = postprocess_to_medical_json([(1, SAMPLE_LAB)], backend="test")
        vals = medical_json_to_legacy_values(doc)
        assert vals
        assert vals[0].test_name
        assert hasattr(vals[0], "value_numeric")
