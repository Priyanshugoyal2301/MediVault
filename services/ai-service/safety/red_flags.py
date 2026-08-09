"""
ai-service/safety/red_flags.py

Deterministic (rule-based, non-ML) safety check for health Q&A inputs.

ARCHITECTURE RULE (03_MVP_SCOPE.md §4, 01_PROJECT_CONTEXT.md §4):
  This module MUST run BEFORE any LLM/RAG call on every /qa request.
  If a red-flag pattern matches, a fixed, non-AI-generated emergency-guidance
  message is returned immediately. The LLM/ML layer never has the final say
  on an emergency escalation.

  Red-flag phrases → fixed message, deterministically, in <100ms.

ADDING NEW PATTERNS:
  Add a new entry to _RED_FLAG_RULES with:
    - "patterns": list of compiled regex patterns (case-insensitive)
    - "message_en": fixed English emergency message
    - "message_hi": fixed Hindi emergency message
  Then add a test in tests/unit/ai-service/test_safety.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SafetyResult:
    """Outcome of a deterministic safety check."""

    triggered: bool
    matched_category: str | None = None
    emergency_message_en: str | None = None
    emergency_message_hi: str | None = None


_SAFE = SafetyResult(triggered=False)

# ---------------------------------------------------------------------------
# Red-flag rule definitions
# ---------------------------------------------------------------------------

_RED_FLAG_RULES: list[dict] = [
    {
        "category": "cardiac_emergency",
        "patterns": [
            re.compile(r"chest\s+pain.*breath", re.IGNORECASE),
            re.compile(r"breath.*chest\s+pain", re.IGNORECASE),
            re.compile(r"heart\s+attack", re.IGNORECASE),
            re.compile(r"(seene|chhati)\s+(mein|me)\s+dard.*(saans|breath)", re.IGNORECASE),
        ],
        "message_en": (
            "Your message mentions symptoms that could indicate a medical emergency. "
            "Please call emergency services (112 in India, 911 in the US, 999 in the UK) "
            "or go to your nearest emergency room immediately. "
            "Do not wait for an online response."
        ),
        "message_hi": (
            "आपके संदेश में ऐसे लक्षणों का उल्लेख है जो चिकित्सा आपातकाल का संकेत हो सकते हैं। "
            "कृपया तुरंत आपातकालीन सेवाओं को कॉल करें (भारत में 112) "
            "या अपने निकटतम आपातकालीन कक्ष में जाएं। "
            "ऑनलाइन उत्तर की प्रतीक्षा न करें।"
        ),
    },
    {
        "category": "gastrointestinal_bleeding",
        "patterns": [
            re.compile(r"blood\s+in\s+(\w+\s+)?(stool|feces|poop)", re.IGNORECASE),
            re.compile(r"blood\s+in\s+(\w+\s+)?urine", re.IGNORECASE),
            re.compile(r"(vomiting|throwing\s+up)\s+blood", re.IGNORECASE),
            re.compile(r"(khoon|rakt).*(peshab|toilet|potty)", re.IGNORECASE),
        ],
        "message_en": (
            "Blood in stool, urine, or vomit can be a sign of a serious condition. "
            "Please contact your doctor or visit a hospital as soon as possible. "
            "If the bleeding is heavy, call emergency services immediately (112)."
        ),
        "message_hi": (
            "मल, पेशाब या उल्टी में खून एक गंभीर स्थिति का संकेत हो सकता है। "
            "कृपया जल्द से जल्द अपने डॉक्टर से संपर्क करें या अस्पताल जाएं। "
            "यदि रक्तस्राव अधिक है, तो तुरंत आपातकालीन सेवाओं (112) को कॉल करें।"
        ),
    },
    {
        "category": "sudden_vision_loss",
        "patterns": [
            re.compile(r"sudden(ly)?\s+(\w+\s+)*(vision\s+loss|blind|can'?t\s+see)", re.IGNORECASE),
            re.compile(r"(lost|losing)\s+(\w+\s+)?vision", re.IGNORECASE),
            re.compile(r"sudden(ly)?\s+(\w+\s+)*(lost|lose)\s+(\w+\s+)?vision", re.IGNORECASE),
            re.compile(r"achanak.*(dikhai|nazar).*(nahi|band)", re.IGNORECASE),
        ],
        "message_en": (
            "Sudden vision loss can be a medical emergency. "
            "Please go to an emergency room or eye hospital immediately. "
            "Early treatment may be critical — do not delay."
        ),
        "message_hi": (
            "अचानक दृष्टि हानि एक चिकित्सा आपातकाल हो सकती है। "
            "कृपया तुरंत आपातकालीन कक्ष या नेत्र अस्पताल जाएं। "
            "शीघ्र उपचार महत्वपूर्ण हो सकता है — देरी न करें।"
        ),
    },
    {
        "category": "stroke_symptoms",
        "patterns": [
            re.compile(r"slurred\s+speech", re.IGNORECASE),
            re.compile(r"speech\s+(\w+\s+)*slurred", re.IGNORECASE),
            re.compile(r"face\s+(\w+\s+)*(droop|numb)", re.IGNORECASE),
            re.compile(r"(numbness|weakness)\s+(\w+\s+)*(one\s+side|arm|leg|face)", re.IGNORECASE),
            re.compile(r"stroke", re.IGNORECASE),
            re.compile(r"(haath|pair|chehra).*(sunn|kamzor)", re.IGNORECASE),
        ],
        "message_en": (
            "Your message describes symptoms that could indicate a stroke. "
            "Remember FAST: Face drooping, Arm weakness, Speech difficulty, Time to call emergency services. "
            "Call 112 (India) or your local emergency number immediately. "
            "Every minute matters."
        ),
        "message_hi": (
            "आपके संदेश में स्ट्रोक के संकेत हो सकते हैं। "
            "FAST याद रखें: चेहरा झुकना, बांह में कमजोरी, बोलने में कठिनाई, समय पर कॉल करें। "
            "तुरंत 112 या अपने स्थानीय आपातकालीन नंबर पर कॉल करें। "
            "हर मिनट मायने रखता है।"
        ),
    },
    {
        "category": "suicidal_ideation",
        "patterns": [
            re.compile(r"(want\s+to|going\s+to)\s+(kill|end|hurt)\s+(myself|my\s+life)", re.IGNORECASE),
            re.compile(r"suicid", re.IGNORECASE),  # matches suicide, suicidal
            re.compile(r"self[\s-]?harm", re.IGNORECASE),
            re.compile(r"don'?t\s+want\s+to\s+live", re.IGNORECASE),
            re.compile(r"(marna|aatmhatya|khudkhushi)", re.IGNORECASE),
        ],
        "message_en": (
            "It sounds like you may be going through a very difficult time. "
            "You are not alone, and help is available right now.\n\n"
            "Please reach out to a crisis helpline:\n"
            "  - India: iCall — 9152987821 | Vandrevala Foundation — 1860-2662-345\n"
            "  - US: 988 Suicide & Crisis Lifeline — call or text 988\n"
            "  - UK: Samaritans — 116 123\n\n"
            "If you are in immediate danger, please call emergency services (112 / 911 / 999)."
        ),
        "message_hi": (
            "ऐसा लगता है कि आप बहुत कठिन समय से गुजर रहे हैं। "
            "आप अकेले नहीं हैं, और अभी मदद उपलब्ध है।\n\n"
            "कृपया किसी क्राइसिस हेल्पलाइन से संपर्क करें:\n"
            "  - iCall: 9152987821\n"
            "  - वंद्रेवाला फाउंडेशन: 1860-2662-345\n\n"
            "यदि आप तत्काल खतरे में हैं, तो कृपया आपातकालीन सेवाओं (112) को कॉल करें।"
        ),
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_safety(text: str) -> SafetyResult:
    """Run all red-flag pattern checks against *text*.

    Returns a SafetyResult. If ``triggered`` is True, the caller MUST return
    the fixed emergency message without proceeding to RAG/LLM.

    Designed to complete in <100ms (pure regex, no ML).
    """
    if not text or not text.strip():
        return _SAFE

    for rule in _RED_FLAG_RULES:
        for pattern in rule["patterns"]:
            if pattern.search(text):
                return SafetyResult(
                    triggered=True,
                    matched_category=rule["category"],
                    emergency_message_en=rule["message_en"],
                    emergency_message_hi=rule["message_hi"],
                )

    return _SAFE
