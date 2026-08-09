"""
tests/unit/ai-service/test_parser.py

Parser acceptance criteria tests (03_MVP_SCOPE.md Feature 1):
  "Extracts at least the common panels (CBC, lipid profile, thyroid, HbA1c)
   with correct value/unit/reference-range pairing."

Also verifies the explainer tone rules (01_PROJECT_CONTEXT.md §4):
  - Never states a diagnosis.
  - Always frames as "commonly associated with" or "may be worth discussing".
"""

import pytest
from decimal import Decimal

# ---------------------------------------------------------------------------
# Sample lab report text — representative of Indian lab printout format
# ---------------------------------------------------------------------------

SAMPLE_CBC_TEXT = """
COMPLETE BLOOD COUNT (CBC)
=========================================
TEST NAME           RESULT    UNIT    REFERENCE RANGE
-----------------------------------------
Haemoglobin         12.5      g/dL    (13.0 - 17.0)
WBC                 8500      /cumm   (4500 - 11000)
RBC                 4.2       mill/cumm (4.5 - 5.5)
Platelets           180000    /cumm   (150000 - 400000)
Hematocrit          38.0      %       (40.0 - 50.0)
MCV                 88.0      fL      (80.0 - 100.0)
MCH                 28.5      pg      (27.0 - 33.0)
MCHC                32.0      g/dL    (31.5 - 34.5)
Neutrophils         65        %       (40 - 75)
Lymphocytes         28        %       (20 - 45)
"""

SAMPLE_LIPID_TEXT = """
LIPID PROFILE
=========================================
Total Cholesterol   210       mg/dL   (< 200)
LDL Cholesterol     135       mg/dL   (< 100)
HDL Cholesterol     45        mg/dL   (> 40)
Triglycerides       185       mg/dL   (< 150)
VLDL Cholesterol    37        mg/dL   (< 40)
"""

SAMPLE_THYROID_TEXT = """
THYROID FUNCTION TEST
=========================================
TSH                 6.8       µIU/mL  (0.4 - 4.0)
Free T4             0.9       ng/dL   (0.8 - 1.8)
Free T3             3.1       pg/mL   (2.3 - 4.2)
"""

SAMPLE_HBA1C_TEXT = """
DIABETES PANEL
=========================================
HbA1c               6.8       %       (< 5.7)
"""

SAMPLE_MIXED_TEXT = (
    SAMPLE_CBC_TEXT + "\n" + SAMPLE_LIPID_TEXT + "\n" +
    SAMPLE_THYROID_TEXT + "\n" + SAMPLE_HBA1C_TEXT
)


# ---------------------------------------------------------------------------
# Stub OCR backend — returns pre-defined text
# ---------------------------------------------------------------------------

class StubOcr:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        return self._text


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestCBCParsing:
    def setup_method(self):
        from services.ai_service.parsers.report_parser import ReportParser

        self.parser = ReportParser(ocr=StubOcr(SAMPLE_CBC_TEXT))

    def test_haemoglobin_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        hb = next((r for r in results if r.test_name == "Haemoglobin"), None)
        assert hb is not None, "Haemoglobin not found in parsed values"
        assert hb.value_numeric == Decimal("12.5")

    def test_wbc_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        wbc = next((r for r in results if r.test_name == "WBC"), None)
        assert wbc is not None
        assert wbc.value_numeric == Decimal("8500")

    def test_platelets_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        plt = next((r for r in results if r.test_name == "Platelets"), None)
        assert plt is not None
        assert plt.value_numeric == Decimal("180000")

    def test_panel_tagged_as_cbc(self):
        results = self.parser.parse(b"", "application/pdf")
        hb = next((r for r in results if r.test_name == "Haemoglobin"), None)
        assert hb is not None
        assert hb.panel == "CBC"

    def test_no_duplicate_test_names(self):
        results = self.parser.parse(b"", "application/pdf")
        names = [r.test_name for r in results]
        assert len(names) == len(set(names)), "Duplicate test names found"


class TestLipidParsing:
    def setup_method(self):
        from services.ai_service.parsers.report_parser import ReportParser

        self.parser = ReportParser(ocr=StubOcr(SAMPLE_LIPID_TEXT))

    def test_total_cholesterol_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        tc = next((r for r in results if r.test_name == "Total Cholesterol"), None)
        assert tc is not None
        assert tc.value_numeric == Decimal("210")

    def test_ldl_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        ldl = next((r for r in results if r.test_name == "LDL Cholesterol"), None)
        assert ldl is not None
        assert ldl.value_numeric == Decimal("135")

    def test_hdl_panel_tagged(self):
        results = self.parser.parse(b"", "application/pdf")
        hdl = next((r for r in results if r.test_name == "HDL Cholesterol"), None)
        assert hdl is not None
        assert hdl.panel == "Lipid Profile"


