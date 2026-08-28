"""
Reusable explainability helpers for MediVault ML models (Phase 6+).

Provides Tree SHAP when `shap` is installed; falls back to
model-native importance and deviation-based local attributions.
Business logic must not hard-depend on SHAP availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np


@dataclass
class LocalExplanation:
    feature: str
    contribution: float  # signed; + raises score, - lowers score
    abs_contribution: float
    percent: float  # share of total abs contributions * 100
    direction: str  # positive | negative | neutral


@dataclass
class ExplanationBundle:
    local: list[LocalExplanation] = field(default_factory=list)
    global_importance: list[tuple[str, float]] = field(default_factory=list)
    method: str = "none"
    positive_labels: list[str] = field(default_factory=list)
    negative_labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "local": [
                {
                    "feature": e.feature,
                    "contribution": e.contribution,
                    "percent": e.percent,
                    "direction": e.direction,
                }
                for e in self.local
            ],
            "global_importance": [
                {"feature": n, "importance": float(v)} for n, v in self.global_importance
            ],
            "positive_contributors": list(self.positive_labels),
            "negative_contributors": list(self.negative_labels),
        }


def _pretty_feature(name: str) -> str:
    return name.replace("_", " ").title()


def contribution_labels(
    local: Sequence[LocalExplanation], top_k: int = 5
) -> tuple[list[str], list[str]]:
    pos = sorted([e for e in local if e.contribution > 0], key=lambda e: -e.contribution)
    neg = sorted([e for e in local if e.contribution < 0], key=lambda e: e.contribution)
    pos_l = [f"{_pretty_feature(e.feature)} (+{e.percent:.0f}%)" for e in pos[:top_k]]
    neg_l = [f"{_pretty_feature(e.feature)} ({e.percent:.0f}%)" for e in neg[:top_k]]
    return pos_l, neg_l


def build_local_from_values(
    feature_names: Sequence[str],
    contributions: Sequence[float],
    *,
    eps: float = 1e-12,
) -> list[LocalExplanation]:
    contribs = np.asarray(contributions, dtype=float)
    abs_c = np.abs(contribs)
    total = float(abs_c.sum()) + eps
    out: list[LocalExplanation] = []
    for name, c, a in zip(feature_names, contribs, abs_c):
        if a < eps:
            continue
        direction = "positive" if c > 0 else ("negative" if c < 0 else "neutral")
        out.append(
            LocalExplanation(
                feature=str(name),
                contribution=float(c),
                abs_contribution=float(a),
                percent=float(100.0 * a / total),
                direction=direction,
            )
        )
    out.sort(key=lambda e: -e.abs_contribution)
    return out


def explain_tree_model(
    model: Any,
    X_row: np.ndarray,
    feature_names: Sequence[str],
    *,
    background: np.ndarray | None = None,
    top_k: int = 8,
) -> ExplanationBundle:
    """
    Prefer SHAP TreeExplainer; fallback to gain * centered feature values.
    X_row: shape (1, n_features) or (n_features,)
    """
    x = np.asarray(X_row, dtype=float).reshape(1, -1)
    names = list(feature_names)
    global_imp: list[tuple[str, float]] = []

    raw = getattr(model, "_model", model)

    # Global importance
    try:
        if hasattr(raw, "feature_importances_"):
            imp = np.asarray(raw.feature_importances_, dtype=float)
            global_imp = sorted(
                zip(names, imp.tolist()), key=lambda t: -t[1]
            )[: max(top_k, 10)]
        elif hasattr(raw, "get_booster"):
            # xgboost sklearn API
            score = raw.get_booster().get_score(importance_type="gain")
            mapped = []
            for i, n in enumerate(names):
                key = f"f{i}"
                mapped.append((n, float(score.get(key, 0.0))))
            global_imp = sorted(mapped, key=lambda t: -t[1])[: max(top_k, 10)]
    except Exception:
        global_imp = []

    # Local SHAP
    method = "shap_tree"
    contribs: np.ndarray | None = None
    try:
        import shap  # type: ignore

        explainer = shap.TreeExplainer(raw)
        sv = explainer.shap_values(x)
        if isinstance(sv, list):
            sv = sv[0]
        contribs = np.asarray(sv, dtype=float).reshape(-1)
        method = "shap_tree"
    except Exception:
        method = "fallback_centered"
        center = (
            np.asarray(background, dtype=float).mean(axis=0)
            if background is not None and len(background)
            else np.zeros(x.shape[1])
        )
        imp_arr = np.ones(x.shape[1], dtype=float)
        if global_imp:
            m = {n: v for n, v in global_imp}
            imp_arr = np.asarray([m.get(n, 1e-3) for n in names], dtype=float)
            if imp_arr.sum() > 0:
                imp_arr = imp_arr / imp_arr.sum()
        contribs = (x.reshape(-1) - center) * (-imp_arr)
        # higher labs often worsen score → flip is absorbed in trained model residual
        # Use signed (feature - center) * importance * sign heuristics later in engine

    local = build_local_from_values(names, contribs, eps=1e-9)[:top_k]
    pos, neg = contribution_labels(local, top_k=5)
    return ExplanationBundle(
        local=local,
        global_importance=global_imp,
        method=method,
        positive_labels=pos,
        negative_labels=neg,
    )


def explain_linear_model(
    coef: Sequence[float],
    X_row: np.ndarray,
    feature_names: Sequence[str],
    *,
    means: Sequence[float] | None = None,
    top_k: int = 8,
) -> ExplanationBundle:
    x = np.asarray(X_row, dtype=float).reshape(-1)
    c = np.asarray(coef, dtype=float).reshape(-1)
    m = (
        np.asarray(means, dtype=float).reshape(-1)
        if means is not None
        else np.zeros_like(x)
    )
    contribs = c * (x - m)
    local = build_local_from_values(feature_names, contribs)[:top_k]
    abs_c = np.abs(c)
    if abs_c.sum() > 0:
        abs_c = abs_c / abs_c.sum()
    global_imp = sorted(zip(feature_names, abs_c.tolist()), key=lambda t: -t[1])[
        : max(top_k, 10)
    ]
    pos, neg = contribution_labels(local, top_k=5)
    return ExplanationBundle(
        local=local,
        global_importance=global_imp,
        method="linear_coef",
        positive_labels=pos,
        negative_labels=neg,
    )


def shap_available() -> bool:
    try:
        import shap  # noqa: F401

        return True
    except Exception:
        return False
