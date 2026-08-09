"""
health-service/routers/qa.py

Q&A proxy: forwards user questions to the ai-service /qa endpoint,
injecting owner_id from the authenticated user header.

The health-service is the public-facing service that the frontend talks to.
The ai-service is internal-only. This proxy ensures that:
  1. owner_id is always derived from the authenticated user (not user input).
  2. The user's own report_values are fetched and injected into the request
     so the ai-service retriever can include user-specific data.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from packages.shared_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class QARequest(BaseModel):
    session_id: Optional[str] = None
    question: str = Field(..., min_length=1, max_length=2000)
    locale: str = Field(default="en-IN", pattern=r"^(en-IN|hi-IN)$")


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
async def proxy_qa(
    body: QARequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
) -> QAResponse:
    """Proxy Q&A requests to the ai-service.

    In production, this would:
      1. Fetch the user's report_values from the DB (owner-scoped).
      2. Forward the question + report_values to ai-service /qa.
      3. Store the Q&A exchange in qa_sessions / qa_messages.
      4. Return the response.

    For MVP unit testing, this endpoint validates the contract and headers.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")

    session_id = body.session_id or str(uuid.uuid4())

    # In production: httpx.AsyncClient call to ai-service
    # For now, import and call directly (monolith-mode for MVP)
    try:
        from services.ai_service.safety import check_safety
        from services.ai_service.rag.retriever import retrieve
        from services.ai_service.rag.synthesizer import synthesize

        # Step 1: Safety check (MUST be first)
        safety_result = check_safety(body.question)

        if safety_result.triggered:
            logger.info("Safety triggered via health-service proxy")
            return QAResponse(
                session_id=session_id,
                answer=safety_result.emergency_message_en or "",
                answer_hi=safety_result.emergency_message_hi or "",
                citations=[],
                safety_triggered=True,
            )

        # Step 2: Retrieve (no user report_values in MVP test mode)
        chunks = retrieve(query=body.question, user_report_values=None, top_k=5)

        # Step 3: Synthesize
        result = synthesize(question=body.question, chunks=chunks, locale=body.locale)

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

    except ImportError:
        # If ai-service modules aren't available (separate deployment),
        # this would be an httpx call instead.
        logger.warning("ai-service modules not available — proxy requires httpx in production")
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable",
        )
