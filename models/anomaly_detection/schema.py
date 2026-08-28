"""Schema, labels, and safety language for Phase 7 anomaly detection."""

from __future__ import annotations

DISCLAIMER_EN = (
    "Anomalous laboratory pattern detection only. "
    "This is not a medical diagnosis. For informational purposes only. "
    "Discuss unusual patterns with a qualified clinician."
)

DISCLAIMER_HI = (
    "केवल असामान्य प्रयोगशाला पैटर्न पहचान। यह निदान नहीं है। "
    "केवल सूचना के लिए। योग्य चिकित्सक से चर्चा करें।"
)

FEATURE_COLUMNS: list[str] = [
    "age",
    "sex_female",
    "hba1c",
    "fasting_glucose",
    "creatinine",
    "egfr",
    "alt",
    "ast",
    "ldl",
    "hdl",
    "triglycerides",
    "tsh",
    "hemoglobin",
    "total_cholesterol",
    # derived
    "ast_alt_ratio",
    "non_hdl",
    "missing_fraction",
    "n_labs",
    # temporal / series (when single analyte)
    "series_last",
    "series_mean",
    "series_std",
    "series_slope",
    "series_delta",
    "series_robust_z",
    "series_n",
    # optional soft priors (proxies — no hard dep on prior phases)
    "risk_proxy",
    "forecast_shift_proxy",
    "health_score_proxy",
]

# Biomarker keys used for multi-marker contribution ranking
LAB_KEYS = [
    "hba1c",
    "fasting_glucose",
    "creatinine",
    "egfr",
    "alt",
    "ast",
    "ldl",
    "hdl",
    "triglycerides",
    "tsh",
    "hemoglobin",
    "total_cholesterol",
]

TEST_ALIASES: dict[str, list[str]] = {
    "hba1c": ["hba1c", "a1c", "hb a1c"],
    "fasting_glucose": ["fasting glucose", "fbs", "fpg", "glucose"],
    "creatinine": ["creatinine", "serum creatinine", "creat"],
    "egfr": ["egfr", "gfr"],
    "alt": ["alt", "sgpt"],
    "ast": ["ast", "sgot"],
    "ldl": ["ldl", "ldl cholesterol"],
    "hdl": ["hdl", "hdl cholesterol"],
    "triglycerides": ["triglycerides", "tg"],
    "tsh": ["tsh"],
    "hemoglobin": ["haemoglobin", "hemoglobin", "hb", "hgb"],
    "total_cholesterol": ["total cholesterol", "cholesterol", "tc"],
    "age": ["age"],
}


def category_from_score(score: float, thr_high: float = 0.75, thr_mod: float = 0.5) -> str:
    """score in [0,1] higher more anomalous."""
    if score >= thr_high:
        return "high"
    if score >= thr_mod:
        return "moderate"
    return "low"


def category_label(cat: str) -> str:
    return {"high": "High", "moderate": "Moderate", "low": "Low"}.get(cat, cat.title())
