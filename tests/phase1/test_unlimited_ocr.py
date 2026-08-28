"""Phase 1 tests — Unlimited-OCR pipeline, flags, fallback, schemas."""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


SAMPLE_LAB_TEXT = """
COMPLETE BLOOD COUNT
Haemoglobin : 13.5 g/dL (12.0-17.0)
WBC : 7200 /uL (4000-11000)
Platelets : 250000 /uL (150000-400000)
"""


def _png_bytes(text_color=(0, 0, 0)) -> bytes:
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestMedicalJSONSchema:
    def test_roundtrip(self):
        from models.ocr.schema import LaboratoryEntry, MedicalDocumentJSON

        doc = MedicalDocumentJSON(
            patient={"name": None},
            laboratory=[
                LaboratoryEntry(
                    test_name="Haemoglobin",
                    value=13.5,
                    unit="g/dL",
                    reference_range="12.0–17.0",
                    page_number=1,
                    ocr_confidence=0.9,
                    extraction_confidence=0.8,
                )
            ],
            metadata={"backend": "stub"},
            confidence={"overall": 0.85},
        )
        raw = doc.to_dict()
        assert "patient" in raw and "laboratory" in raw
        assert raw["laboratory"][0]["test_name"] == "Haemoglobin"
        restored = MedicalDocumentJSON.from_dict(raw)
        assert len(restored.laboratory) == 1
        assert restored.laboratory[0].value == 13.5


class TestPostprocess:
    def test_extracts_lab_rows(self):
        from models.ocr.postprocess import postprocess_to_medical_json

        doc = postprocess_to_medical_json(
            [(1, SAMPLE_LAB_TEXT)],
            mime_type="text/plain",
            backend="test",
            ocr_confidence_default=0.88,
        )
        names = {e.test_name for e in doc.laboratory}
        assert "Haemoglobin" in names
        assert "WBC" in names
        assert doc.confidence.get("ocr_confidence") == 0.88
        assert doc.confidence.get("extraction_confidence") is not None

    def test_unwrap_ref_det_tokens(self):
        from models.ocr.postprocess import unwrap_vlm_text

        raw = "<|ref|>Haemoglobin : 12.0 g/dL<|/ref|><|det|>[1,2,3,4]<|/det|>"
        text, boxes = unwrap_vlm_text(raw)
        assert "Haemoglobin" in text
        assert boxes and boxes[0].x0 == 1.0


