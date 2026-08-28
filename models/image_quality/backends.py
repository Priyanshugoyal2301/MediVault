"""Pluggable image quality backends."""

from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from .features import FEATURE_NAMES, opencv_rule_predict
from .labels import ALL_LABELS, PROBLEM_LABELS, READY_LABEL


class QualityBackend(ABC):
    name: str = "base"

    @abstractmethod
    def fit(
        self, X_feat: np.ndarray, y: np.ndarray, images: list[np.ndarray] | None = None
    ) -> None: ...

    @abstractmethod
    def predict_proba(
        self, X_feat: np.ndarray, images: list[np.ndarray] | None = None
    ) -> np.ndarray:
        """Return (n, n_labels) probabilities in ALL_LABELS order."""

    def predict(
        self,
        X_feat: np.ndarray,
        images: list[np.ndarray] | None = None,
        thr: float = 0.5,
    ) -> np.ndarray:
        return (self.predict_proba(X_feat, images) >= thr).astype(int)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(self, fh)

    @staticmethod
    def load(path: Path) -> "QualityBackend":
        with path.open("rb") as fh:
            return pickle.load(fh)


class OpenCVBackend(QualityBackend):
    name = "opencv_rules"

    def fit(
        self, X_feat: np.ndarray, y: np.ndarray, images: list[np.ndarray] | None = None
    ) -> None:
        return

    def predict_proba(
        self, X_feat: np.ndarray, images: list[np.ndarray] | None = None
    ) -> np.ndarray:
        out = []
        for i in range(len(X_feat)):
            feats = {n: float(X_feat[i, j]) for j, n in enumerate(FEATURE_NAMES)}
            r = opencv_rule_predict(feats)
            out.append([r["multilabel"].get(lab, 0.0) for lab in ALL_LABELS])
        return np.asarray(out, dtype=float)


class SklearnFeatureBackend(QualityBackend):
    """Multi-label model on handcrafted features (fast, picklable)."""

    def __init__(self, name: str = "feature_ml", seed: int = 42) -> None:
        self.name = name
        self.seed = seed
        self._models: list[Any] = []

    def fit(
        self, X_feat: np.ndarray, y: np.ndarray, images: list[np.ndarray] | None = None
    ) -> None:
        from sklearn.ensemble import HistGradientBoostingClassifier

        self._models = []
        for j in range(y.shape[1]):
            yj = y[:, j]
            if len(np.unique(yj)) < 2:
                self._models.append(("const", float(float(yj.mean()) > 0.5)))
                continue
            clf = HistGradientBoostingClassifier(
                max_depth=4,
                learning_rate=0.1,
                max_iter=60,
                random_state=self.seed + j,
            )
            clf.fit(X_feat, yj)
            self._models.append(("clf", clf))

    def predict_proba(
        self, X_feat: np.ndarray, images: list[np.ndarray] | None = None
    ) -> np.ndarray:
        cols = []
        for m in self._models:
            if m[0] == "const":
                cols.append(np.full(len(X_feat), float(m[1])))
            else:
                clf = m[1]
                proba = clf.predict_proba(X_feat)
                classes = list(clf.classes_)
                idx = classes.index(1) if 1 in classes else -1
                cols.append(proba[:, idx])
        return np.stack(cols, axis=1)


def _resize_batch(images: list[np.ndarray]):
    import torch
    from PIL import Image

    tensors = []
    for im in images:
        x = im.astype(np.float32)
        if x.max() > 1.5:
            x = x / 255.0
        if x.ndim == 2:
            x = np.stack([x, x, x], -1)
        pil = Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8)).resize((224, 224))
        x = np.asarray(pil, dtype=np.float32) / 255.0
        tensors.append(np.transpose(x[..., :3], (2, 0, 1)))
    return torch.tensor(np.stack(tensors), dtype=torch.float32)


