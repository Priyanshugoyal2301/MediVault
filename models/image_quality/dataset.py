"""Synthetic image quality datasets (DocLayNet/PubLayNet not redistributed)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from .augmentations import DEGRADE_KINDS, apply_degradation, make_clean_lab_image
from .features import compute_features, feature_vector
from .labels import ALL_LABELS, PROBLEM_LABELS, READY_LABEL


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_dir() -> Path:
    return _repo_root() / "datasets" / "image_quality"


def ensure_dataset_meta(data_dir: Path | None = None) -> Path:
    d = data_dir or default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    lic = d / "LICENSING.md"
    if not lic.exists():
        lic.write_text(
            """# Image quality datasets

| Resource | Redistributed? |
|----------|----------------|
| Synthetic degraded lab page images | Yes (generated) |
| DocLayNet | No — DOCLAYNET_PATH |
| PubLayNet | No — PUBLAYNET_PATH |
| RVL-CDIP | No — RVL_CDIP_PATH |
""",
            encoding="utf-8",
        )
    return d


def labels_to_vector(problem_list: list[str], ready: bool) -> np.ndarray:
    v = np.zeros(len(ALL_LABELS), dtype=np.float32)
    for i, lab in enumerate(ALL_LABELS):
        if lab == READY_LABEL:
            v[i] = 1.0 if ready else 0.0
        elif lab in problem_list:
            v[i] = 1.0
    return v


def generate_samples(
    n: int = 200,
    seed: int = 42,
) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    images = []
    feats = []
    ys = []
    for i in range(n):
        clean = make_clean_lab_image(rng)
        kind = DEGRADE_KINDS[i % len(DEGRADE_KINDS)]
        if kind == "clean" or rng.random() < 0.15:
            img, problems = clean, []
        else:
            img, problems = apply_degradation(clean, kind, rng)
        # multi-degrade occasionally
        if rng.random() < 0.15 and problems:
            img2, p2 = apply_degradation(img, rng.choice(["heavy_noise", "poor_lighting", "jpeg"]), rng)
            img, problems = img2, list(dict.fromkeys(problems + p2))
        ready = len(problems) == 0
        f = feature_vector(compute_features(img))
        images.append(img)
        feats.append(f)
        ys.append(labels_to_vector(problems, ready=ready))
    return images, np.stack(feats), np.stack(ys)


def load_train_arrays(data_dir: Path | None = None, n: int = 240) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    ensure_dataset_meta(data_dir)
    # Prefer env corpus of paths jsonl later
    return generate_samples(n=n, seed=42)


def load_eval_arrays(data_dir: Path | None = None, n: int = 80) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    ensure_dataset_meta(data_dir)
    return generate_samples(n=n, seed=7)
