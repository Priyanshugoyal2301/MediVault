"""
ai-service/ocr/tesseract_backend.py

Tesseract OCR backend implementing the OcrBackend protocol.

Strategy:
1. For each PDF page: use substantial native text if no image is embedded;
   otherwise render that page and run Tesseract, including mixed-content PDFs.
2. For images: honor EXIF orientation and process every frame (up to 40).

Tesseract language: eng+hin (English + Hindi), per DEV_LOG [2026-08-08].
"""

import io

import pdfplumber
import pytesseract
from PIL import Image, ImageOps, ImageSequence

from packages.shared_utils import get_logger

logger = get_logger(__name__)

_TESSERACT_LANG = "eng+hin"
_MIN_NATIVE_TEXT_LENGTH = 50  # chars; below this, treat PDF as scanned


class TesseractBackend:
    """Tesseract + pdfplumber OCR backend."""

    def __init__(self):
        from ..core.config import get_settings
        pytesseract.pytesseract.tesseract_cmd = get_settings().tesseract_cmd

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        if mime_type == "application/pdf":
            return self._extract_pdf(file_bytes)
        return self._extract_image(file_bytes)

    def _read_page(self, image):
        image = ImageOps.exif_transpose(image).convert("RGB")
        if image.width * image.height > 20_000_000:
            raise ValueError("Image is too large to process safely")
        # Orientation is a separate OCR task. Abstain when its confidence is low.
        try:
            orientation = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT, timeout=15)
            rotation = orientation.get("rotate", 0)
            if rotation in (90, 180, 270) and orientation.get("orientation_conf", 0) >= 5:
                image = image.rotate(-rotation, expand=True)
        except (pytesseract.TesseractError, RuntimeError):
            # Sparse pages often have too few characters for orientation analysis.
            pass
        return pytesseract.image_to_string(image, lang=_TESSERACT_LANG, timeout=30)

    def _extract_pdf(self, file_bytes: bytes) -> str:
        """Decide per page: a text cover page must never hide scanned pages."""
        texts: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if len(pdf.pages) > 40:
                raise ValueError("Split documents longer than 40 pages before uploading")
            import fitz
            with fitz.open(stream=file_bytes, filetype="pdf") as rendered:
                for number, page in enumerate(pdf.pages):
                    native = page.extract_text() or ""
                    # Even a page with substantial text can contain a scanned insert.
                    if len(native.strip()) >= _MIN_NATIVE_TEXT_LENGTH and not page.images:
                        texts.append(native)
                    else:
                        bounds = rendered[number].rect
                        if bounds.width * bounds.height * (300 / 72) ** 2 > 20_000_000:
                            raise ValueError("PDF page is too large to render safely")
                        pix = rendered[number].get_pixmap(dpi=300, colorspace=fitz.csRGB, alpha=False)
                        with Image.frombytes("RGB", [pix.width, pix.height], pix.samples) as image:
                            texts.append(self._read_page(image))
        return "\n".join(texts)

    def _extract_image(self, file_bytes: bytes) -> str:
        with Image.open(io.BytesIO(file_bytes)) as image:
            if getattr(image, "n_frames", 1) > 40:
                raise ValueError("Split images longer than 40 frames before uploading")
            return "\n".join(
                self._read_page(frame)
                for frame in ImageSequence.Iterator(image)
            )
