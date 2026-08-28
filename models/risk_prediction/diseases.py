"""Disease codes and non-diagnostic labels for risk models."""

from __future__ import annotations

from typing import Any

# Extensible registry of conditions — add new disease ids without refactoring
DISEASES: list[dict[str, Any]] = [
    {
        "id": "type2_diabetes",
        "name_en": "Type 2 Diabetes Risk",
        "name_hi": "टाइप 2 मधुमेह जोखिम",
        "references": (
            "WHO HbA1c diagnostic criteria (educational reference only)",
            "ADA Standards of Care — risk factors (not personalized diagnosis)",
        ),
    },
    {
        "id": "anemia",
        "name_en": "Anemia Risk",
        "name_hi": "एनीमिया जोखिम",
        "references": (
            "WHO haemoglobin cut-offs (population screening reference)",
            "NHS anaemia overview (educational)",
        ),
    },
    {
        "id": "ckd",
        "name_en": "Chronic Kidney Disease Risk",
        "name_hi": "दीर्घकालिक गुर्दा रोग जोखिम",
        "references": (
            "KDIGO CKD guidelines — biomarker context (not diagnosis)",
            "eGFR interpretive notes for education",
        ),
    },
    {
        "id": "liver_dysfunction",
        "name_en": "Liver Dysfunction Risk",
        "name_hi": "यकृत शिथिलता जोखिम",
        "references": (
            "Common LFT interpretive patterns (educational)",
            "ALT/AST elevation context — clinician confirmation required",
        ),
    },
    {
        "id": "thyroid_dysfunction",
        "name_en": "Thyroid Dysfunction Risk",
        "name_hi": "थायरॉइड शिथिलता जोखिम",
        "references": (
            "ATA thyroid function test interpretation primers",
            "NHS thyroid tests overview (educational)",
        ),
    },
]

DISCLAIMER_EN = (
    "Risk estimate only. This is not a medical diagnosis. "
    "For informational purposes only. Discuss results with a qualified clinician."
)

DISCLAIMER_HI = (
    "केवल जोखिम अनुमान। यह चिकित्सा निदान नहीं है। "
    "केवल सूचना के लिए। योग्य चिकित्सक से चर्चा करें।"
)

# Feature schema keys used in model matrices
FEATURE_COLUMNS: list[str] = [
    "age",
    "sex_female",  # 1 female, 0 male, 0.5 unknown
    "hemoglobin",
    "hba1c",
    "fasting_glucose",
    "random_glucose",
    "alt",
    "ast",
    "creatinine",
    "egfr",
    "urea",
    "tsh",
    "free_t4",
    "total_cholesterol",
    "hdl",
    "ldl",
    "triglycerides",
    "platelets",
    "wbc",
    "rbc",
    "bmi",
    "systolic_bp",
    "diastolic_bp",
    # derived
    "ast_alt_ratio",
    "tc_hdl_ratio",
    "non_hdl",
    "missing_fraction",
]

# Synonym map: feature key → surface test names (lower)
TEST_NAME_SYNONYMS: dict[str, list[str]] = {
    "hemoglobin": ["haemoglobin", "hemoglobin", "hb", "hgb"],
    "hba1c": ["hba1c", "a1c", "hb a1c", "glycated haemoglobin", "glycated hemoglobin"],
    "fasting_glucose": ["fasting glucose", "fbs", "fasting blood sugar", "fpg"],
    "random_glucose": ["random glucose", "rbs", "glucose", "blood glucose"],
    "alt": ["alt", "sgpt", "alanine aminotransferase"],
    "ast": ["ast", "sgot", "aspartate aminotransferase"],
    "creatinine": ["creatinine", "serum creatinine", "creat", "scr"],
    "egfr": ["egfr", "estimated gfr", "gfr"],
    "urea": ["urea", "blood urea", "bun", "serum urea"],
    "tsh": ["tsh", "thyroid stimulating hormone", "thyrotropin"],
    "free_t4": ["free t4", "ft4", "free thyroxine"],
    "total_cholesterol": ["total cholesterol", "cholesterol", "tc"],
    "hdl": ["hdl", "hdl cholesterol", "hdl-c"],
    "ldl": ["ldl", "ldl cholesterol", "ldl-c"],
    "triglycerides": ["triglycerides", "triglyceride", "tg"],
    "platelets": ["platelets", "plt", "platelet count"],
    "wbc": ["wbc", "tlc", "white blood cells", "total leucocyte count"],
    "rbc": ["rbc", "red blood cells", "erythrocytes"],
}
