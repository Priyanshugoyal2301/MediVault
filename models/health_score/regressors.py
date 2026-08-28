"""Regressor backends for health score (business logic model-agnostic)."""

from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np


class RegressorBackend(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    def feature_importances(self, n: int) -> np.ndarray:
        return np.ones(n, dtype=float) / max(1, n)

    def raw_model(self) -> Any:
        return getattr(self, "_model", self)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(self, fh)

    @staticmethod
    def load(path: Path) -> "RegressorBackend":
        with path.open("rb") as fh:
            return pickle.load(fh)


class LinearBackend(RegressorBackend):
    name = "linear_regression"

    def __init__(self) -> None:
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        self._model = Pipeline(
            [("scaler", StandardScaler()), ("reg", Ridge(alpha=1.0))]
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X), dtype=float)

    def feature_importances(self, n: int) -> np.ndarray:
        try:
            coef = np.abs(self._model.named_steps["reg"].coef_).reshape(-1)
            if coef.sum() > 0:
                return coef / coef.sum()
        except Exception:
            pass
        return super().feature_importances(n)

    def coeffs(self) -> np.ndarray | None:
        try:
            return np.asarray(self._model.named_steps["reg"].coef_, dtype=float)
        except Exception:
            return None


class SklearnGBBackend(RegressorBackend):
    name = "sklearn_gb"

    def __init__(self, seed: int = 42) -> None:
        from sklearn.ensemble import HistGradientBoostingRegressor

        self._model = HistGradientBoostingRegressor(
            max_depth=4, learning_rate=0.08, max_iter=100, random_state=seed
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X), dtype=float)


class XGBoostBackend(RegressorBackend):
    name = "xgboost"

    def __init__(self, seed: int = 42) -> None:
        import xgboost as xgb

        self._model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.08,
            random_state=seed,
            n_jobs=2,
            objective="reg:squarederror",
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X), dtype=float)

    def feature_importances(self, n: int) -> np.ndarray:
        try:
            imp = np.asarray(self._model.feature_importances_, dtype=float)
            if len(imp) == n and imp.sum() > 0:
                return imp / imp.sum()
        except Exception:
            pass
        return super().feature_importances(n)


class LightGBMBackend(RegressorBackend):
    name = "lightgbm"

    def __init__(self, seed: int = 42) -> None:
        import lightgbm as lgb

        self._model = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.08,
            random_state=seed,
            verbose=-1,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X), dtype=float)

    def feature_importances(self, n: int) -> np.ndarray:
        try:
            imp = np.asarray(self._model.feature_importances_, dtype=float)
            if len(imp) == n and imp.sum() > 0:
                return imp / imp.sum()
        except Exception:
            pass
        return super().feature_importances(n)


def create_backend(kind: str, seed: int = 42) -> RegressorBackend:
    kind = (kind or "auto").lower()

    def try_xgb():
        try:
            return XGBoostBackend(seed=seed)
        except Exception:
            return None

    def try_lgb():
        try:
            return LightGBMBackend(seed=seed)
        except Exception:
            return None

    if kind in ("linear", "linear_regression", "baseline"):
        return LinearBackend()
    if kind in ("xgboost", "xgb"):
        return try_xgb() or SklearnGBBackend(seed=seed)
    if kind in ("lightgbm", "lgbm"):
        return try_lgb() or SklearnGBBackend(seed=seed)
    if kind == "sklearn_gb":
        return SklearnGBBackend(seed=seed)
    # auto: xgboost → lightgbm → sklearn_gb
    return try_xgb() or try_lgb() or SklearnGBBackend(seed=seed)


def describe_backends() -> dict[str, bool]:
    out = {"linear_regression": True, "sklearn_gb": True}
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
    try:
        import shap  # noqa: F401

        out["shap"] = True
    except Exception:
        out["shap"] = False
    return out
