"""Lab anomaly detection engine (unsupervised)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from .backends import AnomalyBackend, create_backend
from .config_loader import artifacts_dir, load_config
from .feature_engineering import (
    DEFAULT_IMPUTE,
    contribution_from_scaled,
    feature_dict_to_vector,
    labs_to_feature_dict,
    series_detect_vector,
    series_features,
)
from .schema import (
    DISCLAIMER_EN,
    DISCLAIMER_HI,
    FEATURE_COLUMNS,
    category_from_score,
    category_label,
)


class LabAnomalyEngine:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        auto_train_if_missing: bool = True,
    ) -> None:
        self.config = config or load_config(validate=True)
        self.model: AnomalyBackend | None = None
        self.impute: dict[str, float] = dict(DEFAULT_IMPUTE)
        self.medians: dict[str, float] = dict(DEFAULT_IMPUTE)
        self.iqrs: dict[str, float] = {k: 1.0 for k in FEATURE_COLUMNS}
        self.backend_name = "uninitialized"
        self._load_or_train(auto_train_if_missing=auto_train_if_missing)

    def _load_or_train(self, *, auto_train_if_missing: bool) -> None:
        art = artifacts_dir(self.config)
        meta = art / "meta.json"
        model_p = art / "model.pkl"
        if meta.exists() and model_p.exists():
            try:
                meta_obj = json.loads(meta.read_text(encoding="utf-8"))
                self.backend_name = meta_obj.get("backend", "loaded")
                self.impute = {
                    k: float(v)
                    for k, v in json.loads((art / "impute.json").read_text(encoding="utf-8")).items()
                }
                self.medians = {
                    k: float(v)
                    for k, v in json.loads((art / "medians.json").read_text(encoding="utf-8")).items()
                }
                self.iqrs = {
                    k: float(v)
                    for k, v in json.loads((art / "iqrs.json").read_text(encoding="utf-8")).items()
                }
                self.model = AnomalyBackend.load(model_p)
                return
            except Exception:
                self.model = None
        if auto_train_if_missing:
            self.train()

    def train(self) -> Path:
        from .config_loader import resolve_path
        from .dataset import load_train_rows, rows_to_matrix

        data_dir = resolve_path(self.config["paths"]["train_data"])
        rows = load_train_rows(data_dir)
        # Train unsupervised on non-anomaly rows when labels exist
        normal_rows = [r for r in rows if not int(r.get("is_anomaly") or 0)] or rows
        Xn, _, impute, medians, iqrs = rows_to_matrix(normal_rows)
        self.impute, self.medians, self.iqrs = impute, medians, iqrs

        kind = self.config.get("active_backend") or "auto"
        seed = int(self.config.get("seed") or 42)
        cont = float(self.config.get("contamination") or 0.08)
        model = create_backend(kind, seed=seed, contamination=cont)
        model.fit(Xn)
        self.model = model
        self.backend_name = model.name

        art = artifacts_dir(self.config)
        art.mkdir(parents=True, exist_ok=True)
        model.save(art / "model.pkl")
        (art / "impute.json").write_text(json.dumps(self.impute, indent=2), encoding="utf-8")
        (art / "medians.json").write_text(json.dumps(self.medians, indent=2), encoding="utf-8")
        (art / "iqrs.json").write_text(json.dumps(self.iqrs, indent=2), encoding="utf-8")
        (art / "meta.json").write_text(
            json.dumps(
                {
                    "backend": self.backend_name,
                    "n_train": int(len(Xn)),
                    "features": FEATURE_COLUMNS,
                    "primary": self.config.get("primary_architecture"),
                    "fallback": self.config.get("fallback_architecture"),
                    "baseline": self.config.get("baseline_architecture"),
                    "contamination": cont,
                    "score_threshold": self.config.get("score_threshold"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return art

    def score_vector(self, x: np.ndarray) -> float:
        assert self.model is not None
        s = float(self.model.score_samples(x.reshape(1, -1))[0])
        return float(max(0.0, min(1.0, s)))

    def score_profile(
        self,
        metrics: list[dict[str, Any]],
        *,
        demographics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.model is None:
            self.train()
        from .feature_engineering import extract_labs_from_metrics

        labs = extract_labs_from_metrics(metrics)
        fd = labs_to_feature_dict(labs, demographics=demographics)
        x = feature_dict_to_vector(
            fd, self.impute, medians=self.medians, iqrs=self.iqrs
        )
        score = self.score_vector(x)
        thr = float(self.config.get("score_threshold") or 0.55)
        cat = category_from_score(score)
        contrib = contribution_from_scaled(x)
        top = [c[0] for c in contrib[:5]]
        conf = min(0.98, max(0.45, 0.55 + 0.4 * abs(score - 0.5) + 0.1 * (1 - float(fd.get("missing_fraction") or 0))))
        is_anom = score >= thr
        return {
            "anomaly_score": score,
            "anomaly_probability": score,
            "anomaly_category": category_label(cat),
            "category": cat,
            "is_anomaly": is_anom,
            "confidence": conf,
            "top_contributors": top,
            "contributor_details": [{"feature": n, "weight": w} for n, w in contrib[:5]],
            "method": f"anomaly:{self.backend_name}",
            "disclaimer_en": DISCLAIMER_EN,
            "summary_en": (
                f"{DISCLAIMER_EN} "
                + (
                    "Anomalous laboratory pattern detected "
                    f"(category {category_label(cat)}, score ≈ {score:.2f}). "
                    f"Top contributing markers: {', '.join(top) or 'n/a'}."
                    if is_anom
                    else f"No strong anomalous laboratory pattern (score ≈ {score:.2f})."
                )
            ),
            "summary_hi": (
                f"{DISCLAIMER_HI} "
                + (
                    "असामान्य प्रयोगशाला पैटर्न पाया गया।"
                    if is_anom
                    else "कोई स्पष्ट असामान्य पैटर्न नहीं।"
                )
            ),
        }

    def detect_series(
        self,
        test_name: str,
        data_points: list[tuple[date, float]],
        unit: str | None = None,
        reference_range_low: float | None = None,
        reference_range_high: float | None = None,
    ) -> dict[str, Any]:
        """Protocol-compatible single-series detection for /anomaly/detect."""
        if self.model is None:
            self.train()
        x, fd = series_detect_vector(
            test_name,
            data_points,
            impute=self.impute,
            medians=self.medians,
            iqrs=self.iqrs,
        )
        score = self.score_vector(x)
        thr = float(self.config.get("score_threshold") or 0.55)
        is_anom = score >= thr or abs(float(fd.get("series_robust_z") or 0)) >= 3.0
        cat = category_from_score(score)
        series = series_features(data_points)
        # Map score to API's loosely [-1,1] historical range: normal→+1, anomaly→-1
        # Keep 0–1 available as anomaly_probability in extras
        api_score = float(1.0 - 2.0 * score)  # high anomaly → negative
        z = float(series.get("series_robust_z") or 0.0)
        n = int(series.get("series_n") or len(data_points))
        slope = float(series.get("series_slope") or 0.0)
        if n < 2:
            trend = "insufficient_data"
        elif abs(slope) < 1e-6:
            trend = "stable"
        elif slope > 0:
            trend = "rising"
        else:
            trend = "falling"

        contrib_names = [c[0] for c in contribution_from_scaled(x)[:3]]
        if test_name and test_name.lower() not in [c.lower() for c in contrib_names]:
            contrib_names = [test_name] + contrib_names

        conf = min(0.98, max(0.4, 0.5 + 0.1 * min(5, n) + 0.2 * abs(score - 0.5)))

        if is_anom:
            summary_en = (
                f"{DISCLAIMER_EN} Anomalous laboratory pattern detected "
                f"for {test_name}"
                + (f" ({unit})" if unit else "")
                + f". Category {category_label(cat)}; score ≈ {score:.2f}. "
                f"Contributors: {', '.join(contrib_names[:3])}."
            )
            summary_hi = (
                f"{DISCLAIMER_HI} {test_name} के लिए असामान्य प्रयोगशाला पैटर्न पाया गया।"
            )
        else:
            summary_en = (
                f"{DISCLAIMER_EN} No strong anomalous laboratory pattern detected "
                f"for {test_name}. Score ≈ {score:.2f}."
            )
            summary_hi = (
                f"{DISCLAIMER_HI} {test_name} के लिए कोई स्पष्ट असामान्य पैटर्न नहीं।"
            )

        # Soft ref range note only
        if (
            is_anom is False
            and reference_range_low is not None
            and reference_range_high is not None
            and data_points
        ):
            last = sorted(data_points, key=lambda t: t[0])[-1][1]
            if last < reference_range_low or last > reference_range_high:
                summary_en += " Last value is outside the provided reference interval (informational)."

        return {
            "test_name": test_name,
            "trend": trend,
            "anomaly_score": api_score,
            "anomaly_probability": score,
            "anomaly_category": category_label(cat),
            "is_anomaly": bool(is_anom),
            "z_score": z,
            "out_of_range_streak": 0,
            "method": f"ml_anomaly:{self.backend_name}",
            "data_points_used": n,
            "summary_en": summary_en,
            "summary_hi": summary_hi,
            "confidence": conf,
            "top_contributors": contrib_names[:5],
            "disclaimer_en": DISCLAIMER_EN,
        }
