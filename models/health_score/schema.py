"""Feature schema and clinical-style labels for health score (non-diagnostic)."""

from __future__ import annotations

from typing import Any

DISCLAIMER_EN = (
    "Health score estimate only. This is not a medical diagnosis or "
    "treatment recommendation. For informational purposes only. "
    "Discuss results with a qualified clinician."
)

DISCLAIMER_HI = (
    "केवल स्वास्थ्य स्कोर अनुमान। यह निदान या उपचार सलाह नहीं है। "
    "केवल सूचना के लिए। योग्य चिकित्सक से चर्चा करें।"
)

# Canonical feature order for models
FEATURE_COLUMNS: list[str] = [
    "age",
    "sex_female",
    "hba1c",
    "fasting_glucose",
    "random_glucose",
    "creatinine",
    "egfr",
    "alt",
    "ast",
    "total_cholesterol",
    "ldl",
    "hdl",
    "triglycerides",
    "tsh",
    "hemoglobin",
    "bmi",
    "systolic_bp",
    "diastolic_bp",
    # derived
    "ast_alt_ratio",
    "tc_hdl_ratio",
    "non_hdl",
    "missing_fraction",
    "n_recent_labs",
    # temporal
    "hba1c_slope",
    "creatinine_slope",
    "alt_slope",
    "hemoglobin_slope",
    # prior-phase aggregates (soft / rule proxies)
    "risk_mean_proxy",
    "risk_max_proxy",
    "forecast_worsening_proxy",
    "trend_penalty",
]

TEST_ALIASES: dict[str, list[str]] = {
    "hba1c": ["hba1c", "a1c", "hb a1c"],
    "fasting_glucose": ["fasting glucose", "fbs", "fpg", "fasting blood sugar"],
    "random_glucose": ["random glucose", "rbs", "glucose"],
    "creatinine": ["creatinine", "serum creatinine", "creat"],
    "egfr": ["egfr", "gfr", "estimated gfr"],
    "alt": ["alt", "sgpt", "alanine aminotransferase"],
    "ast": ["ast", "sgot", "aspartate aminotransferase"],
    "total_cholesterol": ["total cholesterol", "cholesterol", "tc"],
    "ldl": ["ldl", "ldl cholesterol", "ldl-c"],
    "hdl": ["hdl", "hdl cholesterol", "hdl-c"],
    "triglycerides": ["triglycerides", "triglyceride", "tg"],
    "tsh": ["tsh", "thyroid stimulating hormone"],
    "hemoglobin": ["haemoglobin", "hemoglobin", "hb", "hgb"],
    "bmi": ["bmi", "body mass index"],
    "systolic_bp": ["systolic", "sbp", "systolic bp"],
    "diastolic_bp": ["diastolic", "dbp", "diastolic bp"],
    "age": ["age"],
}


def score_to_band(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "fair"
    if score >= 40:
        return "watch"
    return "elevated"


def band_label_en(band: str) -> str:
    return {
        "excellent": "Excellent",
        "good": "Good",
        "fair": "Fair",
        "watch": "Watch",
        "elevated": "Elevated concern",
        "unavailable": "Unavailable",
    }.get(band, band.title())


def feature_display_name(feat: str) -> str:
    special = {
        "hba1c": "HbA1c",
        "hdl": "HDL",
        "ldl": "LDL",
        "alt": "ALT",
        "ast": "AST",
        "tsh": "TSH",
        "egfr": "eGFR",
        "risk_mean_proxy": "Aggregate risk signal",
        "risk_max_proxy": "Highest condition risk",
        "forecast_worsening_proxy": "Projected biomarker trends",
        "missing_fraction": "Missing labs",
        "sex_female": "Sex",
    }
    if feat in special:
        return special[feat]
    return feat.replace("_", " ").title()
