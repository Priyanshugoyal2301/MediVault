"""Personalized Health Score engine with explainability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from models.explainability import (
    ExplanationBundle,
    explain_linear_model,
    explain_tree_model,
)

from .config_loader import artifacts_dir, load_config
from .feature_engineering import (
    DEFAULT_IMPUTE,
    feature_dict_to_vector,
    metrics_to_feature_dict,
)
from .regressors import LinearBackend, RegressorBackend, create_backend
from .schema import (
    DISCLAIMER_EN,
    DISCLAIMER_HI,
    FEATURE_COLUMNS,
    band_label_en,
    feature_display_name,
    score_to_band,
)


class HealthScoreEngine:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        auto_train_if_missing: bool = True,
    ) -> None:
        self.config = config or load_config(validate=True)
        self.model: RegressorBackend | None = None
        self.impute: dict[str, float] = dict(DEFAULT_IMPUTE)
        self.background: np.ndarray | None = None
        self.residual_std: float = 5.0
        self.global_importance: list[tuple[str, float]] = []
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
                self.residual_std = float(meta_obj.get("residual_std", 5.0))
                self.impute = {
                    k: float(v)
                    for k, v in json.loads(
                        (art / "impute.json").read_text(encoding="utf-8")
                    ).items()
                }
                self.model = RegressorBackend.load(model_p)
                bg = art / "background.npy"
                if bg.exists():
                    self.background = np.load(bg)
                gi = art / "global_importance.json"
                if gi.exists():
                    raw = json.loads(gi.read_text(encoding="utf-8"))
                    self.global_importance = [(r["feature"], float(r["importance"])) for r in raw]
                return
            except Exception:
                self.model = None
        if auto_train_if_missing:
            self.train()

    def train(self) -> Path:
        from .config_loader import resolve_path
        from .dataset import load_train_rows, rows_to_matrices

        data_dir = resolve_path(self.config["paths"]["train_data"])
        rows = load_train_rows(data_dir)
        X, y, impute = rows_to_matrices(rows)
        self.impute = impute
        kind = self.config.get("active_backend") or "auto"
        seed = int(self.config.get("seed") or 42)
        reg = create_backend(kind, seed=seed)
        reg.fit(X, y)
        pred = reg.predict(X)
        self.residual_std = float(max(np.std(y - pred), 1.0))
        self.model = reg
        self.backend_name = reg.name
        self.background = X[: min(80, len(X))]

        imp = reg.feature_importances(len(FEATURE_COLUMNS))
        self.global_importance = sorted(
            zip(FEATURE_COLUMNS, imp.tolist()), key=lambda t: -t[1]
        )

        art = artifacts_dir(self.config)
        art.mkdir(parents=True, exist_ok=True)
        reg.save(art / "model.pkl")
        (art / "impute.json").write_text(json.dumps(self.impute, indent=2), encoding="utf-8")
        np.save(art / "background.npy", self.background)
        (art / "global_importance.json").write_text(
            json.dumps(
                [
                    {"feature": n, "importance": float(v)}
                    for n, v in self.global_importance
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        (art / "meta.json").write_text(
            json.dumps(
                {
                    "backend": self.backend_name,
                    "residual_std": self.residual_std,
                    "n_train": int(len(y)),
                    "features": FEATURE_COLUMNS,
                    "primary": self.config.get("primary_architecture"),
                    "fallback": self.config.get("fallback_architecture"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return art

    def _explain(self, x: np.ndarray) -> ExplanationBundle:
        assert self.model is not None
        top_k = int(self.config.get("top_k_explain") or 8)
        if isinstance(self.model, LinearBackend):
            coef = self.model.coeffs()
            means = (
                self.background.mean(axis=0)
                if self.background is not None
                else np.zeros(x.shape[1])
            )
            if coef is not None:
                bundle = explain_linear_model(
                    coef, x, FEATURE_COLUMNS, means=means, top_k=top_k
                )
            else:
                bundle = explain_tree_model(
                    self.model.raw_model(),
                    x,
                    FEATURE_COLUMNS,
                    background=self.background,
                    top_k=top_k,
                )
        else:
            bundle = explain_tree_model(
                self.model.raw_model(),
                x,
                FEATURE_COLUMNS,
                background=self.background,
                top_k=top_k,
            )
        if not bundle.global_importance and self.global_importance:
            bundle.global_importance = list(self.global_importance[: max(top_k, 10)])
        return bundle

    def _humanize_contributors(
        self, bundle: ExplanationBundle, fd: dict[str, float | None]
    ) -> tuple[list[str], list[str]]:
        """Map raw SHAP features to friendlier clinical-style phrases."""
        pos: list[str] = []
        neg: list[str] = []
        for e in bundle.local:
            name = feature_display_name(e.feature)
            val = fd.get(e.feature)
            # For health score: positive contribution increases score (good)
            if e.contribution > 0:
                if e.feature == "hdl" and val is not None and float(val) >= 50:
                    pos.append(f"Favorable HDL ({e.percent:.0f}%)")
                elif e.feature == "creatinine" and val is not None and float(val) <= 1.1:
                    pos.append(f"Normal Creatinine ({e.percent:.0f}%)")
                elif e.feature == "hemoglobin" and val is not None and float(val) >= 12:
                    pos.append(f"Normal Hemoglobin ({e.percent:.0f}%)")
                elif e.feature == "egfr" and val is not None and float(val) >= 90:
                    pos.append(f"Healthy eGFR ({e.percent:.0f}%)")
                else:
                    pos.append(f"{name} (+{e.percent:.0f}%)")
            elif e.contribution < 0:
                if e.feature == "hba1c" and val is not None and float(val) >= 5.7:
                    neg.append(f"Elevated HbA1c ({e.percent:.0f}%)")
                elif e.feature == "ldl" and val is not None and float(val) > 100:
                    neg.append(f"High LDL ({e.percent:.0f}%)")
                elif e.feature == "alt" and (
                    (val is not None and float(val) > 40)
                    or (fd.get("alt_slope") or 0) > 0
                ):
                    if (fd.get("alt_slope") or 0) > 0:
                        neg.append(f"Increasing ALT ({e.percent:.0f}%)")
                    else:
                        neg.append(f"Elevated ALT ({e.percent:.0f}%)")
                elif e.feature == "risk_mean_proxy":
                    neg.append(f"Higher aggregate risk signal ({e.percent:.0f}%)")
                elif e.feature == "forecast_worsening_proxy":
                    neg.append(f"Unfavorable projected trends ({e.percent:.0f}%)")
                else:
                    neg.append(f"{name} (−{e.percent:.0f}%)")
        if not pos and bundle.positive_labels:
            pos = list(bundle.positive_labels)
        if not neg and bundle.negative_labels:
            neg = list(bundle.negative_labels)
        return pos[:5], neg[:5]

    def score(
        self,
        metrics: list[dict[str, Any]],
        *,
        demographics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.model is None:
            self.train()
        assert self.model is not None

        # extract demographics from metrics markers
        demo = dict(demographics or {})
        for m in metrics or []:
            tn = (m.get("test_name") or "").lower()
            if tn == "age" and demo.get("age") is None:
                try:
                    demo["age"] = float(m["value_numeric"])
                except Exception:
                    pass
            if tn in ("sex", "gender") and demo.get("sex") is None:
                demo["sex"] = m.get("value_text") or m.get("value_numeric")

        fd = metrics_to_feature_dict(metrics, demographics=demo)
        x = feature_dict_to_vector(fd, self.impute).reshape(1, -1)
        pred = float(self.model.predict(x)[0])
        pred = float(max(0.0, min(100.0, pred)))
        band = score_to_band(pred)
        label = band_label_en(band)

        miss = float(fd.get("missing_fraction") or 0.0)
        # confidence: less missing + residual
        conf = min(
            0.98,
            max(
                0.45,
                0.72 - 0.35 * miss + 0.15 * min(1.0, 8.0 / (self.residual_std + 1e-3)),
            ),
        )

        bundle = self._explain(x)
        pos, neg = self._humanize_contributors(bundle, fd)

        summary_en = (
            f"{DISCLAIMER_EN} Personalized health score ≈ {pred:.0f}/100 "
            f"({label}). Confidence ≈ {conf:.0%}. "
            f"Top supports: {', '.join(pos[:3]) or 'n/a'}. "
            f"Areas of attention: {', '.join(neg[:3]) or 'n/a'}."
        )
        summary_hi = (
            f"{DISCLAIMER_HI} स्वास्थ्य स्कोर ≈ {pred:.0f}/100 ({label}). "
            f"आत्मविश्वास ≈ {conf:.0%}।"
        )

        components = {
            "score": pred,
            "confidence": conf,
            "missing_fraction": miss,
            "residual_std": self.residual_std,
        }
        for e in bundle.local[:10]:
            components[f"shap_{e.feature}"] = float(e.contribution)

        return {
            "score": pred,
            "level": band,
            "risk_band": label,
            "confidence": conf,
            "method": f"health_score:{self.backend_name}",
            "components": components,
            "positive_contributors": pos,
            "negative_contributors": neg,
            "top_features": [
                {
                    "feature": e.feature,
                    "display": feature_display_name(e.feature),
                    "contribution": e.contribution,
                    "percent": e.percent,
                    "direction": e.direction,
                }
                for e in bundle.local[: int(self.config.get("top_k_explain") or 8)]
            ],
            "global_importance": [
                {"feature": n, "importance": float(v)}
                for n, v in (bundle.global_importance or self.global_importance)[:12]
            ],
            "explanation_method": bundle.method,
            "disclaimer_en": DISCLAIMER_EN,
            "summary_en": summary_en,
            "summary_hi": summary_hi,
        }