class TestThyroidParsing:
    def setup_method(self):
        from services.ai_service.parsers.report_parser import ReportParser

        self.parser = ReportParser(ocr=StubOcr(SAMPLE_THYROID_TEXT))

    def test_tsh_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        tsh = next((r for r in results if r.test_name == "TSH"), None)
        assert tsh is not None
        assert tsh.value_numeric == Decimal("6.8")

    def test_free_t4_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        ft4 = next((r for r in results if r.test_name == "Free T4"), None)
        assert ft4 is not None

    def test_thyroid_panel_tagged(self):
        results = self.parser.parse(b"", "application/pdf")
        tsh = next((r for r in results if r.test_name == "TSH"), None)
        assert tsh is not None
        assert tsh.panel == "Thyroid"


class TestHbA1cParsing:
    def setup_method(self):
        from services.ai_service.parsers.report_parser import ReportParser

        self.parser = ReportParser(ocr=StubOcr(SAMPLE_HBA1C_TEXT))

    def test_hba1c_extracted(self):
        results = self.parser.parse(b"", "application/pdf")
        a1c = next((r for r in results if r.test_name == "HbA1c"), None)
        assert a1c is not None
        assert a1c.value_numeric == Decimal("6.8")

    def test_hba1c_panel_tagged(self):
        results = self.parser.parse(b"", "application/pdf")
        a1c = next((r for r in results if r.test_name == "HbA1c"), None)
        assert a1c is not None
        assert a1c.panel == "HbA1c"


# ---------------------------------------------------------------------------
# Explainer tests — tone rules (01_PROJECT_CONTEXT.md §4)
# ---------------------------------------------------------------------------

DIAGNOSIS_KEYWORDS = [
    "you have",
    "you are diagnosed",
    "diagnosed with",
    "you suffer from",
    "you are suffering",
]


class TestExplainerTone:
    def _explain(self, test_name, value_numeric, ref_low=None, ref_high=None, ref_text=None, unit=None):
        from services.ai_service.explainer.explainer import explain

        return explain(
            test_name=test_name,
            value_numeric=value_numeric,
            value_text=None,
            unit=unit,
            reference_range_low=ref_low,
            reference_range_high=ref_high,
            reference_range_text=ref_text,
        )

    def test_normal_haemoglobin_no_diagnosis(self):
        exp = self._explain("Haemoglobin", Decimal("14.5"), Decimal("13.0"), Decimal("17.0"))
        assert exp.status == "normal"
        for kw in DIAGNOSIS_KEYWORDS:
            assert kw not in exp.explanation_en.lower(), f"Diagnosis keyword '{kw}' found in explanation"

    def test_high_tsh_no_diagnosis(self):
        """Even a clearly elevated TSH must not say 'you have hypothyroidism'."""
        exp = self._explain("TSH", Decimal("6.8"), Decimal("0.4"), Decimal("4.0"))
        assert exp.status == "high"
        assert "hypothyroid" not in exp.explanation_en.lower() or "associated" in exp.explanation_en.lower()
        for kw in DIAGNOSIS_KEYWORDS:
            assert kw not in exp.explanation_en.lower(), f"Diagnosis keyword '{kw}' found"

    def test_low_haemoglobin_no_diagnosis(self):
        """Low Hb must not say 'you have anaemia' as a statement."""
        exp = self._explain("Haemoglobin", Decimal("10.5"), Decimal("13.0"), Decimal("17.0"))
        assert exp.status == "low"
        # Should say "associated with" or "worth discussing", not definitive diagnosis
        en = exp.explanation_en.lower()
        assert "associated with" in en or "worth discussing" in en or "may be" in en
        for kw in DIAGNOSIS_KEYWORDS:
            assert kw not in en, f"Diagnosis keyword '{kw}' found"

    def test_high_hba1c_no_diagnosis(self):
        exp = self._explain("HbA1c", Decimal("7.2"), Decimal("4.0"), Decimal("5.7"))
        assert exp.status == "high"
        for kw in DIAGNOSIS_KEYWORDS:
            assert kw not in exp.explanation_en.lower()

    def test_hindi_explanation_generated(self):
        exp = self._explain("Haemoglobin", Decimal("12.0"), Decimal("13.0"), Decimal("17.0"))
        assert exp.explanation_hi
        assert len(exp.explanation_hi) > 20, "Hindi explanation is too short to be real"

    def test_hindi_no_diagnosis_keywords(self):
        """Key Hindi diagnosis phrases must not appear."""
        hindi_diagnosis_phrases = ["आपको यह बीमारी है", "आप बीमार हैं"]
        exp = self._explain("TSH", Decimal("7.0"), Decimal("0.4"), Decimal("4.0"))
        for phrase in hindi_diagnosis_phrases:
            assert phrase not in exp.explanation_hi

    def test_unknown_status_when_no_ref_range(self):
        exp = self._explain("Haemoglobin", Decimal("14.5"), ref_low=None, ref_high=None)
        assert exp.status == "unknown"

    def test_explanation_includes_test_name(self):
        exp = self._explain("Total Cholesterol", Decimal("210"), Decimal("0"), Decimal("200"))
        assert "Total Cholesterol" in exp.explanation_en or "cholesterol" in exp.explanation_en.lower()
