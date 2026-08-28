"""
UnlimitedOCRParser — DocumentParser (Phase 1 / 1A).

Phase 1A: structured empty results raise UnlimitedOCRError → outer fallback to legacy.
Structured logging: backend, duration, confidence, status.
"""

from __future__ import annotations

import time
from typing import Any

from packages.shared_utils import get_logger

from .client import UnlimitedOCRClient, UnlimitedOCRError
from .config_loader import describe_config, load_config
from .postprocess import (
    medical_json_to_legacy_values,
    medical_json_to_parsed_fields,
    postprocess_to_medical_json,
)
from .preprocess import preprocess_document
from .schema import MedicalDocumentJSON

logger = get_logger(__name__)


class UnlimitedOCRParser:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config if config is not None else load_config(validate=True)
        self._client = UnlimitedOCRClient(self.config)
        self._last_medical_json: MedicalDocumentJSON | None = None
        self.last_log: dict[str, Any] = {}

    @property
    def last_medical_json(self) -> MedicalDocumentJSON | None:
        return self._last_medical_json

    def parse_document(self, file_bytes: bytes, mime_type: str) -> MedicalDocumentJSON:
        t0 = time.perf_counter()
        cfg_summary = describe_config(self.config)
        logger.info(
            "OCR request start backend_config=%s mime=%s size_bytes=%s",
            cfg_summary.get("backend"),
            mime_type,
            len(file_bytes) if file_bytes else 0,
        )

        if not file_bytes:
            self._fail("empty_file_bytes", t0)
            raise UnlimitedOCRError("Empty file_bytes")

        try:
            pre_cfg = self.config.get("preprocess") or {}
            pages = preprocess_document(file_bytes, mime_type, config=pre_cfg)
            ocr_pages = self._client.run(pages)

            page_texts = [(r.page_number, r.raw_text) for r in ocr_pages]
            boxes_by_page = {
                r.page_number: list(r.boxes or []) for r in ocr_pages if r.boxes
            }
            confs = [r.ocr_confidence for r in ocr_pages if r.ocr_confidence is not None]
            mean_ocr = sum(confs) / len(confs) if confs else 0.85

            doc = postprocess_to_medical_json(
                page_texts,
                mime_type=mime_type,
                backend=self._client.last_backend_used or self._client.backend,
                ocr_confidence_default=mean_ocr,
                boxes_by_page=boxes_by_page,
                extra_metadata={
                    "parser": "UnlimitedOCRParser",
                    "hf_model_id": self.config.get("hf_model_id"),
                    "rotation": [p.rotation_applied_deg for p in pages],
                    "deskew": [p.deskew_angle_deg for p in pages],
                    "client_backend": self._client.last_backend_used,
                    "inference_ms": self._client.last_duration_ms,
                },
            )

            # Phase 1A O-07: empty structured lab → fail so Fallback → legacy
            if self.config.get("treat_empty_lab_as_failure", True) and not doc.laboratory:
                self._fail(
                    "empty_structured_laboratory",
                    t0,
                    backend=self._client.last_backend_used,
                    conf=doc.confidence,
                )
                raise UnlimitedOCRError(
                    "Empty structured laboratory extraction from Unlimited-OCR"
                )

            self._last_medical_json = doc
            elapsed = (time.perf_counter() - t0) * 1000.0
            conf = doc.confidence or {}
            self.last_log = {
                "status": "completed",
                "backend_selected": self._client.last_backend_used,
                "inference_duration_ms": self._client.last_duration_ms,
                "total_duration_ms": round(elapsed, 3),
                "fallback_triggered": False,
                "confidence_available": bool(conf),
                "ocr_confidence": conf.get("ocr_confidence"),
                "extraction_confidence": conf.get("extraction_confidence"),
                "lab_count": len(doc.laboratory),
                "failure_reason": None,
            }
            logger.info(
                "OCR request completed backend=%s inference_ms=%s total_ms=%s "
                "lab_count=%s ocr_confidence=%s extraction_confidence=%s",
                self._client.last_backend_used,
                self._client.last_duration_ms,
                round(elapsed, 3),
                len(doc.laboratory),
                conf.get("ocr_confidence"),
                conf.get("extraction_confidence"),
            )
            return doc
        except UnlimitedOCRError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._fail(f"{type(exc).__name__}: {exc}", t0)
            raise UnlimitedOCRError(f"OCR pipeline failed: {exc}") from exc

    def parse(self, file_bytes: bytes, mime_type: str):
        doc = self.parse_document(file_bytes, mime_type)
        return medical_json_to_parsed_fields(doc)

    def parse_as_legacy(self, file_bytes: bytes, mime_type: str):
        doc = self.parse_document(file_bytes, mime_type)
        return medical_json_to_legacy_values(doc)

    def _fail(
        self,
        reason: str,
        t0: float,
        backend: str | None = None,
        conf: dict | None = None,
    ) -> None:
        elapsed = (time.perf_counter() - t0) * 1000.0
        self.last_log = {
            "status": "failed",
            "backend_selected": backend or self._client.last_backend_used,
            "inference_duration_ms": self._client.last_duration_ms,
            "total_duration_ms": round(elapsed, 3),
            "fallback_triggered": True,  # expected at outer FallbackDocumentParser
            "confidence_available": bool(conf),
            "failure_reason": reason,
        }
        logger.warning(
            "OCR request failed reason=%s backend=%s total_ms=%s "
            "(outer fallback expected)",
            reason,
            backend or self._client.last_backend_used,
            round(elapsed, 3),
        )


def create_parser(config: dict[str, Any] | None = None) -> UnlimitedOCRParser:
    return UnlimitedOCRParser(config=config)
