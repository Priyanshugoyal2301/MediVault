"""Synthetic degradations for training / data augmentation."""

from __future__ import annotations

import io
from typing import Any

import numpy as np

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:  # pragma: no cover
    Image = None  # type: ignore
    ImageEnhance = None  # type: ignore
    ImageFilter = None  # type: ignore


def make_clean_lab_image(rng: np.random.Generator, h: int = 480, w: int = 360) -> np.ndarray:
    img = np.full((h, w, 3), 250, dtype=np.uint8)
    # letterhead
    img[10:40, 20 : w - 20] = 30
    for i in range(14):
        y = 60 + i * 26
        x0 = 25 + int(rng.integers(0, 20))
        length = int(rng.integers(100, w - 50))
        img[y : y + 2, x0 : x0 + length] = 50
        # values
        img[y : y + 2, w - 80 : w - 25] = 50
    return img


def apply_degradation(
    rgb: np.ndarray,
    kind: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[str]]:
    """Apply named degradation; return image + problem labels."""
    if Image is None:
        return rgb, []
    im = Image.fromarray(rgb)
    labels: list[str] = []

    if kind == "blurry":
        im = im.filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(1.5, 3.5))))
        labels.append("blurry")
    elif kind == "motion_blur":
        k = int(rng.integers(7, 15))
        im = im.filter(ImageFilter.GaussianBlur(radius=2.0))
        # approximate motion by stretching
        w, h = im.size
        im = im.resize((w + k, h), Image.BILINEAR).resize((w, h), Image.BILINEAR)
        labels.extend(["motion_blur", "blurry"])
    elif kind == "out_of_focus":
        im = im.filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(3.5, 6.0))))
        labels.extend(["out_of_focus", "blurry"])
    elif kind == "low_resolution":
        w, h = im.size
        small = im.resize((max(40, w // 6), max(40, h // 6)), Image.BILINEAR)
        im = small.resize((w, h), Image.NEAREST)
        labels.append("low_resolution")
    elif kind == "skewed":
        im = im.rotate(float(rng.uniform(8, 18)), expand=False, fillcolor=(240, 240, 240))
        labels.append("skewed")
    elif kind == "rotated":
        im = im.rotate(float(rng.choice([90, 180, 270])), expand=False, fillcolor=(240, 240, 240))
        labels.append("rotated")
    elif kind == "poor_lighting":
        factor = float(rng.choice([0.35, 0.45, 1.7, 1.9]))
        im = ImageEnhance.Brightness(im).enhance(factor)
        labels.append("poor_lighting")
    elif kind == "low_contrast":
        im = ImageEnhance.Contrast(im).enhance(float(rng.uniform(0.25, 0.45)))
        labels.append("low_contrast")
    elif kind == "cropped":
        w, h = im.size
        box = (w // 5, h // 5, w - w // 8, h - h // 8)
        im = im.crop(box).resize((w, h), Image.BILINEAR)
        labels.extend(["cropped", "incomplete_page"])
    elif kind == "incomplete_page":
        arr = np.asarray(im).copy()
        arr[arr.shape[0] // 2 :, :] = 255
        im = Image.fromarray(arr)
        labels.append("incomplete_page")
    elif kind == "heavy_noise":
        arr = np.asarray(im).astype(np.float32)
        arr += rng.normal(0, float(rng.uniform(25, 45)), arr.shape)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        labels.append("heavy_noise")
    elif kind == "shadowed":
        arr = np.asarray(im).astype(np.float32)
        h, w = arr.shape[:2]
        ys = np.linspace(0.4, 1.0, h).reshape(-1, 1, 1)
        arr *= ys
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        labels.append("shadowed")
    elif kind == "jpeg":
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=int(rng.integers(8, 25)))
        im = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
        labels.append("heavy_noise")
    elif kind == "clean":
        labels = []
    else:
        labels = []

    return np.asarray(im.convert("RGB"), dtype=np.uint8), labels


def random_augment(rgb: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Light training augment (may not change label set)."""
    if Image is None:
        return rgb
    im = Image.fromarray(rgb)
    if rng.random() < 0.4:
        im = ImageEnhance.Brightness(im).enhance(float(rng.uniform(0.85, 1.15)))
    if rng.random() < 0.4:
        im = ImageEnhance.Contrast(im).enhance(float(rng.uniform(0.85, 1.15)))
    if rng.random() < 0.25:
        im = im.rotate(float(rng.uniform(-3, 3)), fillcolor=(245, 245, 245))
    if rng.random() < 0.2:
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=int(rng.integers(70, 95)))
        im = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    return np.asarray(im, dtype=np.uint8)


DEGRADE_KINDS = [
    "clean",
    "blurry",
    "motion_blur",
    "out_of_focus",
    "low_resolution",
    "skewed",
    "rotated",
    "poor_lighting",
    "low_contrast",
    "cropped",
    "incomplete_page",
    "heavy_noise",
    "shadowed",
    "jpeg",
]
