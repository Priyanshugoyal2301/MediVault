"""Hand-crafted quality features + OpenCV-style rule baseline."""

from __future__ import annotations

from typing import Any

import numpy as np

from .image_io import to_gray
from .labels import PROBLEM_LABELS, READY_LABEL


FEATURE_NAMES: list[str] = [
    "laplacian_var",
    "tenengrad",
    "contrast_std",
    "brightness_mean",
    "brightness_p10",
    "brightness_p90",
    "edge_density",
    "noise_est",
    "skew_score",
    "rotation_score",
    "res_h",
    "res_w",
    "aspect",
    "border_margin",
    "shadow_score",
    "multi_page_score",
]


def compute_features(rgb: np.ndarray) -> dict[str, float]:
    gray = to_gray(rgb)
    h, w = gray.shape
    # Laplacian variance (blur inverse)
    lap_k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    pad = np.pad(gray, 1, mode="edge")
    lap = (
        lap_k[0, 1] * pad[0:-2, 1:-1]
        + lap_k[1, 0] * pad[1:-1, 0:-2]
        + lap_k[1, 1] * pad[1:-1, 1:-1]
        + lap_k[1, 2] * pad[1:-1, 2:]
        + lap_k[2, 1] * pad[2:, 1:-1]
    )
    laplacian_var = float(np.var(lap))

    # Tenengrad (Sobel energy)
    gx = np.diff(gray, axis=1, prepend=gray[:, :1])
    gy = np.diff(gray, axis=0, prepend=gray[:1, :])
    tenengrad = float(np.mean(gx * gx + gy * gy))

    contrast_std = float(np.std(gray))
    brightness_mean = float(np.mean(gray))
    brightness_p10 = float(np.percentile(gray, 10))
    brightness_p90 = float(np.percentile(gray, 90))

    edges = (np.abs(gx) + np.abs(gy)) > 25
    edge_density = float(np.mean(edges))

    # noise: high-frequency residual
    blur = (
        pad[0:-2, 1:-1]
        + pad[1:-1, 0:-2]
        + pad[1:-1, 1:-1]
        + pad[1:-1, 2:]
        + pad[2:, 1:-1]
    ) / 5.0
    noise_est = float(np.std(gray - blur))

    # crude skew via row projection asymmetry
    row_proj = gray.mean(axis=1)
    col_proj = gray.mean(axis=0)
    skew_score = float(abs(np.argmax(row_proj) / max(1, h) - 0.5) * 2)
    # rotation proxy: gradient direction imbalance
    rotation_score = float(abs(np.mean(np.abs(gx)) - np.mean(np.abs(gy))) / (tenengrad + 1e-3))

    # border content (cropping): dark/light margins
    m = max(2, min(h, w) // 20)
    margin = np.concatenate(
        [
            gray[:m, :].ravel(),
            gray[-m:, :].ravel(),
            gray[:, :m].ravel(),
            gray[:, -m:].ravel(),
        ]
    )
    center = gray[m:-m, m:-m] if h > 2 * m and w > 2 * m else gray
    border_margin = float(abs(np.mean(margin) - np.mean(center)) / 255.0)

    # shadow: brightness histogram bimodality-ish
    shadow_score = float(
        max(0.0, (brightness_mean - brightness_p10) / 255.0 - 0.15)
    )

    multi_page_score = 0.0  # single raster default; PDF multipage handled upstream

    return {
        "laplacian_var": laplacian_var,
        "tenengrad": tenengrad,
        "contrast_std": contrast_std,
        "brightness_mean": brightness_mean,
        "brightness_p10": brightness_p10,
        "brightness_p90": brightness_p90,
        "edge_density": edge_density,
        "noise_est": noise_est,
        "skew_score": skew_score,
        "rotation_score": rotation_score,
        "res_h": float(h),
        "res_w": float(w),
        "aspect": float(w) / float(max(1, h)),
        "border_margin": border_margin,
        "shadow_score": shadow_score,
        "multi_page_score": multi_page_score,
    }


def feature_vector(feats: dict[str, float]) -> np.ndarray:
    return np.asarray([float(feats.get(n, 0.0)) for n in FEATURE_NAMES], dtype=np.float64)


def opencv_rule_predict(feats: dict[str, float]) -> dict[str, Any]:
    """Baseline rule checks → multi-label + quality score 0–100."""
    problems: list[str] = []
    scores_pen = 0.0

    lap = feats["laplacian_var"]
    if lap < 80:
        problems.append("blurry")
        scores_pen += 25
        if lap < 40:
            problems.append("out_of_focus")
            scores_pen += 10
    if feats["tenengrad"] < 30 and lap < 100:
        if "motion_blur" not in problems:
            problems.append("motion_blur")
            scores_pen += 12

    if min(feats["res_h"], feats["res_w"]) < 400:
        problems.append("low_resolution")
        scores_pen += 15

    if feats["contrast_std"] < 25:
        problems.append("low_contrast")
        scores_pen += 15

    bm = feats["brightness_mean"]
    if bm < 60 or bm > 220:
        problems.append("poor_lighting")
        scores_pen += 12
    if feats["brightness_p10"] < 25 and feats["shadow_score"] > 0.2:
        problems.append("shadowed")
        scores_pen += 10

    if feats["noise_est"] > 18:
        problems.append("heavy_noise")
        scores_pen += 12

    if feats["skew_score"] > 0.35:
        problems.append("skewed")
        scores_pen += 8
    if feats["rotation_score"] > 0.45:
        problems.append("rotated")
        scores_pen += 8

    if feats["border_margin"] > 0.35 and feats["edge_density"] < 0.05:
        problems.append("cropped")
        scores_pen += 10
        problems.append("incomplete_page")
        scores_pen += 5

    if feats.get("multi_page_score", 0) > 0.5:
        problems.append("multiple_pages_detected")
        scores_pen += 5

    # unique preserve order
    seen = set()
    uniq = []
    for p in problems:
        if p not in seen and p in PROBLEM_LABELS:
            seen.add(p)
            uniq.append(p)

    score_100 = float(max(5.0, min(99.0, 95.0 - scores_pen)))
    ready = score_100 >= 75 and not any(
        p in uniq for p in ("blurry", "out_of_focus", "low_resolution", "heavy_noise")
    )
    multilabel = {READY_LABEL: float(ready)}
    for p in PROBLEM_LABELS:
        multilabel[p] = 1.0 if p in uniq else 0.0

    return {
        "quality_score": score_100,
        "problems": uniq,
        "ready": ready,
        "multilabel": multilabel,
        "method": "opencv_rules",
        "confidence": float(min(0.95, 0.55 + 0.03 * len(uniq) + 0.1 * (1 if ready else 0))),
    }
