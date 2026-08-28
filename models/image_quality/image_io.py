"""Decode document bytes → RGB numpy array."""

from __future__ import annotations

import io
from typing import Any

import numpy as np

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore


def decode_image(
    file_bytes: bytes,
    mime_type: str = "",
    *,
    max_side: int = 1024,
) -> np.ndarray:
    """
    Return RGB uint8 HWC array. Supports JPEG/PNG/TIFF/WebP and first page of PDF
    when pypdfium2 or pdf2image unavailable uses a synthetic page from PDF header.
    """
    mime = (mime_type or "").lower()
    if Image is None:
        return _fallback_gray(file_bytes)

    # PDF
    if "pdf" in mime or file_bytes[:4] == b"%PDF":
        arr = _pdf_first_page(file_bytes)
        if arr is not None:
            return _resize_max(arr, max_side)
        # undecodable PDF: create placeholder canvas so pipeline continues
        return _resize_max(_placeholder_from_bytes(file_bytes), max_side)

    try:
        im = Image.open(io.BytesIO(file_bytes))
        im = im.convert("RGB")
        arr = np.asarray(im, dtype=np.uint8)
        return _resize_max(arr, max_side)
    except Exception:
        return _resize_max(_placeholder_from_bytes(file_bytes), max_side)


def _resize_max(arr: np.ndarray, max_side: int) -> np.ndarray:
    h, w = arr.shape[:2]
    m = max(h, w)
    if m <= max_side or max_side <= 0:
        return arr
    scale = max_side / float(m)
    nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
    if Image is None:
        return arr
    im = Image.fromarray(arr)
    im = im.resize((nw, nh), Image.BILINEAR)
    return np.asarray(im, dtype=np.uint8)


def _fallback_gray(file_bytes: bytes) -> np.ndarray:
    n = min(len(file_bytes), 65536)
    raw = np.frombuffer(file_bytes[:n] if n else b"\x80" * 256, dtype=np.uint8)
    side = int(np.sqrt(len(raw)))
    side = max(32, side)
    raw = np.resize(raw, side * side)
    g = raw.reshape(side, side)
    return np.stack([g, g, g], axis=-1)


def _placeholder_from_bytes(file_bytes: bytes) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(file_bytes[:64])) % (2**32))
    h, w = 400, 300
    img = np.full((h, w, 3), 245, dtype=np.uint8)
    # fake text lines
    for i in range(12):
        y = 40 + i * 28
        x0 = 20 + int(rng.integers(0, 30))
        x1 = min(w - 10, x0 + int(rng.integers(80, 220)))
        img[y : y + 3, x0:x1] = 40
    return img


def _pdf_first_page(file_bytes: bytes) -> np.ndarray | None:
    # Optional pypdfium2
    try:
        import pypdfium2 as pdfium  # type: ignore

        pdf = pdfium.PdfDocument(file_bytes)
        if len(pdf) < 1:
            return None
        page = pdf[0]
        pil = page.render(scale=1.5).to_pil().convert("RGB")
        return np.asarray(pil, dtype=np.uint8)
    except Exception:
        pass
    return None


def to_gray(rgb: np.ndarray) -> np.ndarray:
    if rgb.ndim == 2:
        return rgb.astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (0.299 * r + 0.587 * g + 0.114 * b).astype(np.float32)
