"""
Synthetic India-style lab report text fixtures for IE bake-off.

Hypothesis: Regex IE fails on common layout/alias variants; hardening aliases
and separators lifts field-level exact-match F1 by ≥0.05 on hard fixtures.
No neural training — synthetic gold labels only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldField:
    test_name: str
    value: float
    unit: str | None = None


@dataclass(frozen=True)
class IEFixture:
    fixture_id: str
    layout: str  # colon | table | messy | alias_heavy
    text: str
    gold: list[GoldField]


def load_fixtures() -> list[IEFixture]:
    return [
        IEFixture(
            fixture_id="cbc_colon_easy",
            layout="colon",
            text="""
COMPLETE BLOOD COUNT
Haemoglobin : 13.5 g/dL (12.0-17.0)
WBC : 7200 /µL (4000-11000)
Platelets : 250000 /µL (150000-400000)
RBC : 4.8 mill/cumm (4.5-5.5)
""",
            gold=[
                GoldField("Haemoglobin", 13.5, "g/dL"),
                GoldField("WBC", 7200.0, None),
                GoldField("Platelets", 250000.0, None),
                GoldField("RBC", 4.8, None),
            ],
        ),
        IEFixture(
            fixture_id="cbc_table_pipes",
            layout="table",
            text="""
Test | Result | Unit | Reference
Hemoglobin | 11,2 | g/dL | 12.0-15.0
Total Leucocyte Count | 9.1 | x10^3/uL | 4.0-11.0
Platelet Count | 1.8 | lakh/cumm | 1.5-4.0
PCV | 36.5 | % | 36-46
""",
            gold=[
                GoldField("Haemoglobin", 11.2, "g/dL"),
                GoldField("WBC", 9.1, None),
                GoldField("Platelets", 1.8, None),
                GoldField("Hematocrit", 36.5, "%"),
            ],
        ),
        IEFixture(
            fixture_id="lipid_alias_heavy",
            layout="alias_heavy",
            text="""
LIPID PROFILE (12 hrs fasting)
Serum Cholesterol .... 248 mg/dL  Desirable <200
LDL-C : 162 mg/dl (Optimal <100)
HDL-C = 38 mg/dL
TG : 210 mg/dL
Non HDL : 210 mg/dL
""",
            gold=[
                GoldField("Total Cholesterol", 248.0, "mg/dL"),
                GoldField("LDL Cholesterol", 162.0, "mg/dl"),
                GoldField("HDL Cholesterol", 38.0, "mg/dL"),
                GoldField("Triglycerides", 210.0, "mg/dL"),
                GoldField("Non-HDL Cholesterol", 210.0, "mg/dL"),
            ],
        ),
        IEFixture(
            fixture_id="thyroid_messy",
            layout="messy",
            text="""
THYROID FUNCTION TEST
TSH(Ultrasensitive)  6.8  mIU/L   0.4 - 4.0
Free T4              0.9  ng/dL  0.8-1.8
FT3                  2.9  pg/mL
""",
            gold=[
                GoldField("TSH", 6.8, "mIU/L"),
                GoldField("Free T4", 0.9, "ng/dL"),
                GoldField("Free T3", 2.9, "pg/mL"),
            ],
        ),
        IEFixture(
            fixture_id="hba1c_alias",
            layout="alias_heavy",
            text="""
DIABETES MONITORING
Glycosylated Hemoglobin (HbA1c) : 7.4 % (4.0-5.6)
Estimated Average Glucose (eAG) : 166 mg/dL
""",
            gold=[
                GoldField("HbA1c", 7.4, "%"),
                GoldField("eAG (Est. Avg Glucose)", 166.0, "mg/dL"),
            ],
        ),
        IEFixture(
            fixture_id="cbc_hb_dot_alias",
            layout="alias_heavy",
            text="""
Hb.  9.8 g%   (Male 13-17)
TLC  11200 cells/cmm
Plt. Count : 98000 /cmm
""",
            gold=[
                GoldField("Haemoglobin", 9.8, None),
                GoldField("WBC", 11200.0, None),
                GoldField("Platelets", 98000.0, None),
            ],
        ),
        IEFixture(
            fixture_id="lipid_spaced_dots",
            layout="messy",
            text="""
Cholesterol Total : 190
LDL Cholesterol : 118 mg/dL
H.D.L. Cholesterol : 45
Triglyceride : 140
""",
            gold=[
                GoldField("Total Cholesterol", 190.0, None),
                GoldField("LDL Cholesterol", 118.0, "mg/dL"),
                GoldField("HDL Cholesterol", 45.0, None),
                GoldField("Triglycerides", 140.0, None),
            ],
        ),
        IEFixture(
            fixture_id="mixed_panel_noise",
            layout="messy",
            text="""
Patient: DEMO  Age: 34  Lab: PathCare Delhi
-------------------------------------------
HbA1c                  5.9 %
TSH                    2.1 uIU/ml
LDL                    99 mg/dL
Haemoglobin (HB)       14.1 g/dL
Method: HPLC / CLIA — for research use notes ignore
""",
            gold=[
                GoldField("HbA1c", 5.9, "%"),
                GoldField("TSH", 2.1, None),
                GoldField("LDL Cholesterol", 99.0, "mg/dL"),
                GoldField("Haemoglobin", 14.1, "g/dL"),
            ],
        ),
    ]
