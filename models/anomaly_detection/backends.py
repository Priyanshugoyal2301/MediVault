"""Anomaly detector model backends — IsolationForest / LOF / Robust Z / stubs."""

from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


class AnomalyBackend(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, X: np.ndarray) -> None:
        ...

    @abstractmethod
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Higher = more anomalous, approximately in [0, 1]."""

    def predict_labels(self, X: np.ndarray, thr: float = 0.5) -> np.ndarray:
        return (self.score_samples(X) >= thr).astype(int)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(self, fh)

    @staticmethod
    def load(path: Path) -> "AnomalyBackend":
        with path.open("rb") as fh:
            return pickle.load(fh)


def _to_unit_interval_from_if(raw: np.ndarray) -> np.ndarray:
    """IsolationForest decision_function: higher = more normal. Invert & squash."""
    # raw typically negative for outliers
    s = -raw
    s = s - s.min()
    if s.max() > 1e-9:
        s = s / s.max()
    return s.astype(float)


class IsolationForestBackend(AnomalyBackend):
    name = "isolation_forest"

    def __init__(self, contamination: float = 0.08, seed: int = 42) -> None:
        self._pipe = Pipeline(
            [
                ("scaler", RobustScaler()),
                (
                    "if",
                    IsolationForest(
                        n_estimators=120,
                        contamination=contamination,
                        random_state=seed,
                        n_jobs=2,
                    ),
                ),
            ]
        )

    def fit(self, X: np.ndarray) -> None:
        self._pipe.fit(X)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        if_model: IsolationForest = self._pipe.named_steps["if"]
        Xs = self._pipe.named_steps["scaler"].transform(X)
        raw = if_model.decision_function(Xs)
        return _to_unit_interval_from_if(np.asarray(raw, dtype=float))


class LOFBackend(AnomalyBackend):
    name = "lof"

    def __init__(self, contamination: float = 0.08, n_neighbors: int = 20) -> None:
        self.contamination = contamination
        self.n_neighbors = n_neighbors
        self._scaler = RobustScaler()
        self._lof: LocalOutlierFactor | None = None
        self._X_train: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> None:
        self._X_train = self._scaler.fit_transform(X)
        # novelty=True allows score_samples on new data
        nn = min(self.n_neighbors, max(2, len(X) - 1))
        self._lof = LocalOutlierFactor(
            n_neighbors=nn,
            contamination=self.contamination,
            novelty=True,
        )
        self._lof.fit(self._X_train)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        assert self._lof is not None
        Xs = self._scaler.transform(X)
        # score_samples: higher = more normal for LOF novelty
        raw = self._lof.score_samples(Xs)
        s = -np.asarray(raw, dtype=float)
        s = s - s.min()
        if s.max() > 1e-9:
            s = s / (s.max() + 1e-9)
        return s


class RobustZBackend(AnomalyBackend):
    name = "robust_z"

    def __init__(self) -> None:
        self._med: np.ndarray | None = None
        self._mad: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> None:
        self._med = np.median(X, axis=0)
        self._mad = np.median(np.abs(X - self._med), axis=0) + 1e-6

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        assert self._med is not None and self._mad is not None
        z = np.abs((X - self._med) / (1.4826 * self._mad))
        # max abs robust z across features → map roughly
        m = z.max(axis=1)
        return np.clip(m / 6.0, 0.0, 1.0)


class FutureStubBackend(AnomalyBackend):
    """Autoencoder / One-Class SVM stubs — degrade to robust z until implemented."""

    def __init__(self, kind: str = "autoencoder") -> None:
        self.name = kind
        self._inner = RobustZBackend()

    def fit(self, X: np.ndarray) -> None:
        self._inner.fit(X)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        return self._inner.score_samples(X)


def create_backend(kind: str, seed: int = 42, contamination: float = 0.08) -> AnomalyBackend:
    kind = (kind or "auto").lower()
    if kind in ("isolation_forest", "iforest", "if"):
        return IsolationForestBackend(contamination=contamination, seed=seed)
    if kind in ("lof", "local_outlier_factor"):
        return LOFBackend(contamination=contamination)
    if kind in ("robust_z", "zscore", "baseline"):
        return RobustZBackend()
    if kind in ("autoencoder", "ocsvm", "one_class_svm"):
        return FutureStubBackend(kind=kind)
    # auto: Isolation Forest
    return IsolationForestBackend(contamination=contamination, seed=seed)


def describe_backends() -> dict[str, bool]:
    return {
        "isolation_forest": True,
        "lof": True,
        "robust_z": True,
        "autoencoder_stub": True,
        "one_class_svm_stub": True,
    }
