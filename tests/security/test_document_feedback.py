"""No silent empty success, unsafe upstream messages, or text truncation."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from services.ai_service.routers import parse
from services.ai_service.ocr.tesseract_backend import TesseractBackend


@pytest.mark.asyncio
@pytest.mark.parametrize('text,code', [('', 'unreadable'), (' ' * 100, 'unreadable'), ('x' * 100001, 'too_much_text')], ids=['empty','whitespace','oversized'])
async def test_empty_or_excessive_text_is_explicit_failure(monkeypatch, text, code):
    monkeypatch.setattr(TesseractBackend, 'extract_text', lambda *args: text)
    with pytest.raises(HTTPException) as error:
        await parse.read_review_text(b'synthetic', 'image/png')
    assert error.value.detail == {'code': code}


@pytest.mark.asyncio
async def test_parser_without_lab_fields_preserves_review_text(monkeypatch, tmp_path):
    path = tmp_path/'synthetic.txt'
    path.write_bytes(b'synthetic document')
    monkeypatch.setattr(parse, 'get_quality_checker', lambda: SimpleNamespace(check=lambda *args: SimpleNamespace(ok=True)))
    monkeypatch.setattr(parse, 'get_document_parser', lambda: SimpleNamespace(parse_as_legacy=lambda *args: []))
    monkeypatch.setattr(parse, 'read_review_text', AsyncMock(return_value='Fictional prescription text'))
    response = await parse.parse_report(parse.ParseRequest(report_id='synthetic',owner_id='synthetic',
        storage_path=str(path),mime_type='application/pdf',document_kind='report'),None,
        SimpleNamespace(storage_root=tmp_path,file_encryption_key=''))
    assert response.values == []
    assert response.extracted_text == 'Fictional prescription text'
    assert 'no supported lab measurements' in response.processing_note


@pytest.mark.asyncio
async def test_parser_error_does_not_expose_private_content(monkeypatch):
    def fail(*args):
        raise ValueError('secret document path and health information')
    monkeypatch.setattr(TesseractBackend, 'extract_text', fail)
    with pytest.raises(HTTPException) as error:
        await parse.read_review_text(b'synthetic', 'image/png')
    assert error.value.detail == {'code': 'invalid_document'}