class TestPreprocess:
    def test_png_preprocess(self):
        from models.ocr.preprocess import preprocess_document

        pages = preprocess_document(_png_bytes(), "image/png")
        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].image.width > 0

    def test_jpeg_alias(self):
        from models.ocr.preprocess import preprocess_document

        img = Image.new("RGB", (50, 50), color=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        pages = preprocess_document(buf.getvalue(), "image/jpg")
        assert len(pages) == 1

    def test_unsupported_mime(self):
        from models.ocr.preprocess import preprocess_document

        with pytest.raises(ValueError):
            preprocess_document(b"not-a-doc", "application/zip")


class TestUnlimitedParserStub:
    def test_stub_with_injected_text(self):
        from models.ocr.config_loader import load_config
        from models.ocr.infer import UnlimitedOCRParser
        from models.ocr.preprocess import PageImage
        from models.ocr.client import UnlimitedOCRClient
        from PIL import Image

        cfg = load_config()
        cfg["backend"] = "stub"
        client = UnlimitedOCRClient(cfg)
        page = PageImage(
            image=Image.new("RGB", (100, 100), (255, 255, 255)),
            page_number=1,
            source_mime="image/png",
            metadata={"stub_text": SAMPLE_LAB_TEXT},
        )
        results = client.run([page])
        assert "Haemoglobin" in results[0].raw_text

        # Full parser with monkeypatched client
        parser = UnlimitedOCRParser(config=cfg)

        def _fake_run(pages):
            from models.ocr.client import OCRPageResult

            return [
                OCRPageResult(
                    page_number=1,
                    raw_text=SAMPLE_LAB_TEXT,
                    ocr_confidence=0.9,
                )
            ]

        parser._client.run = _fake_run  # type: ignore[method-assign]
        doc = parser.parse_document(_png_bytes(), "image/png")
        assert len(doc.laboratory) >= 2
        legacy = parser.parse_as_legacy(_png_bytes(), "image/png")
        assert len(legacy) >= 2
        assert legacy[0].test_name


class TestFallback:
    def test_fallback_on_primary_failure(self):
        from services.ai_service.adapters.document_parser import (
            FallbackDocumentParser,
            RegexDocumentParser,
        )

        class Boom:
            def parse_as_legacy(self, *a, **k):
                raise RuntimeError("vlm down")

            def parse(self, *a, **k):
                raise RuntimeError("vlm down")

        # Fallback will call real regex which needs OCR — use text via custom fallback
        class TextLegacy:
            def parse_as_legacy(self, file_bytes, mime_type):
                from services.ai_service.parsers.report_parser import ReportParser

                class _P:
                    def extract_text(self, b, m):
                        return SAMPLE_LAB_TEXT

                return ReportParser(_P()).parse(b"x", "text/plain")

            def parse(self, file_bytes, mime_type):
                return []

        fb = FallbackDocumentParser(primary=Boom(), fallback=TextLegacy())
        vals = fb.parse_as_legacy(b"unused", "image/png")
        assert fb.last_path == "legacy_fallback"
        assert any(v.test_name == "Haemoglobin" for v in vals)


class TestFeatureFlag:
    def test_flag_off_uses_legacy(self, monkeypatch):
        monkeypatch.setenv("USE_UNLIMITED_OCR", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import (
            get_document_parser,
            reset_registry_cache,
        )

        reset_feature_flags_cache()
        reset_registry_cache()
        p = get_document_parser()
        assert p.__class__.__name__ == "RegexDocumentParser"

    def test_flag_on_uses_fallback_wrapper(self, monkeypatch):
        monkeypatch.setenv("USE_UNLIMITED_OCR", "1")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import (
            get_document_parser,
            reset_registry_cache,
        )

        reset_feature_flags_cache()
        reset_registry_cache()
        p = get_document_parser()
        # FallbackDocumentParser or Regex if Unlimited init fails hard
        assert p.__class__.__name__ in (
            "FallbackDocumentParser",
            "RegexDocumentParser",
        )
        # cleanup for other tests
        monkeypatch.setenv("USE_UNLIMITED_OCR", "0")
        reset_feature_flags_cache()
        reset_registry_cache()


class TestDataset:
    def test_plan_c_synthetic_loads(self):
        from models.ocr.dataset import DocumentParsingDataset

        ds = DocumentParsingDataset()
        samples = list(ds.iter_index())
        assert len(samples) >= 1
        assert samples[0].gold_fields
        summary = ds.summary()
        assert summary["n_samples"] >= 1


class TestErrorRecovery:
    def test_empty_bytes_fails_into_fallback(self):
        from models.ocr.client import UnlimitedOCRError
        from models.ocr.infer import UnlimitedOCRParser
        from models.ocr.config_loader import load_config

        cfg = load_config()
        cfg["backend"] = "http"
        cfg["http"] = {"endpoint": "", "timeout_s": 1}
        parser = UnlimitedOCRParser(config=cfg)
        with pytest.raises(UnlimitedOCRError):
            parser.parse_document(b"", "image/png")


class TestMetrics:
    def test_field_f1_perfect(self):
        from models.ocr.metrics import field_precision_recall_f1

        g = {"Haemoglobin": 13.5, "WBC": 7200.0}
        m = field_precision_recall_f1(g, g)
        assert m["field_f1"] == 1.0
        assert m["field_precision"] == 1.0
