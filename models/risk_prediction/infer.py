"""
DiseaseRiskEngine — multi-condition non-diagnostic risk probabilities.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .classifiers import ClassifierBackend, create_backend
from .config_loader import artifacts_dir, load_config
from .diseases import (
    DISCLAIMER_EN,
    DISCLAIMER_HI,
    DISEASES,
    FEATURE_COLUMNS,
)
from .feature_engineering import feature_importance_from_coef
from .preprocess import (
    feature_dict_to_vector,
    metrics_to_feature_dict,
)


@dataclass
class ConditionRisk:
    disease_id: str
    name_en: str
    risk_probability: float
    risk_category: str  # low | moderate | high
    confidence: float
    top_contributors: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _band(prob: float, low: float = 0.33, high: float = 0.66) -> str:
    if prob < low:
        return "low"
    if prob < high:
        return "moderate"
    return "high"


def _confidence_from_missing(missing_fraction: float, margin: float) -> float:
    # Higher margin from 0.5 and fewer missing labs → higher confidence
    base = 0.55 + 0.4 * min(1.0, abs(margin - 0.5) * 2)
    base *= max(0.4, 1.0 - 0.6 * missing_fraction)
    return float(min(0.99, max(0.35, base)))


class DiseaseRiskEngine:
    """Trains / loads one binary classifier per disease."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        auto_train_if_missing: bool = True,
    ) -> None:
        self.config = config or load_config(validate=True)
        self.models: dict[str, ClassifierBackend] = {}
        self.impute: dict[str, float] = {}
        self.backend_name = "uninitialized"
        self._load_or_train(auto_train_if_missing=auto_train_if_missing)

    def _load_or_train(self, *, auto_train_if_missing: bool) -> None:
        art = artifacts_dir(self.config)
        meta = art / "meta.json"
        if meta.exists() and (art / "impute.json").exists():
            try:
                meta_obj = json.loads(meta.read_text(encoding="utf-8"))
                self.backend_name = meta_obj.get("backend", "loaded")
                self.impute = {
                    k: float(v)
                    for k, v in json.loads(
                        (art / "impute.json").read_text(encoding="utf-8")
                    ).items()
                }
                for d in DISEASES:
                    p = art / f"model_{d['id']}.pkl"
                    if p.exists():
                        self.models[d["id"]] = ClassifierBackend.load(p)
                if self.models:
                    return
            except Exception:
                self.models = {}
        if auto_train_if_missing:
            self.train()

    def train(self) -> Path:
        from .dataset import load_train_rows, rows_to_matrices
        from .config_loader import resolve_path

        data_dir = resolve_path(self.config["paths"]["train_data"])
        rows = load_train_rows(data_dir)
        X, ys, imp = rows_to_matrices(rows)
        self.impute = imp
        kind = self.config.get("active_backend") or "auto"
        seed = int(self.config.get("seed") or 42)

        # Resolve name once
        probe = create_backend(kind, seed=seed)
        self.backend_name = probe.name

        art = artifacts_dir(self.config)
        art.mkdir(parents=True, exist_ok=True)
        self.models = {}
        for d in DISEASES:
            did = d["id"]
            y = ys[did]
            # need both classes for classifiers
            if len(np.unique(y)) < 2:
                clf = create_backend("logistic", seed=seed)
            else:
                clf = create_backend(kind, seed=seed)
            clf.fit(X, y)
            clf.save(art / f"model_{did}.pkl")
            self.models[did] = clf
            self.backend_name = clf.name

        (art / "impute.json").write_text(
            json.dumps(self.impute, indent=2), encoding="utf-8"
        )
        (art / "meta.json").write_text(
            json.dumps(
                {
                    "backend": self.backend_name,
                    "n_train": int(X.shape[0]),
                    "features": FEATURE_COLUMNS,
                    "diseases": [d["id"] for d in DISEASES],
                    "primary_architecture": self.config.get("primary_architecture"),
                    "fallback_architecture": self.config.get("fallback_architecture"),
                    "baseline_architecture": self.config.get("baseline_architecture"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return art

    def predict_conditions(
        self,
        metrics: list[dict[str, Any]],
        *,
        demographics: dict[str, Any] | None = None,
    ) -> list[ConditionRisk]:
        fdict = metrics_to_feature_dict(metrics, demographics=demographics)
        vec = feature_dict_to_vector(fdict, impute_values=self.impute).reshape(1, -1)
        thr = self.config.get("thresholds") or {}
        low_t = float(thr.get("low", 0.33))
        high_t = float(thr.get("moderate", 0.66))
        missing = float(fdict.get("missing_fraction") or 0.0)

        results: list[ConditionRisk] = []
        for d in DISEASES:
            did = d["id"]
            model = self.models.get(did)
            if model is None:
                prob = 0.0
                contribs: list[str] = []
            else:
                prob = float(model.predict_proba(vec)[0])
                prob = max(0.0, min(1.0, prob))
                contribs = [n for n, _ in model.feature_importance(FEATURE_COLUMNS, top_k=5)]
            conf = _confidence_from_missing(missing, prob)
            results.append(
                ConditionRisk(
                    disease_id=did,
                    name_en=d["name_en"],
                    risk_probability=prob,
                    risk_category=_band(prob, low_t, high_t),
                    confidence=conf,
                    top_contributors=contribs,
                    references=list(d.get("references") or []),
                )
            )
        return results

    def predict_summary(
        self,
        metrics: list[dict[str, Any]],
        *,
        demographics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conditions = self.predict_conditions(metrics, demographics=demographics)
        if not conditions:
            return {
                "risk_score": None,
                "risk_band": "unavailable",
                "conditions": [],
                "method": self.backend_name,
                "disclaimer_en": DISCLAIMER_EN,
                "disclaimer_hi": DISCLAIMER_HI,
            }
        # Overall score: mean of max risk (transparent aggregation)
        top = max(conditions, key=lambda c: c.risk_probability)
        avg = float(np.mean([c.risk_probability for c in conditions]))
        # drivers from highest risk condition
        drivers = tuple(top.top_contributors[:5])
        band = top.risk_category
        lines = [
            DISCLAIMER_EN,
            f"Highest elevated statistical risk among tracked conditions: "
            f"{top.name_en} ≈ {top.risk_probability:.0%} ({top.risk_category}). "
            f"Increased statistical risk only — not a diagnosis.",
        ]
        for c in sorted(conditions, key=lambda x: -x.risk_probability)[:3]:
            lines.append(
                f"- {c.name_en}: {c.risk_probability:.0%} ({c.risk_category}); "
                f"confidence {c.confidence:.0%}; contributors: "
                f"{', '.join(c.top_contributors[:3]) or 'n/a'}"
            )
        summary_en = " ".join(lines)
        summary_hi = (
            f"{DISCLAIMER_HI} सर्वोच्च जोखिम अनुमान: {top.name_en} "
            f"≈ {top.risk_probability:.0%} ({top.risk_category})। यह निदान नहीं है।"
        )
        return {
            "risk_score": avg,
            "risk_band": band if band != "low" else ("moderate" if avg >= 0.33 else "low"),
            "drivers": drivers,
            "summary_en": summary_en,
            "summary_hi": summary_hi,
            "method": f"disease_risk:{self.backend_name}",
            "conditions": [c.to_dict() for c in conditions],
            "disclaimer_en": DISCLAIMER_EN,
            "disclaimer_hi": DISCLAIMER_HI,
        }
