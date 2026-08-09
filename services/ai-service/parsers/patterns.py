"""
ai-service/parsers/patterns.py

Regex patterns for extracting structured values from lab report text.
Covers the four MVP-required panels: CBC, lipid profile, thyroid, HbA1c.

Pattern design principles:
- Case-insensitive.
- Handles common Indian lab report formats:
    * "TestName : value unit (ref: low-high)"
    * Table format: "TestName | value | unit | ref range"
    * Variations in spacing, colon vs tab, comma vs period for decimals.
- value_numeric group: captures the numeric result.
- unit group: captures the unit string.
- ref_low / ref_high groups: capture reference range bounds when present.
  ref_text: captures the raw reference range string as fallback.

Each entry in PANEL_PATTERNS is:
  (panel_name, canonical_test_name, compiled_regex)
"""

import re
from dataclasses import dataclass
from typing import Pattern


@dataclass(frozen=True)
class PanelPattern:
    panel: str
    test_name: str
    pattern: Pattern[str]


def _p(panel: str, name: str, raw: str) -> PanelPattern:
    return PanelPattern(panel=panel, test_name=name, pattern=re.compile(raw, re.IGNORECASE))


# Common sub-patterns
_NUM = r"(\d+(?:[.,]\d+)?)"   # numeric value (allows comma as decimal separator)
_UNIT = r"([\w/%µμ]+(?:/[\w]+)*)"  # unit like g/dL, %, IU/L, mmol/L
_SEP = r"[\s:|\t]+"              # separator between label and value
_REF = r"(?:" + r"[\s(\[]+" + _NUM + r"\s*[-–to]+\s*" + _NUM + r")?"  # optional ref range


def _build(panel: str, name: str, aliases: list[str]) -> PanelPattern:
    """Build a PanelPattern matching any of the aliases followed by value/unit/ref."""
    alt = "|".join(re.escape(a) for a in aliases)
    raw = (
        rf"(?:{alt}){_SEP}{_NUM}"          # label : value
        rf"(?:\s*{_UNIT})?"                 # optional unit
        + r"(?:\s*[\[(]?\s*"               # optional ref range
        + _NUM + r"\s*[-–to]+\s*" + _NUM
        + r"\s*[\])]?)?"
    )
    return _p(panel, name, raw)


# ---------------------------------------------------------------------------
# CBC panel
# ---------------------------------------------------------------------------
_CBC = "CBC"
CBC_PATTERNS: list[PanelPattern] = [
    _build(_CBC, "Haemoglobin",      ["haemoglobin", "hemoglobin", "hb", "hgb"]),
    _build(_CBC, "WBC",              ["wbc", "white blood cell", "white blood cells", "leukocytes", "total wbc count", "total leucocyte count", "tlc"]),
    _build(_CBC, "RBC",              ["rbc", "red blood cell", "red blood cells", "erythrocytes", "total rbc count"]),
    _build(_CBC, "Platelets",        ["platelets", "platelet count", "plt", "thrombocytes"]),
    _build(_CBC, "Hematocrit",       ["hematocrit", "haematocrit", "pcv", "packed cell volume"]),
    _build(_CBC, "MCV",              ["mcv", "mean corpuscular volume"]),
    _build(_CBC, "MCH",              ["mch", "mean corpuscular haemoglobin", "mean corpuscular hemoglobin"]),
    _build(_CBC, "MCHC",             ["mchc", "mean corpuscular haemoglobin concentration", "mean corpuscular hemoglobin concentration"]),
    _build(_CBC, "Neutrophils",      ["neutrophils", "neutrophil", "neut", "segs", "segmented neutrophils"]),
    _build(_CBC, "Lymphocytes",      ["lymphocytes", "lymphocyte", "lymph"]),
    _build(_CBC, "Monocytes",        ["monocytes", "monocyte", "mono"]),
    _build(_CBC, "Eosinophils",      ["eosinophils", "eosinophil", "eos"]),
    _build(_CBC, "Basophils",        ["basophils", "basophil", "baso"]),
]

# ---------------------------------------------------------------------------
# Lipid profile panel
# ---------------------------------------------------------------------------
_LIP = "Lipid Profile"
LIPID_PATTERNS: list[PanelPattern] = [
    _build(_LIP, "Total Cholesterol",  ["total cholesterol", "cholesterol", "serum cholesterol"]),
    _build(_LIP, "LDL Cholesterol",    ["ldl cholesterol", "ldl-c", "ldl", "low density lipoprotein"]),
    _build(_LIP, "HDL Cholesterol",    ["hdl cholesterol", "hdl-c", "hdl", "high density lipoprotein"]),
    _build(_LIP, "Triglycerides",      ["triglycerides", "triglyceride", "tg", "trigs"]),
    _build(_LIP, "VLDL Cholesterol",   ["vldl cholesterol", "vldl-c", "vldl", "very low density lipoprotein"]),
    _build(_LIP, "Non-HDL Cholesterol",["non-hdl cholesterol", "non hdl", "non-hdl"]),
    _build(_LIP, "TC/HDL Ratio",       ["tc/hdl", "cholesterol/hdl ratio", "total cholesterol/hdl"]),
]

# ---------------------------------------------------------------------------
# Thyroid panel
# ---------------------------------------------------------------------------
_THY = "Thyroid"
THYROID_PATTERNS: list[PanelPattern] = [
    _build(_THY, "TSH",     ["tsh", "thyroid stimulating hormone", "thyrotropin"]),
    _build(_THY, "T3",      ["t3", "triiodothyronine", "total t3", "serum t3"]),
    _build(_THY, "T4",      ["t4", "thyroxine", "total t4", "serum t4"]),
    _build(_THY, "Free T3", ["free t3", "ft3", "free triiodothyronine"]),
    _build(_THY, "Free T4", ["free t4", "ft4", "free thyroxine"]),
]

# ---------------------------------------------------------------------------
# HbA1c panel
# ---------------------------------------------------------------------------
_A1C = "HbA1c"
HBA1C_PATTERNS: list[PanelPattern] = [
    _build(_A1C, "HbA1c",             ["hba1c", "hb a1c", "glycated haemoglobin", "glycated hemoglobin", "glycosylated haemoglobin", "glycosylated hemoglobin", "a1c"]),
    _build(_A1C, "eAG (Est. Avg Glucose)", ["eag", "estimated average glucose"]),
]

# ---------------------------------------------------------------------------
# Combined list — parser iterates this in order
# ---------------------------------------------------------------------------
ALL_PATTERNS: list[PanelPattern] = (
    CBC_PATTERNS + LIPID_PATTERNS + THYROID_PATTERNS + HBA1C_PATTERNS
)