class TorchMobileNetBackend(QualityBackend):
    """MobileNetV3-Small multi-label (primary). Pickles via state_dict / feature head."""

    name = "mobilenet_v3"

    def __init__(self, seed: int = 42, epochs: int = 3, lr: float = 1e-3) -> None:
        self.seed = seed
        self.epochs = epochs
        self.lr = lr
        self._mode = "unfit"
        self._feat: SklearnFeatureBackend | None = None
        self._state_dict: dict | None = None

    def _build(self):
        import torch
        import torch.nn as nn
        from torchvision import models

        torch.manual_seed(self.seed)
        backbone = models.mobilenet_v3_small(weights=None)
        in_f = backbone.classifier[-1].in_features
        backbone.classifier[-1] = nn.Linear(in_f, len(ALL_LABELS))
        if self._state_dict is not None:
            backbone.load_state_dict(self._state_dict)
        return backbone

    def fit(
        self, X_feat: np.ndarray, y: np.ndarray, images: list[np.ndarray] | None = None
    ) -> None:
        if not images:
            self._feat = SklearnFeatureBackend(name="mobilenet_v3", seed=self.seed)
            self._feat.fit(X_feat, y)
            self._mode = "feat"
            self._state_dict = None
            return
        import torch
        import torch.nn as nn

        backbone = self._build()
        backbone.train()
        opt = torch.optim.Adam(backbone.parameters(), lr=self.lr)
        loss_fn = nn.BCEWithLogitsLoss()
        X = _resize_batch(images)
        Y = torch.tensor(y, dtype=torch.float32)
        bs = min(16, len(X))
        for _ in range(self.epochs):
            perm = torch.randperm(len(X))
            for i in range(0, len(X), bs):
                idx = perm[i : i + bs]
                logits = backbone(X[idx])
                loss = loss_fn(logits, Y[idx])
                opt.zero_grad()
                loss.backward()
                opt.step()
        backbone.eval()
        self._state_dict = {k: v.detach().cpu() for k, v in backbone.state_dict().items()}
        self._mode = "torch"
        self._feat = None

    def predict_proba(
        self, X_feat: np.ndarray, images: list[np.ndarray] | None = None
    ) -> np.ndarray:
        if self._mode == "feat" and self._feat is not None:
            return self._feat.predict_proba(X_feat)
        import torch

        assert images is not None and self._state_dict is not None
        backbone = self._build()
        backbone.eval()
        with torch.no_grad():
            logits = backbone(_resize_batch(images))
            return torch.sigmoid(logits).cpu().numpy()


class TorchEfficientNetBackend(QualityBackend):
    """EfficientNet-B0 as Lite0-compatible fallback."""

    name = "efficientnet_lite0"

    def __init__(self, seed: int = 42, epochs: int = 3, lr: float = 1e-3) -> None:
        self.seed = seed
        self.epochs = epochs
        self.lr = lr
        self._mode = "unfit"
        self._feat: SklearnFeatureBackend | None = None
        self._state_dict: dict | None = None

    def _build(self):
        import torch
        import torch.nn as nn
        from torchvision import models

        torch.manual_seed(self.seed)
        backbone = models.efficientnet_b0(weights=None)
        in_f = backbone.classifier[-1].in_features
        backbone.classifier[-1] = nn.Linear(in_f, len(ALL_LABELS))
        if self._state_dict is not None:
            backbone.load_state_dict(self._state_dict)
        return backbone

    def fit(
        self, X_feat: np.ndarray, y: np.ndarray, images: list[np.ndarray] | None = None
    ) -> None:
        if not images:
            self._feat = SklearnFeatureBackend(name="efficientnet_lite0", seed=self.seed)
            self._feat.fit(X_feat, y)
            self._mode = "feat"
            self._state_dict = None
            return
        import torch
        import torch.nn as nn

        backbone = self._build()
        backbone.train()
        opt = torch.optim.Adam(backbone.parameters(), lr=self.lr)
        loss_fn = nn.BCEWithLogitsLoss()
        X = _resize_batch(images)
        Y = torch.tensor(y, dtype=torch.float32)
        bs = min(16, len(X))
        for _ in range(self.epochs):
            perm = torch.randperm(len(X))
            for i in range(0, len(X), bs):
                idx = perm[i : i + bs]
                logits = backbone(X[idx])
                loss = loss_fn(logits, Y[idx])
                opt.zero_grad()
                loss.backward()
                opt.step()
        backbone.eval()
        self._state_dict = {k: v.detach().cpu() for k, v in backbone.state_dict().items()}
        self._mode = "torch"
        self._feat = None

    def predict_proba(
        self, X_feat: np.ndarray, images: list[np.ndarray] | None = None
    ) -> np.ndarray:
        if self._mode == "feat" and self._feat is not None:
            return self._feat.predict_proba(X_feat)
        import torch

        assert images is not None and self._state_dict is not None
        backbone = self._build()
        backbone.eval()
        with torch.no_grad():
            logits = backbone(_resize_batch(images))
            return torch.sigmoid(logits).cpu().numpy()


