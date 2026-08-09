"""
tests/unit/ai-service/test_safety.py

Tests for the deterministic safety layer (red-flag detection).

Validates:
  - All 5 red-flag categories trigger deterministically
  - Non-flag inputs don't trigger
  - EN + HI emergency messages are present
  - Latency < 100ms
  - Hindi red-flag patterns also trigger
"""

import time

import pytest


# ---------------------------------------------------------------------------
# Fixtures — import safety module with hyphenated path handling
# ---------------------------------------------------------------------------

@pytest.fixture
def check_safety():
    """Import check_safety from the ai-service safety module."""
    from services.ai_service.safety.red_flags import check_safety
    return check_safety


@pytest.fixture
def SafetyResult():
    """Import SafetyResult for type checking."""
    from services.ai_service.safety.red_flags import SafetyResult
    return SafetyResult


# ---------------------------------------------------------------------------
# Trigger tests — each red-flag category
# ---------------------------------------------------------------------------

class TestCardiacEmergency:
    """Cardiac emergency patterns trigger correctly."""

    def test_chest_pain_and_breathing(self, check_safety):
        result = check_safety("I have chest pain and difficulty breathing")
        assert result.triggered is True
        assert result.matched_category == "cardiac_emergency"

    def test_heart_attack(self, check_safety):
        result = check_safety("am I having a heart attack")
        assert result.triggered is True
        assert result.matched_category == "cardiac_emergency"

    def test_hindi_cardiac(self, check_safety):
        result = check_safety("seene mein dard aur saans lene mein takleef")
        assert result.triggered is True
        assert result.matched_category == "cardiac_emergency"


class TestGastrointestinalBleeding:
    """GI bleeding patterns trigger correctly."""

    def test_blood_in_stool(self, check_safety):
        result = check_safety("I noticed blood in my stool today")
        assert result.triggered is True
        assert result.matched_category == "gastrointestinal_bleeding"

    def test_blood_in_urine(self, check_safety):
        result = check_safety("there is blood in my urine")
        assert result.triggered is True
        assert result.matched_category == "gastrointestinal_bleeding"

    def test_vomiting_blood(self, check_safety):
        result = check_safety("I am vomiting blood")
        assert result.triggered is True
        assert result.matched_category == "gastrointestinal_bleeding"


class TestSuddenVisionLoss:
    """Vision loss patterns trigger correctly."""

    def test_sudden_vision_loss(self, check_safety):
        result = check_safety("I suddenly lost my vision in my left eye")
        assert result.triggered is True
        assert result.matched_category == "sudden_vision_loss"

    def test_suddenly_cant_see(self, check_safety):
        result = check_safety("suddenly I can't see anything")
        assert result.triggered is True
        assert result.matched_category == "sudden_vision_loss"


class TestStrokeSymptoms:
    """Stroke symptom patterns trigger correctly."""

    def test_slurred_speech(self, check_safety):
        result = check_safety("my speech is slurred and I feel dizzy")
        assert result.triggered is True
        assert result.matched_category == "stroke_symptoms"

    def test_face_drooping(self, check_safety):
        result = check_safety("one side of my face is drooping")
        assert result.triggered is True
        assert result.matched_category == "stroke_symptoms"

    def test_numbness_one_side(self, check_safety):
        result = check_safety("I have numbness in one side of my body")
        assert result.triggered is True
        assert result.matched_category == "stroke_symptoms"

    def test_word_stroke(self, check_safety):
        result = check_safety("I think I am having a stroke")
        assert result.triggered is True
        assert result.matched_category == "stroke_symptoms"


class TestSuicidalIdeation:
    """Suicidal ideation patterns trigger correctly."""

    def test_want_to_kill_myself(self, check_safety):
        result = check_safety("I want to kill myself")
        assert result.triggered is True
        assert result.matched_category == "suicidal_ideation"

    def test_suicide(self, check_safety):
        result = check_safety("thinking about suicide")
        assert result.triggered is True
        assert result.matched_category == "suicidal_ideation"

    def test_self_harm(self, check_safety):
        result = check_safety("I've been self-harming")
        assert result.triggered is True
        assert result.matched_category == "suicidal_ideation"

    def test_dont_want_to_live(self, check_safety):
        result = check_safety("I don't want to live anymore")
        assert result.triggered is True
        assert result.matched_category == "suicidal_ideation"

    def test_hindi_suicidal(self, check_safety):
        result = check_safety("mujhe marna hai")
        assert result.triggered is True
        assert result.matched_category == "suicidal_ideation"


# ---------------------------------------------------------------------------
# Non-trigger tests — normal health questions must NOT trigger
# ---------------------------------------------------------------------------

class TestNonTrigger:
    """Normal health questions must not trigger the safety layer."""

    @pytest.mark.parametrize("question", [
        "What does my high cholesterol mean?",
        "My haemoglobin is 10 g/dL, is that low?",
        "How can I improve my blood sugar levels?",
        "What is a normal TSH range?",
        "I have a headache, should I be worried?",
        "My LDL has been rising for the last 3 tests",
        "Can you explain my CBC report?",
        "What foods help lower triglycerides?",
        "Is HbA1c of 6.2% considered pre-diabetes?",
        "My doctor said my iron is low",
    ])
    def test_normal_questions_do_not_trigger(self, check_safety, question):
        result = check_safety(question)
        assert result.triggered is False
        assert result.matched_category is None


# ---------------------------------------------------------------------------
# Response quality tests
# ---------------------------------------------------------------------------

class TestResponseQuality:
    """Triggered results contain proper emergency messages."""

    def test_english_message_present(self, check_safety):
        result = check_safety("chest pain and breathing difficulty")
        assert result.triggered is True
        assert result.emergency_message_en is not None
        assert len(result.emergency_message_en) > 50
        assert "emergency" in result.emergency_message_en.lower() or "112" in result.emergency_message_en

    def test_hindi_message_present(self, check_safety):
        result = check_safety("chest pain and breathing difficulty")
        assert result.triggered is True
        assert result.emergency_message_hi is not None
        assert len(result.emergency_message_hi) > 20

    def test_suicidal_message_has_helpline(self, check_safety):
        result = check_safety("I want to end my life")
        assert result.triggered is True
        assert "988" in result.emergency_message_en or "iCall" in result.emergency_message_en
        assert "112" in result.emergency_message_hi or "iCall" in result.emergency_message_hi


# ---------------------------------------------------------------------------
# Performance test — must complete in < 100ms
# ---------------------------------------------------------------------------

class TestPerformance:
    """Safety check must complete within 100ms (deterministic regex)."""

    def test_latency_under_100ms(self, check_safety):
        # Run 100 checks and verify average is under 100ms
        start = time.perf_counter()
        for _ in range(100):
            check_safety("I have chest pain and difficulty breathing")
            check_safety("What is my cholesterol level?")
        elapsed_ms = (time.perf_counter() - start) * 1000 / 200  # per check

        assert elapsed_ms < 100, f"Safety check took {elapsed_ms:.2f}ms on average (limit: 100ms)"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case handling."""

    def test_empty_string(self, check_safety):
        result = check_safety("")
        assert result.triggered is False

    def test_none_text(self, check_safety):
        result = check_safety(None)
        assert result.triggered is False

    def test_whitespace_only(self, check_safety):
        result = check_safety("   \n\t  ")
        assert result.triggered is False

    def test_case_insensitive(self, check_safety):
        result = check_safety("CHEST PAIN AND BREATHING DIFFICULTY")
        assert result.triggered is True
