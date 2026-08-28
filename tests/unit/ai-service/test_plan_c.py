"""Plan C regression tests: IE fixtures + tone sanitizer."""

from __future__ import annotations


class TestToneSanitize:
    def test_removes_you_have(self):
        from services.ai_service.rag.synthesizer import _sanitize_tone

        out = _sanitize_tone("This does not mean you have a medical condition today.")
        assert "you have" not in out.lower()

    def test_rewrites_diagnosed_with(self):
        from services.ai_service.rag.synthesizer import _sanitize_tone

        out = _sanitize_tone("For people already diagnosed with diabetes, targets vary.")
        assert "diagnosed with" not in out.lower()


class TestIEFixtures:
    def test_field_f1_above_threshold(self):
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(root / "data" / "datasets"))
        from plan_c.ie_eval import evaluate_ie

        metrics = evaluate_ie()
        assert metrics["recall"] == 1.0
        assert metrics["f1"] >= 0.95
