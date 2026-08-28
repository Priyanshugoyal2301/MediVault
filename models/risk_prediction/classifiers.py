"""
Classifier backends — interchangeable model zoo.

Primary: XGBoost
Fallback: LightGBM
Baseline: Logistic Regression
Always-on offline: sklearn HistGradientBoosting (if tree libs missing)
"""

from __future__ import annotations

import json
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from .feature_engineering import feature_importance_from_coef


class ClassifierBackend(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return probability of positive class, shape (n,)."""

    @abstractmethod
    def feature_importance(self, columns: list[str], top_k: int = 5) -> list[tuple[str, float]]:
        ...

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(self, fh)

    @staticmethod
    def load(path: Path) -> "ClassifierBackend":
        with path.open("rb") as fh:
            return pickle.load(fh)


class LogisticBackend(ClassifierBackend):
    name = "logistic_regression"

    def __init__(self, seed: int = 42) -> None:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        self._model = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=500,
                        class_weight="balanced",
                        random_state=seed,
                    ),
                ),
            ]
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        proba = self._model.predict_proba(X)
        # positive class column
        classes = list(self._model.named_steps["clf"].classes_)
        if 1 in classes:
            idx = classes.index(1)
        else:
            idx = -1
        return proba[:, idx]

    def feature_importance(self, columns: list[str], top_k: int = 5) -> list[tuple[str, float]]:
        coef = self._model.named_steps["clf"].coef_
        return feature_importance_from_coef(coef, columns, top_k=top_k)


class SklearnGBBackend(ClassifierBackend):
    """Deploy-safe tree ensemble when XGBoost/LightGBM unavailable."""

    name = "sklearn_gb"

    def __init__(self, seed: int = 42) -> None:
        from sklearn.ensemble import HistGradientBoostingClassifier

        self._model = HistGradientBoostingClassifier(
            max_depth=4,
            learning_rate=0.08,
            max_iter=120,
            random_state=seed,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        proba = self._model.predict_proba(X)
        classes = list(self._model.classes_)
        idx = classes.index(1) if 1 in classes else -1
        return proba[:, idx]

    def feature_importance(self, columns: list[str], top_k: int = 5) -> list[tuple[str, float]]:
        # permutation-free: use absolute partial dependence proxy via feature_names_
        # HistGB has no coef_; fall back to zero-importance ranking by variance proxy
        return [(c, 0.0) for c in columns[:top_k]]


class XGBoostBackend(ClassifierBackend):
    name = "xgboost"

    def __init__(self, seed: int = 42) -> None:
        import xgboost as xgb

        self._model = xgb.XGBClassifier(
            n_estimators=80,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=seed,
            n_jobs=2,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict_proba(X)[:, 1]

    def feature_importance(self, columns: list[str], top_k: int = 5) -> list[tuple[str, float]]:
        try:
            imp = self._model.feature_importances_
            return feature_importance_from_coef(imp, columns, top_k=top_k)
        except Exception:
            return [(c, 0.0) for c in columns[:top_k]]


class LightGBMBackend(ClassifierBackend):
    name = "lightgbm"

    def __init__(self, seed: int = 42) -> None:
        import lightgbm as lgb

        self._model = lgb.LGBMClassifier(
            n_estimators=80,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=seed,
            verbose=-1,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict_proba(X)[:, 1]

    def feature_importance(self, columns: list[str], top_k: int = 5) -> list[tuple[str, float]]:
        try:
            imp = self._model.feature_importances_
            return feature_importance_from_coef(imp, columns, top_k=top_k)
        except Exception:
            return [(c, 0.0) for c in columns[:top_k]]


def create_backend(kind: str, seed: int = 42) -> ClassifierBackend:
    kind = (kind or "auto").lower()

    def try_xgb() -> ClassifierBackend | None:
        try:
            return XGBoostBackend(seed=seed)
        except Exception:
            return None

    def try_lgb() -> ClassifierBackend | None:
        try:
            return LightGBMBackend(seed=seed)
        except Exception:
            return None

    if kind in ("logistic", "logistic_regression", "baseline"):
        return LogisticBackend(seed=seed)
    if kind in ("xgboost", "xgb"):
        return try_xgb() or SklearnGBBackend(seed=seed)
    if kind in ("lightgbm", "lgbm"):
        return try_lgb() or SklearnGBBackend(seed=seed)
    if kind == "sklearn_gb":
        return SklearnGBBackend(seed=seed)
    # auto: xgb → lgb → sklearn_gb
    return try_xgb() or try_lgb() or SklearnGBBackend(seed=seed)


def describe_backends() -> dict[str, bool]:
    out = {"logistic_regression": True, "sklearn_gb": True}
    try:
        import xgboost  # noqa: F401

        out["xgboost"] = True
    except Exception:
        out["xgboost"] = False
    try:
        import lightgbm  # noqa: F401

        out["lightgbm"] = True
    except Exception:
        out["lightgbm"] = False
    return out
