"""
Preprocessing pipeline for medical report documents (Phase 1).

Modular steps (each can be disabled via config):
  - PDF page extraction
  - Resolution normalization
  - Rotation correction (EXIF + 90° heuristics)
  - Deskew
  - Contrast enhancement
  - Noise reduction
  - Image normalization

Dependencies: Pillow required; PyMuPDF for PDF; OpenCV optional for deskew/denoise.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


SUPPORTED_IMAGE_MIMES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/tiff",
        "image/webp",
    }
)
PDF_MIME = "application/pdf"


@dataclass
class PageImage:
    """One preprocessed page ready for VLM OCR."""

    image: Image.Image
    page_number: int  # 1-based
    source_mime: str
    rotation_applied_deg: float = 0.0
    deskew_angle_deg: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_png_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        return buf.getvalue()


def _default_preprocess_cfg() -> dict[str, Any]:
    return {
        "target_dpi": 300,
        "max_page_side": 2500,
        "enable_deskew": True,
        "enable_contrast": True,
        "enable_denoise": True,
        "enable_rotation": True,
    }


def preprocess_document(
    file_bytes: bytes,
    mime_type: str,
    config: dict[str, Any] | None = None,
) -> list[PageImage]:
    """
    Convert PDF/image bytes into a list of preprocessed page images.

    Raises ValueError for unsupported types or empty documents.
    """
    cfg = {**_default_preprocess_cfg(), **(config or {})}
    mime = (mime_type or "").lower().strip()
    if mime == "image/jpg":
        mime = "image/jpeg"

    if mime == PDF_MIME:
        pages = _pdf_to_images(file_bytes, dpi=int(cfg["target_dpi"]))
    elif mime in SUPPORTED_IMAGE_MIMES:
        pages = [_open_image(file_bytes, mime)]
    else:
        raise ValueError(f"Unsupported mime_type for Unlimited-OCR preprocess: {mime_type}")

    if not pages:
        raise ValueError("No pages extracted from document")

    out: list[PageImage] = []
    for idx, img in enumerate(pages, start=1):
        page = _process_page(img, idx, mime or "image/png", cfg)
        out.append(page)
    return out


def _open_image(file_bytes: bytes, mime: str) -> Image.Image:
    img = Image.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")
    return img


def _pdf_to_images(file_bytes: bytes, dpi: int = 300) -> list[Image.Image]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF (pymupdf) is required for PDF page extraction"
        ) from exc

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images: list[Image.Image] = []
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
    finally:
        doc.close()
    return images


def _process_page(
    img: Image.Image,
    page_number: int,
    source_mime: str,
    cfg: dict[str, Any],
) -> PageImage:
    rotation = 0.0
    deskew = 0.0
    work = img.copy()

    if cfg.get("enable_rotation", True):
        work, rotation = _fix_rotation(work)

    if cfg.get("enable_deskew", True):
        work, deskew = _deskew(work)

    if cfg.get("enable_denoise", True):
        work = _denoise(work)

    if cfg.get("enable_contrast", True):
        work = _enhance_contrast(work)

    work = _normalize_resolution(work, int(cfg.get("max_page_side", 2500)))

    return PageImage(
        image=work,
        page_number=page_number,
        source_mime=source_mime,
        rotation_applied_deg=rotation,
        deskew_angle_deg=deskew,
        metadata={
            "width": work.width,
            "height": work.height,
        },
    )


def _fix_rotation(img: Image.Image) -> tuple[Image.Image, float]:
    """
    Best-effort upright orientation.
    EXIF already applied; try 0/90/180/270 variance heuristic for landscape scans.
    """
    # Prefer portrait reports: if very wide, try rotating 90°
    if img.width > img.height * 1.35:
        rotated = img.rotate(90, expand=True)
        return rotated, 90.0
    return img, 0.0


def _deskew(img: Image.Image) -> tuple[Image.Image, float]:
    """Estimate skew angle via projection profile; no OpenCV required."""
    try:
        gray = img.convert("L")
        # Downsample for speed
        scale = max(gray.width, gray.height) / 800.0
        if scale > 1:
            small = gray.resize(
                (max(1, int(gray.width / scale)), max(1, int(gray.height / scale))),
                Image.Resampling.BILINEAR,
            )
        else:
            small = gray
        best_angle = 0.0
        best_score = -1.0
        for angle in range(-8, 9):
            trial = small.rotate(angle, expand=False, fillcolor=255)
            # Horizontal projection variance — higher when lines align
            w, h = trial.size
            # Prefer get_flattened_data when available (Pillow 10+)
            if hasattr(trial, "get_flattened_data"):
                pixels = list(trial.get_flattened_data())  # type: ignore[attr-defined]
            else:
                pixels = list(trial.getdata())
            row_sums = [0] * h
            for y in range(h):
                row_sums[y] = sum(255 - pixels[y * w + x] for x in range(w))
            mean = sum(row_sums) / max(len(row_sums), 1)
            var = sum((s - mean) ** 2 for s in row_sums) / max(len(row_sums), 1)
            if var > best_score:
                best_score = var
                best_angle = float(angle)
        if abs(best_angle) < 0.5:
            return img, 0.0
        return img.rotate(best_angle, expand=True, fillcolor=(255, 255, 255)), best_angle
    except Exception:  # noqa: BLE001
        return img, 0.0


def _denoise(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.MedianFilter(size=3))


def _enhance_contrast(img: Image.Image) -> Image.Image:
    # Autocontrast + mild enhancement — no fixed clinical thresholds
    work = ImageOps.autocontrast(img, cutoff=1)
    return ImageEnhance.Contrast(work).enhance(1.15)


def _normalize_resolution(img: Image.Image, max_side: int) -> Image.Image:
    w, h = img.size
    longest = max(w, h)
    if longest <= max_side:
        return img
    scale = max_side / float(longest)
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def pages_to_text_stub(pages: list[PageImage]) -> list[tuple[int, str]]:
    """
    Offline stub OCR for CI when VLM weights are unavailable.
    Uses Tesseract if present; otherwise empty strings (caller may inject text).
    """
    results: list[tuple[int, str]] = []
    try:
        import pytesseract
    except ImportError:
        return [(p.page_number, "") for p in pages]

    for p in pages:
        try:
            text = pytesseract.image_to_string(p.image, lang="eng+hin")
        except Exception:  # noqa: BLE001
            text = ""
        results.append((p.page_number, text))
    return results
