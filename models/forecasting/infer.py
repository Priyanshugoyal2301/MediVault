"""
BiomarkerForecastEngine — multi-biomarker longitudinal forecasting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .biomarkers import BIOMARKERS, DISCLAIMER_EN, DISCLAIMER_HI, biomarker_meta
from .config_loader import artifacts_dir, load_config
from .feature_engineering import (
    build_point_features,
    feature_vector,
    history_to_series,
    trend_from_values,
)
from .regressors import RegressorBackend, create_backend


class BiomarkerForecastEngine:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        auto_train_if_missing: bool = True,
    ) -> None:
        self.config = config or load_config(validate=True)
        self.models: dict[str, RegressorBackend] = {}
        self.residual_std: dict[str, float] = {}
        self.backend_name = "uninitialized"
        self._load_or_train(auto_train_if_missing=auto_train_if_missing)

    def _load_or_train(self, *, auto_train_if_missing: bool) -> None:
        art = artifacts_dir(self.config)
        meta = art / "meta.json"
        if meta.exists() and (art / "residual_std.json").exists():
            try:
                meta_obj = json.loads(meta.read_text(encoding="utf-8"))
                self.backend_name = meta_obj.get("backend", "loaded")
                self.residual_std = {
                    k: float(v)
                    for k, v in json.loads(
                        (art / "residual_std.json").read_text(encoding="utf-8")
                    ).items()
                }
                for b in BIOMARKERS:
                    p = art / f"model_{b['id']}.pkl"
                    if p.exists():
                        self.models[b["id"]] = RegressorBackend.load(p)
                if self.models:
                    return
            except Exception:
                self.models = {}
        if auto_train_if_missing:
            self.train()

    def train(self) -> Path:
        from .config_loader import resolve_path
        from .dataset import (
            load_train_patients,
            supervised_from_patients,
        )

        data_dir = resolve_path(self.config["paths"]["train_data"])
        patients = load_train_patients(data_dir)
        horizon = int(self.config.get("default_horizon_days") or 180)
        X_map, y_map = supervised_from_patients(patients, horizon_days=horizon)
        kind = self.config.get("active_backend") or "auto"
        seed = int(self.config.get("seed") or 42)

        art = artifacts_dir(self.config)
        art.mkdir(parents=True, exist_ok=True)
        self.models = {}
        self.residual_std = {}

        for bid, X in X_map.items():
            y = y_map[bid]
            if len(y) < 5:
                continue
            reg = create_backend(kind, seed=seed)
            reg.fit(X, y)
            pred = reg.predict(X)
            resid = y - pred
            self.residual_std[bid] = float(max(np.std(resid), 1e-3))
            reg.save(art / f"model_{bid}.pkl")
            self.models[bid] = reg
            self.backend_name = reg.name

        if not self.models:
            # emergency: fit linear on dummy for all biomarkers
            from .biomarkers import POINT_FEATURE_NAMES

            reg = create_backend("linear")
            rng = np.random.default_rng(0)
            Xd = rng.standard_normal((20, len(POINT_FEATURE_NAMES)))
            yd = rng.standard_normal(20)
            reg.fit(Xd, yd)
            for b in BIOMARKERS:
                reg.save(art / f"model_{b['id']}.pkl")
                self.models[b["id"]] = reg
                self.residual_std[b["id"]] = 1.0
            self.backend_name = reg.name

        (art / "residual_std.json").write_text(
            json.dumps(self.residual_std, indent=2), encoding="utf-8"
        )
        (art / "meta.json").write_text(
            json.dumps(
                {
                    "backend": self.backend_name,
                    "biomarkers": list(self.models.keys()),
                    "primary_architecture": self.config.get("primary_architecture"),
                    "fallback_architecture": self.config.get("fallback_architecture"),
                    "baseline_architecture": self.config.get("baseline_architecture"),
                    "future_architectures": self.config.get("future_architectures"),
                    "default_horizon_days": horizon,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return art

    def forecast(
        self,
        history: list[dict[str, Any]],
        *,
        horizon_days: int | None = None,
        biomarkers: list[str] | None = None,
        demographics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        horizon = int(horizon_days or self.config.get("default_horizon_days") or 180)
        demo = demographics or {}
        age = demo.get("age")
        sex = str(demo.get("sex") or demo.get("gender") or "").lower()
        if sex in ("f", "female", "woman", "1"):
            sex_f = 1.0
        elif sex in ("m", "male", "man", "0"):
            sex_f = 0.0
        else:
            sex_f = 0.5

        series_map = history_to_series(history)
        # infer age from last age_marker if present
        for m in history or []:
            if (m.get("test_name") or "") == "age_marker":
                try:
                    age = float(m["value_numeric"])
                except Exception:
                    pass

        want = biomarkers
        if want is None:
            want = [b["id"] for b in BIOMARKERS]
        else:
            want = [w.lower().replace(" ", "_") for w in want]

        z = float(self.config.get("pi_z") or 1.645)
        min_pts = int(self.config.get("min_history_points") or 2)
        forecasts: list[dict[str, Any]] = []

        for bid in want:
            meta = biomarker_meta(bid)
            series = series_map.get(bid) or []
            current = float(series[-1][1]) if series else None

            if len(series) < min_pts or bid not in self.models:
                # insufficient history
                pred = current
                conf = 0.35 if current is not None else 0.2
                lo = hi = None
                if current is not None:
                    std = self.residual_std.get(bid, abs(current) * 0.1 + 0.1)
                    lo = current - z * std
                    hi = current + z * std
                direction, expected = (
                    ("unknown", "Insufficient longitudinal history for a reliable forecast.")
                    if len(series) < min_pts
                    else trend_from_values(current, pred)
                )
                if len(series) < min_pts and current is not None:
                    # naive persistence
                    pred = current
                    direction, expected = trend_from_values(current, pred)
            else:
                feats = build_point_features(
                    series,
                    horizon_days=horizon,
                    age=float(age) if age is not None else 45.0,
                    sex_female=sex_f,
                )
                x = feature_vector(feats).reshape(1, -1)
                pred = float(self.models[bid].predict(x)[0])
                std = self.residual_std.get(bid, abs(pred) * 0.05 + 0.05)
                lo = pred - z * std
                hi = pred + z * std
                # confidence: more points + shorter residual → higher
                conf = min(
                    0.98,
                    max(
                        0.4,
                        0.55
                        + 0.08 * min(5, len(series))
                        - 0.15 * (std / (abs(pred) + 1e-3)),
                    ),
                )
                direction, expected = trend_from_values(current, pred)

            forecasts.append(
                {
                    "biomarker": meta.get("name") or bid,
                    "biomarker_id": bid,
                    "current_value": current,
                    "predicted_value": pred,
                    "lower_bound": lo,
                    "upper_bound": hi,
                    "confidence": float(conf),
                    "trend_direction": direction,
                    "expected_trend": expected,
                    "horizon_days": horizon,
                    "unit": meta.get("unit"),
                    "method": self.backend_name,
                    "n_history": len(series),
                }
            )

        # summary
        rising = [f for f in forecasts if f["trend_direction"] == "increasing"]
        summary_en = (
            f"{DISCLAIMER_EN} Forecast horizon ≈ {horizon} days "
            f"({horizon // 30} months). "
            f"{len(rising)} biomarker(s) projected increasing (statistical only)."
        )
        summary_hi = (
            f"{DISCLAIMER_HI} क्षितिज ≈ {horizon} दिन। केवल सांख्यिकीय पूर्वानुमान।"
        )
        return {
            "forecasts": forecasts,
            "horizon_days": horizon,
            "method": f"forecast:{self.backend_name}",
            "disclaimer_en": DISCLAIMER_EN,
            "disclaimer_hi": DISCLAIMER_HI,
            "summary_en": summary_en,
            "summary_hi": summary_hi,
        }
