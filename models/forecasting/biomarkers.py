"""Configurable biomarker registry for forecasting."""

from __future__ import annotations

from typing import Any

# Configurable list — extend without changing business logic
BIOMARKERS: list[dict[str, Any]] = [
    {"id": "hba1c", "name": "HbA1c", "unit": "%", "aliases": ["hba1c", "a1c", "hb a1c"]},
    {
        "id": "fasting_glucose",
        "name": "Fasting Glucose",
        "unit": "mg/dL",
        "aliases": ["fasting glucose", "fbs", "fpg"],
    },
    {
        "id": "random_glucose",
        "name": "Random Glucose",
        "unit": "mg/dL",
        "aliases": ["random glucose", "rbs", "glucose"],
    },
    {
        "id": "creatinine",
        "name": "Creatinine",
        "unit": "mg/dL",
        "aliases": ["creatinine", "serum creatinine", "creat"],
    },
    {"id": "egfr", "name": "eGFR", "unit": "mL/min/1.73m2", "aliases": ["egfr", "gfr"]},
    {
        "id": "alt",
        "name": "ALT",
        "unit": "U/L",
        "aliases": ["alt", "sgpt", "alanine aminotransferase"],
    },
    {
        "id": "ast",
        "name": "AST",
        "unit": "U/L",
        "aliases": ["ast", "sgot", "aspartate aminotransferase"],
    },
    {
        "id": "total_cholesterol",
        "name": "Total Cholesterol",
        "unit": "mg/dL",
        "aliases": ["total cholesterol", "cholesterol", "tc"],
    },
    {
        "id": "ldl",
        "name": "LDL",
        "unit": "mg/dL",
        "aliases": ["ldl", "ldl cholesterol", "ldl-c"],
    },
    {
        "id": "hdl",
        "name": "HDL",
        "unit": "mg/dL",
        "aliases": ["hdl", "hdl cholesterol", "hdl-c"],
    },
    {
        "id": "triglycerides",
        "name": "Triglycerides",
        "unit": "mg/dL",
        "aliases": ["triglycerides", "triglyceride", "tg"],
    },
    {
        "id": "tsh",
        "name": "TSH",
        "unit": "µIU/mL",
        "aliases": ["tsh", "thyroid stimulating hormone"],
    },
    {
        "id": "hemoglobin",
        "name": "Hemoglobin",
        "unit": "g/dL",
        "aliases": ["haemoglobin", "hemoglobin", "hb", "hgb"],
    },
]

DISCLAIMER_EN = (
    "Forecast estimate only. This is not a medical diagnosis or treatment "
    "recommendation. For informational purposes only. Discuss trends with "
    "a qualified clinician."
)

DISCLAIMER_HI = (
    "केवल पूर्वानुमान। यह निदान या उपचार सलाह नहीं है। "
    "केवल सूचना के लिए। चिकित्सक से चर्चा करें।"
)

# Lag / window feature names for one biomarker series (local FE vector)
POINT_FEATURE_NAMES = [
    "value",
    "age",
    "sex_female",
    "horizon_days",
    "n_obs",
    "days_span",
    "days_since_last",
    "lag1",
    "lag2",
    "lag3",
    "roll_mean_3",
    "roll_std_3",
    "roll_mean_all",
    "delta_last",
    "slope_per_day",
    "missing_frac",
]


def alias_to_id(test_name: str) -> str | None:
    key = " ".join((test_name or "").strip().lower().replace("_", " ").split())
    for b in BIOMARKERS:
        if key == b["id"] or key == b["name"].lower():
            return b["id"]
        for a in b.get("aliases") or []:
            if key == a or a in key or key in a:
                return b["id"]
    return None


def biomarker_meta(bid: str) -> dict[str, Any]:
    for b in BIOMARKERS:
        if b["id"] == bid:
            return b
    return {"id": bid, "name": bid, "unit": None, "aliases": []}
