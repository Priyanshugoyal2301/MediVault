"""Phase 1 multipage / image / API contract regression tests."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

SAMPLE = """Haemoglobin : 13.5 g/dL (12.0-17.0)
LDL Cholesterol : 120 mg/dL (0-100)
"""


def test_multipage_client_split():
    from models.ocr.client import UnlimitedOCRClient, OCRPageResult
    from models.ocr.preprocess import PageImage
    from PIL import Image

    cfg = {"backend": "stub", "http": {}, "local": {}}
    client = UnlimitedOCRClient(cfg)
    pages = []
    for i in range(1, 3):
        pages.append(
            PageImage(
                image=Image.new("RGB", (40, 40), (255, 255, 255)),
                page_number=i,
                source_mime="image/png",
                metadata={"stub_text": f"Page {i}\nHaemoglobin : {10 + i}.0 g/dL"},
            )
        )
    results = client.run(pages)
    assert len(results) == 2
    assert results[0].page_number == 1
    assert results[1].page_number == 2


def test_legacy_parser_still_works():
    from services.ai_service.adapters.document_parser import RegexDocumentParser
    from services.ai_service.parsers.report_parser import ReportParser

    class _P:
        def extract_text(self, file_bytes, mime_type):
            return SAMPLE

    vals = ReportParser(_P()).parse(b"x", "text/plain")
    assert any(v.test_name == "Haemoglobin" for v in vals)

    # Adapter path
    parser = RegexDocumentParser(ocr=_P())
    fields = parser.parse(b"x", "text/plain")
    assert any(f.test_name == "Haemoglobin" for f in fields)


def test_parse_response_schema_unchanged():
    """ParseResponse model fields must not gain required keys (API contract)."""
    from services.ai_service.routers.parse import ParseRequest, ParseResponse, ParsedValueOut

    assert set(ParseRequest.model_fields) >= {
        "report_id",
        "owner_id",
        "storage_path",
        "mime_type",
    }
    assert set(ParsedValueOut.model_fields) == {
        "test_name",
        "panel",
        "value_numeric",
        "value_text",
        "unit",
        "reference_range_low",
        "reference_range_high",
        "reference_range_text",
        "status",
        "explanation_en",
        "explanation_hi",
    }
    assert set(ParseResponse.model_fields) == {"report_id", "values"}


def test_tiff_preprocess():
    from models.ocr.preprocess import preprocess_document

    img = Image.new("RGB", (60, 60), (240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="TIFF")
    pages = preprocess_document(buf.getvalue(), "image/tiff")
    assert len(pages) == 1


def test_medical_json_to_legacy_mapping():
    from models.ocr.postprocess import (
        medical_json_to_legacy_values,
        postprocess_to_medical_json,
    )

    doc = postprocess_to_medical_json([(1, SAMPLE)], backend="test")
    legacy = medical_json_to_legacy_values(doc)
    assert legacy
    assert hasattr(legacy[0], "test_name")
    assert hasattr(legacy[0], "value_numeric")
