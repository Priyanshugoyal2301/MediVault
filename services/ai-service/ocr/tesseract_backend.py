"""
ai-service/ocr/tesseract_backend.py

Tesseract OCR backend implementing the OcrBackend protocol.

Strategy:
1. For PDFs: use pdfplumber to extract native text layer. If text is
   substantial (>50 chars after stripping), return it — no OCR needed.
   If text is sparse or absent (scanned PDF), render pages as images and
   run Tesseract.
2. For images: run Tesseract directly.

Tesseract language: eng+hin (English + Hindi), per DEV_LOG [2026-08-08].
"""

import io

import pdfplumber
import pytesseract
from PIL import Image

from packages.shared_utils import get_logger

logger = get_logger(__name__)

_TESSERACT_LANG = "eng+hin"
_MIN_NATIVE_TEXT_LENGTH = 50  # chars; below this, treat PDF as scanned


class TesseractBackend:
    """Tesseract + pdfplumber OCR backend."""

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        if mime_type == "application/pdf":
            return self._extract_pdf(file_bytes)
        return self._extract_image(file_bytes)

    def _extract_pdf(self, file_bytes: bytes) -> str:
        native_text = self._extract_pdf_native_text(file_bytes)
        if len(native_text.strip()) >= _MIN_NATIVE_TEXT_LENGTH:
            logger.info("PDF: native text layer used (length=%d)", len(native_text))
            return native_text

        logger.info("PDF: sparse native text, falling back to Tesseract OCR")
        return self._ocr_pdf_as_images(file_bytes)

    def _extract_pdf_native_text(self, file_bytes: bytes) -> str:
        texts: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                texts.append(text)
        return "\n".join(texts)

    def _ocr_pdf_as_images(self, file_bytes: bytes) -> str:
        """Render each PDF page as an image and OCR it."""
        try:
            import fitz  # PyMuPDF — optional for image-PDF rendering
        except ImportError:
            logger.error("PyMuPDF not installed; cannot OCR image PDFs")
            return ""

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        texts: list[str] = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang=_TESSERACT_LANG)
            texts.append(text)
        doc.close()
        return "\n".join(texts)

    def _extract_image(self, file_bytes: bytes) -> str:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang=_TESSERACT_LANG)