def create_backend(kind: str, seed: int = 42, epochs: int = 3) -> QualityBackend:
    kind = (kind or "auto").lower()

    def try_mnet():
        try:
            import torchvision  # noqa: F401

            return TorchMobileNetBackend(seed=seed, epochs=epochs)
        except Exception:
            return SklearnFeatureBackend(name="mobilenet_v3", seed=seed)

    def try_eff():
        try:
            import torchvision  # noqa: F401

            return TorchEfficientNetBackend(seed=seed, epochs=epochs)
        except Exception:
            return SklearnFeatureBackend(name="efficientnet_lite0", seed=seed)

    if kind in ("opencv", "opencv_rules", "baseline"):
        return OpenCVBackend()
    if kind in ("mobilenet", "mobilenet_v3", "mobilenetv3"):
        return try_mnet()
    if kind in ("efficientnet", "efficientnet_lite0", "efficientnet_b0"):
        return try_eff()
    if kind in ("sklearn", "feature_ml"):
        return SklearnFeatureBackend(seed=seed)
    try:
        import torchvision  # noqa: F401

        return try_mnet()
    except Exception:
        return SklearnFeatureBackend(name="mobilenet_v3", seed=seed)


def describe_backends() -> dict[str, bool]:
    out = {"opencv_rules": True, "feature_ml": True, "mobilenet_v3": True, "efficientnet_lite0": True}
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401

        out["torch"] = True
    except Exception:
        out["torch"] = False
    return out


def probs_to_result(probs: np.ndarray, thr: float = 0.45) -> dict[str, Any]:
    assert probs.ndim == 1 and len(probs) == len(ALL_LABELS)
    pmap = {lab: float(probs[i]) for i, lab in enumerate(ALL_LABELS)}
    problems = [p for p in PROBLEM_LABELS if pmap.get(p, 0) >= thr]
    ready_p = pmap.get(READY_LABEL, 0.0)
    pen = sum(pmap.get(p, 0) for p in PROBLEM_LABELS) * 8.0
    score_100 = float(max(5.0, min(99.0, 20 + ready_p * 70 - pen + 10)))
    if problems and score_100 > 70:
        score_100 = max(40.0, score_100 - 12 * min(3, len(problems)))
    ready = ready_p >= thr and score_100 >= 70 and not any(
        p in problems for p in ("blurry", "out_of_focus", "low_resolution")
    )
    conf = float(min(0.98, 0.5 + 0.4 * abs(ready_p - 0.5) + 0.05 * min(5, len(problems))))
    return {
        "quality_score": score_100,
        "problems": problems,
        "ready": ready or (score_100 >= 80 and len(problems) == 0),
        "probs": pmap,
        "confidence": conf,
    }
