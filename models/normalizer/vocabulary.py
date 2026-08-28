"""
Curated lab vocabulary + LOINC mapping + synthetic synonyms.

LOINC: codes are public identifiers from Regenstrief LOINC®. We ship only a
minimal curated subset for MediVault MVP panels (not the full LOINC release).
Users should consult https://loinc.org for full licensing when redistributing.

UMLS: we do not redistribut UMLS Metathesaurus content. Synonym edges here are
synthetic / publicly common medical abbreviations (education domain only).
"""

from __future__ import annotations

from typing import Any

# MediVault product canons (British haem-* where already used by patterns/explainer)
CANONICAL_CONCEPTS: list[dict[str, Any]] = [
    # CBC
    {"canonical": "Haemoglobin", "panel": "CBC", "loinc": "718-7", "unit": "g/dL"},
    {"canonical": "WBC", "panel": "CBC", "loinc": "6690-2", "unit": "/µL"},
    {"canonical": "RBC", "panel": "CBC", "loinc": "789-8", "unit": "million/µL"},
    {"canonical": "Platelets", "panel": "CBC", "loinc": "777-3", "unit": "/µL"},
    {"canonical": "Hematocrit", "panel": "CBC", "loinc": "4544-3", "unit": "%"},
    {"canonical": "MCV", "panel": "CBC", "loinc": "787-2", "unit": "fL"},
    {"canonical": "MCH", "panel": "CBC", "loinc": "785-6", "unit": "pg"},
    {"canonical": "MCHC", "panel": "CBC", "loinc": "786-4", "unit": "g/dL"},
    {"canonical": "Neutrophils", "panel": "CBC", "loinc": "770-8", "unit": "%"},
    {"canonical": "Lymphocytes", "panel": "CBC", "loinc": "736-9", "unit": "%"},
    {"canonical": "Monocytes", "panel": "CBC", "loinc": "5905-5", "unit": "%"},
    {"canonical": "Eosinophils", "panel": "CBC", "loinc": "711-2", "unit": "%"},
    {"canonical": "Basophils", "panel": "CBC", "loinc": "704-7", "unit": "%"},
    # Lipid
    {"canonical": "Total Cholesterol", "panel": "Lipid Profile", "loinc": "2093-3", "unit": "mg/dL"},
    {"canonical": "LDL Cholesterol", "panel": "Lipid Profile", "loinc": "2089-1", "unit": "mg/dL"},
    {"canonical": "HDL Cholesterol", "panel": "Lipid Profile", "loinc": "2085-9", "unit": "mg/dL"},
    {"canonical": "Triglycerides", "panel": "Lipid Profile", "loinc": "2571-8", "unit": "mg/dL"},
    {"canonical": "VLDL Cholesterol", "panel": "Lipid Profile", "loinc": "13457-7", "unit": "mg/dL"},
    {"canonical": "Non-HDL Cholesterol", "panel": "Lipid Profile", "loinc": "43396-1", "unit": "mg/dL"},
    {"canonical": "TC/HDL Ratio", "panel": "Lipid Profile", "loinc": "9830-1", "unit": None},
    # Thyroid
    {"canonical": "TSH", "panel": "Thyroid", "loinc": "3016-3", "unit": "µIU/mL"},
    {"canonical": "T3", "panel": "Thyroid", "loinc": "3053-6", "unit": "ng/dL"},
    {"canonical": "T4", "panel": "Thyroid", "loinc": "3026-2", "unit": "µg/dL"},
    {"canonical": "Free T3", "panel": "Thyroid", "loinc": "3051-0", "unit": "pg/mL"},
    {"canonical": "Free T4", "panel": "Thyroid", "loinc": "3024-7", "unit": "ng/dL"},
    # Diabetes
    {"canonical": "HbA1c", "panel": "HbA1c", "loinc": "4548-4", "unit": "%"},
    {"canonical": "eAG (Est. Avg Glucose)", "panel": "HbA1c", "loinc": "27353-2", "unit": "mg/dL"},
]

