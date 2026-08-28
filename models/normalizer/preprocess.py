"""Text preprocessing for lab test name normalization."""

from __future__ import annotations

import re
import unicodedata

# British ↔ American orthography for our domain
_SPELLING_MAP = {
    "hemoglobin": "haemoglobin",
    "hematocrit": "haematocrit",
    "leukocyte": "leucocyte",
    "leukocytes": "leucocytes",
    "anemia": "anaemia",
}

# Common expansions applied before matching
_ABBREV_EXPAND = {
    r"\bh\.?b\.?\b": "haemoglobin",
    r"\bhgb\b": "haemoglobin",
    r"\bw\.?b\.?c\.?\b": "wbc",
    r"\br\.?b\.?c\.?\b": "rbc",
    r"\bp\.?l\.?t\.?\b": "platelets",
    r"\bt\.?g\.?\b": "triglycerides",
    r"\bhba1c\b": "hba1c",
    r"\ba1c\b": "hba1c",
    r"\bft3\b": "free t3",
    r"\bft4\b": "free t4",
    r"\bsgpt\b": "alt",
    r"\bsgot\b": "ast",
}


def preprocess_test_name(raw: str) -> str:
    """
    Normalize surface lab names for matching.

    Steps: unicode NFKC, whitespace, case fold, punctuation, spelling, tokens.
    """
    if raw is None:
        return ""
    text = unicodedata.normalize("NFKC", str(raw))
    text = text.replace("\u00a0", " ").replace("\t", " ")
    text = text.strip().lower()
    # drop leading bullets / numbering
    text = re.sub(r"^[\d\*\#\-\.\)]+\s*", "", text)
    # medical punctuation → space
    text = text.replace("%", " percent ")
    text = re.sub(r"[\[\]\{\}\(\)]", " ", text)
    text = re.sub(r"[/:|_=+]+", " ", text)
    text = re.sub(r"[.,;]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    for pat, repl in _ABBREV_EXPAND.items():
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)

    tokens = text.split()
    mapped = [_SPELLING_MAP.get(t, t) for t in tokens]
    text = " ".join(mapped)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preprocess_for_exact(raw: str) -> str:
    """Slightly lighter preprocess for exact alias table keys."""
    text = preprocess_test_name(raw)
    # collapse "hemoglobin blood" style trailing contexts lightly retained
    return text
