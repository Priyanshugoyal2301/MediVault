"""Rule-based non-diagnostic risk baseline (threshold heuristics)."""

from __future__ import annotations

from typing import Any


def rule_based_probs(features: dict[str, Any]) -> dict[str, float]:
    """Simple threshold baseline — risk estimates only, not diagnoses."""

    def g(k: str, default: float | None = None) -> float | None:
        v = features.get(k)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    out = {
        "type2_diabetes": 0.15,
        "anemia": 0.15,
        "ckd": 0.15,
        "liver_dysfunction": 0.15,
        "thyroid_dysfunction": 0.15,
    }
    hba1c, fpg = g("hba1c"), g("fasting_glucose")
    if hba1c is not None and hba1c >= 6.5:
        out["type2_diabetes"] = 0.82
    elif hba1c is not None and hba1c >= 5.7:
        out["type2_diabetes"] = 0.55
    elif fpg is not None and fpg >= 126:
        out["type2_diabetes"] = 0.75
    elif fpg is not None and fpg >= 100:
        out["type2_diabetes"] = 0.45

    hb = g("hemoglobin")
    sex_f = g("sex_female", 0.5) or 0.5
    cut = 12.0 if sex_f >= 0.5 else 13.0
    if hb is not None and hb < cut - 1:
        out["anemia"] = 0.78
    elif hb is not None and hb < cut:
        out["anemia"] = 0.5

    egfr, creat = g("egfr"), g("creatinine")
    if egfr is not None and egfr < 60:
        out["ckd"] = 0.8
    elif creat is not None and creat > 1.3:
        out["ckd"] = 0.55

    alt, ast = g("alt"), g("ast")
    if (alt is not None and alt > 55) or (ast is not None and ast > 50):
        out["liver_dysfunction"] = 0.72

    tsh = g("tsh")
    if tsh is not None and (tsh > 4.5 or tsh < 0.3):
        out["thyroid_dysfunction"] = 0.7
    return out
