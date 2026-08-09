"""
ai-service/rag/synthesizer.py

Template-based answer synthesis from retrieved chunks.

Combines retrieved knowledge base chunks and user report data into a
structured, cited answer. No external LLM API call — uses templates
to ensure deterministic, tone-compliant output.

TONE RULES (01_PROJECT_CONTEXT.md §4):
  - Never output a diagnosis or definitive medical claim.
  - Always frame as "commonly associated with", "may be worth discussing".
  - Every claim must reference its source via citation [N].
  - Include "consult your doctor" when discussing abnormal values.
"""

from __future__ import annotations

from .retriever import RetrievedChunk


# ---------------------------------------------------------------------------
# Citation formatting
# ---------------------------------------------------------------------------

def _format_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    """Build a citation list from retrieved chunks.

    Returns: [{"index": 1, "source": "...", "url": "..." or null}, ...]
    """
    citations = []
    seen_sources: set[str] = set()

    for i, chunk in enumerate(chunks, 1):
        # Deduplicate by source name
        if chunk.source in seen_sources:
            continue
        seen_sources.add(chunk.source)
        citations.append({
            "index": i,
            "source": chunk.source,
            "url": chunk.source_url,
        })

    return citations


# ---------------------------------------------------------------------------
# Answer templates
# ---------------------------------------------------------------------------

_ANSWER_TEMPLATE_EN = """Based on available medical references and your health data:

{body}

{user_data_section}

**Sources cited:**
{citation_list}

Please consult your healthcare provider for personalised interpretation of your results."""

_ANSWER_TEMPLATE_HI = """उपलब्ध चिकित्सा संदर्भों और आपके स्वास्थ्य डेटा के आधार पर:

{body}

{user_data_section}

**उद्धृत स्रोत:**
{citation_list}

अपने परिणामों की व्यक्तिगत व्याख्या के लिए कृपया अपने स्वास्थ्य सेवा प्रदाता से परामर्श करें।"""

_INSUFFICIENT_DATA_EN = (
    "I don't have enough information to answer this question comprehensively. "
    "Please consult your healthcare provider for guidance."
)

_INSUFFICIENT_DATA_HI = (
    "इस प्रश्न का व्यापक उत्तर देने के लिए मेरे पास पर्याप्त जानकारी नहीं है। "
    "कृपया मार्गदर्शन के लिए अपने स्वास्थ्य सेवा प्रदाता से परामर्श करें।"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def synthesize(
    question: str,
    chunks: list[RetrievedChunk],
    locale: str = "en-IN",
) -> dict:
    """Synthesize an answer from retrieved chunks.

    Args:
        question: The user's original question.
        chunks: Retrieved chunks from the knowledge base and/or user reports.
        locale: "en-IN" or "hi-IN".

    Returns:
        {
            "answer_en": str,
            "answer_hi": str,
            "citations": [{"index", "source", "url"}, ...],
        }
    """
    if not chunks:
        return {
            "answer_en": _INSUFFICIENT_DATA_EN,
            "answer_hi": _INSUFFICIENT_DATA_HI,
            "citations": [],
        }

    citations = _format_citations(chunks)

    # Build the body from knowledge base chunks
    kb_chunks = [c for c in chunks if not c.is_user_data]
    user_chunks = [c for c in chunks if c.is_user_data]

    # English body
    body_parts: list[str] = []
    citation_idx = 1
    source_to_idx: dict[str, int] = {}

    for c in citations:
        source_to_idx[c["source"]] = c["index"]

    for chunk in kb_chunks:
        idx = source_to_idx.get(chunk.source, citation_idx)
        # Summarise the chunk content (first 2–3 sentences)
        sentences = _extract_key_sentences(chunk.text, max_sentences=3)
        body_parts.append(f"{sentences} [{idx}]")

    body_en = "\n\n".join(body_parts) if body_parts else ""

    # User data section
    user_data_section_en = ""
    user_data_section_hi = ""
    if user_chunks:
        user_lines = []
        user_lines_hi = []
        for uc in user_chunks:
            idx = source_to_idx.get(uc.source, len(citations))
            user_lines.append(f"- {uc.text} [{idx}]")
            user_lines_hi.append(f"- {uc.text} [{idx}]")
        user_data_section_en = "**From your own health records:**\n" + "\n".join(user_lines)
        user_data_section_hi = "**आपके अपने स्वास्थ्य रिकॉर्ड से:**\n" + "\n".join(user_lines_hi)

    # Citation list
    citation_list_en = "\n".join(
        f"[{c['index']}] {c['source']}" + (f" — {c['url']}" if c["url"] else "")
        for c in citations
    )
    citation_list_hi = citation_list_en  # Same references in both languages

    answer_en = _ANSWER_TEMPLATE_EN.format(
        body=body_en,
        user_data_section=user_data_section_en,
        citation_list=citation_list_en,
    ).strip()

    # Hindi answer: translate the body using simple template substitution
    body_hi = _translate_body_to_hindi(body_en)

    answer_hi = _ANSWER_TEMPLATE_HI.format(
        body=body_hi,
        user_data_section=user_data_section_hi,
        citation_list=citation_list_hi,
    ).strip()

    return {
        "answer_en": answer_en,
        "answer_hi": answer_hi,
        "citations": citations,
    }


def _extract_key_sentences(text: str, max_sentences: int = 3) -> str:
    """Extract the first N meaningful sentences from a chunk."""
    import re
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter out very short fragments and headers
    meaningful = [
        s.strip() for s in sentences
        if len(s.strip()) > 20 and not s.strip().startswith("|")
    ]
    return " ".join(meaningful[:max_sentences])


def _translate_body_to_hindi(body_en: str) -> str:
    """Simple template-based EN→HI translation for common medical phrases.

    This is NOT a full translation engine — it substitutes key medical terms
    and wraps the English content in a Hindi context frame. For a production
    system, an actual translation API or model would be used.
    """
    _PHRASE_MAP = {
        "Normal range": "सामान्य सीमा",
        "normal range": "सामान्य सीमा",
        "High": "अधिक",
        "Low": "कम",
        "may indicate": "संकेत कर सकता है",
        "commonly associated with": "आमतौर पर जुड़ा होता है",
        "consult your doctor": "अपने डॉक्टर से परामर्श करें",
        "consult your healthcare provider": "अपने स्वास्थ्य सेवा प्रदाता से परामर्श करें",
        "Please": "कृपया",
    }

    result = body_en
    for en, hi in _PHRASE_MAP.items():
        result = result.replace(en, hi)

    return result