# Alias surface forms → canonical (lower keys applied after preprocess)
# Expanded Indian lab + UK/US spellings + common abbreviations.
SYNTHETIC_SYNONYMS: dict[str, list[str]] = {
    "Haemoglobin": [
        "hb", "hgb", "hemoglobin", "haemoglobin", "hemoglobin (blood)",
        "haemoglobin (hb)", "hemoglobin (hb)", "hb.", "hgb.", "hb blood",
        "haemglobin", "hemoglobon", "hb-blood", "serum hemoglobin",
    ],
    "WBC": [
        "wbc", "tlc", "total leucocyte count", "total leukocyte count",
        "total wbc count", "white blood cells", "white blood cell",
        "leukocytes", "leucocytes", "white cell count", "twbc",
    ],
    "RBC": [
        "rbc", "red blood cell", "red blood cells", "erythrocytes",
        "total rbc count", "red cell count", "r.b.c.",
    ],
    "Platelets": [
        "plt", "platelets", "platelet count", "plt. count", "plt count",
        "thrombocytes", "platelet", "plts",
    ],
    "Hematocrit": [
        "pcv", "hematocrit", "haematocrit", "packed cell volume", "hct", "ht",
    ],
    "MCV": ["mcv", "mean corpuscular volume", "mean cell volume"],
    "MCH": [
        "mch", "mean corpuscular haemoglobin", "mean corpuscular hemoglobin",
        "mean cell haemoglobin", "mean cell hemoglobin",
    ],
    "MCHC": [
        "mchc", "mean corpuscular haemoglobin concentration",
        "mean corpuscular hemoglobin concentration",
    ],
    "Neutrophils": [
        "neutrophils", "neutrophil", "neut", "segs", "segmented neutrophils",
        "polymorphs", "pmn",
    ],
    "Lymphocytes": ["lymphocytes", "lymphocyte", "lymph", "lym"],
    "Monocytes": ["monocytes", "monocyte", "mono"],
    "Eosinophils": ["eosinophils", "eosinophil", "eos"],
    "Basophils": ["basophils", "basophil", "baso"],
    "Total Cholesterol": [
        "total cholesterol", "cholesterol total", "serum cholesterol",
        "cholesterol", "tc", "chol", "t.chol",
    ],
    "LDL Cholesterol": [
        "ldl", "ldl cholesterol", "ldl-c", "ldlc", "low density lipoprotein",
        "low-density lipoprotein", "ldl chol",
    ],
    "HDL Cholesterol": [
        "hdl", "hdl cholesterol", "hdl-c", "hdlc", "high density lipoprotein",
        "high-density lipoprotein", "h.d.l. cholesterol", "hdl chol",
    ],
    "Triglycerides": [
        "triglycerides", "triglyceride", "tg", "trigs", "tri glycerides", "t.g.",
    ],
    "VLDL Cholesterol": [
        "vldl", "vldl cholesterol", "vldl-c", "very low density lipoprotein",
    ],
    "Non-HDL Cholesterol": [
        "non-hdl", "non hdl", "non-hdl cholesterol", "non hdl cholesterol",
        "nonhdl", "non hdl chol",
    ],
    "TC/HDL Ratio": [
        "tc/hdl", "cholesterol/hdl ratio", "total cholesterol/hdl",
        "tc hdl ratio", "chol/hdl",
    ],
    "TSH": [
        "tsh", "thyroid stimulating hormone", "thyrotropin",
        "tsh (ultrasensitive)", "tsh(ultrasensitive)", "s.tsh",
    ],
    "T3": ["t3", "triiodothyronine", "total t3", "serum t3", "t-3"],
    "T4": ["t4", "thyroxine", "total t4", "serum t4", "t-4"],
    "Free T3": ["free t3", "ft3", "free triiodothyronine", "f.t3"],
    "Free T4": ["free t4", "ft4", "free thyroxine", "f.t4"],
    "HbA1c": [
        "hba1c", "a1c", "hb a1c", "glycosylated hemoglobin",
        "glycosylated haemoglobin", "glycated hemoglobin", "glycated haemoglobin",
        "glycosylated hemoglobin (hba1c)", "glycosylated haemoglobin (hba1c)",
        "glycohb", "hb1ac",
    ],
    "eAG (Est. Avg Glucose)": [
        "eag", "estimated average glucose", "estimated average glucose (eag)",
        "est avg glucose", "estimated avg glucose",
    ],
}

# Liver enzymes often on Indian reports (beyond MVP patterns — still normalize names
# for OCR path; explainer may not know them; LOINC public codes used).
EXTENDED_CONCEPTS: list[dict[str, Any]] = [
    {
        "canonical": "Alanine Aminotransferase",
        "panel": "LFT",
        "loinc": "1742-6",
        "unit": "U/L",
        "aliases": ["alt", "sgpt", "alanine aminotransferase", "serum gpt", "gpt"],
    },
    {
        "canonical": "Aspartate Aminotransferase",
        "panel": "LFT",
        "loinc": "1920-8",
        "unit": "U/L",
        "aliases": ["ast", "sgot", "aspartate aminotransferase", "serum got", "got"],
    },
    {
        "canonical": "Alkaline Phosphatase",
        "panel": "LFT",
        "loinc": "6768-6",
        "unit": "U/L",
        "aliases": ["alp", "alkaline phosphatase", "alk phos", "alkp"],
    },
    {
        "canonical": "Bilirubin Total",
        "panel": "LFT",
        "loinc": "1975-2",
        "unit": "mg/dL",
        "aliases": ["total bilirubin", "bilirubin total", "tbil", "bilirubin"],
    },
    {
        "canonical": "Creatinine",
        "panel": "RFT",
        "loinc": "2160-0",
        "unit": "mg/dL",
        "aliases": ["creatinine", "serum creatinine", "creat", "scr"],
    },
    {
        "canonical": "Urea",
        "panel": "RFT",
        "loinc": "3094-0",
        "unit": "mg/dL",
        "aliases": ["urea", "blood urea", "bun urea", "serum urea"],
    },
]


def build_full_vocabulary() -> list[dict[str, Any]]:
    """Merge MVP canons + extended LFT/RFT into a unified vocabulary list."""
    out: list[dict[str, Any]] = []
    for c in CANONICAL_CONCEPTS:
        row = dict(c)
        row["aliases"] = list(SYNTHETIC_SYNONYMS.get(c["canonical"], []))
        # include canonical itself
        row["aliases"].append(c["canonical"].lower())
        out.append(row)
    for c in EXTENDED_CONCEPTS:
        out.append(dict(c))
    return out


def loinc_for(canonical: str) -> str | None:
    for c in build_full_vocabulary():
        if c["canonical"].lower() == (canonical or "").lower():
            return c.get("loinc")
    return None


def unit_for(canonical: str) -> str | None:
    for c in build_full_vocabulary():
        if c["canonical"].lower() == (canonical or "").lower():
            return c.get("unit")
    return None


def alias_lookup_table() -> dict[str, str]:
    """Lowercased surface → canonical."""
    table: dict[str, str] = {}
    for c in build_full_vocabulary():
        canon = c["canonical"]
        table[canon.lower()] = canon
        for a in c.get("aliases") or []:
            table[str(a).strip().lower()] = canon
    return table
