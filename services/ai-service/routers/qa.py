"""
ai-service/routers/qa.py

POST /qa — Evidence-based Q&A endpoint with safety-first architecture.

Flow:
  1. Safety check FIRST (deterministic red-flag regex). If triggered → return
     fixed emergency message immediately, do NOT proceed to RAG.
  2. Retrieve relevant chunks (knowledge base + user report history).
  3. Synthesize cited answer (template-based, bilingual EN/HI).
  4. Return answer with citations.

ARCHITECTURE RULE (main.py, 03_MVP_SCOPE.md §4):
  The safety layer MUST run before any RAG/LLM call. This is non-negotiable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from packages.shared_utils import get_logger

from ..core.registry import get_retriever
from ..rag.retriever import RetrievedChunk
from ..rag.synthesizer import synthesize
from ..safety import check_safety

logger = get_logger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class QARequest(BaseModel):
    session_id: Optional[str] = None
    question: str = Field(..., min_length=1, max_length=2000)
    locale: str = Field(default="en-IN", pattern=r"^(en-IN|hi-IN)$")
    user_report_values: Optional[list[dict]] = Field(
        default=None,
        description="User's own report values (owner-scoped, injected by health-service proxy).",
    )


class CitationOut(BaseModel):
    index: int
    source: str
    url: Optional[str] = None


class QAResponse(BaseModel):
    session_id: str
    answer: str
    answer_hi: str
    citations: list[CitationOut]
    safety_triggered: bool


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=QAResponse)
async def ask_question(
    body: QARequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
) -> QAResponse:
    """Handle a user's health Q&A question.

    SAFETY CHECK runs FIRST — before any retrieval or generation.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")

    session_id = body.session_id or str(uuid.uuid4())

    # ----- STEP 1: Deterministic safety check (MUST be first) -----
    safety_result = check_safety(body.question)

    if safety_result.triggered:
        logger.info(
            "Safety layer triggered for category=%s",
            safety_result.matched_category,
        )
        return QAResponse(
            session_id=session_id,
            answer=safety_result.emergency_message_en or "",
            answer_hi=safety_result.emergency_message_hi or "",
            citations=[],
            safety_triggered=True,
        )

    # ----- STEP 2: Retrieve relevant chunks (Retriever interface → BM25 default) -----
    retrieved = get_retriever().retrieve(
        query=body.question,
        user_report_values=body.user_report_values,
        top_k=5,
    )
    chunks = [
        RetrievedChunk(
            text=c.text,
            source=c.source,
            source_url=c.source_url,
            score=c.score,
            is_user_data=c.is_user_data,
        )
        for c in retrieved
    ]

    # ----- STEP 3: Synthesize answer -----
    result = synthesize(
        question=body.question,
        chunks=chunks,
        locale=body.locale,
    )

    citations_out = [
        CitationOut(index=c["index"], source=c["source"], url=c.get("url"))
        for c in result["citations"]
    ]

    return QAResponse(
        session_id=session_id,
        answer=result["answer_en"],
        answer_hi=result["answer_hi"],
        citations=citations_out,
        safety_triggered=False,
    )
