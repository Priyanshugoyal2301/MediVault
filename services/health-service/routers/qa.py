"""
health-service/routers/qa.py

Q&A proxy: loads owner-scoped report values, then forwards to ai-service /qa.
owner_id always comes from the X-User-ID header (injected by the BFF).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared_utils import get_logger

from ..core.config import Settings, get_settings
from ..db.models import Report, ReportValue
from ..care.document_scope import DocumentScope, document_scope
from ..db.repositories.report_repository import ReportRepository
from ..db.session import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])


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


def _get_owner_id(x_user_id: Annotated[str | None, Header()] = None) -> uuid.UUID:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-ID header")
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-ID")


async def _load_user_report_values(
    db: AsyncSession,
    owner_id: uuid.UUID,
    limit: int = 50,
    scope=None,
) -> list[dict]:
    result = await db.execute(
        select(ReportValue)
        .where(ReportValue.report_id.in_(select(Report.id).where(ReportRepository(db, scope).predicate(owner_id))))
        .order_by(ReportValue.created_at.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    return [
        {
            "test_name": r.test_name,
            "value_numeric": float(r.value_numeric) if r.value_numeric is not None else None,
            "value_text": r.value_text,
            "unit": r.unit,
            "date_of_test": r.date_of_test.isoformat() if r.date_of_test else None,
            "panel": r.panel,
            "explanation_en": getattr(r, "explanation_en", None),
        }
        for r in rows
    ]


@router.post("", response_model=QAResponse)
async def proxy_qa(
    body: QARequest,
    owner_id: Annotated[uuid.UUID, Depends(_get_owner_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Annotated[DocumentScope, Depends(document_scope)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QAResponse:
    session_id = body.session_id or str(uuid.uuid4())
    if scope.pediatric:
        from services.ai_service.safety import check_safety
        safety = check_safety(body.question)
        return QAResponse(session_id=session_id,
            answer=(safety.emergency_message_en if safety.triggered else
                    "This is a child's record. Open the original report and review its age-specific reference ranges with the child's clinician. Automated interpretation of pediatric results is not available."),
            answer_hi=(safety.emergency_message_hi if safety.triggered else
                       "यह बच्चे का रिकॉर्ड है। मूल रिपोर्ट और आयु के अनुसार संदर्भ सीमाओं की समीक्षा बच्चे के डॉक्टर के साथ करें। बच्चों के परिणामों की स्वचालित व्याख्या उपलब्ध नहीं है।"),
            citations=[], safety_triggered=safety.triggered)
    user_values = await _load_user_report_values(db, owner_id, scope=scope)

    headers = {"X-User-Id": str(owner_id)}
    if settings.internal_service_key:
        headers["X-Internal-Key"] = settings.internal_service_key

    payload = {
        "session_id": session_id,
        "question": body.question,
        "locale": body.locale,
        "user_report_values": user_values,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ai_service_base_url}/qa",
                json=payload,
                headers=headers,
            )
        if response.status_code >= 400:
            logger.error("AI QA failed status=%s", response.status_code)
            raise HTTPException(status_code=503, detail="AI service unavailable")
        data = response.json()
    except httpx.HTTPError as exc:
        logger.error("AI QA transport error: %s", type(exc).__name__)
        # Fallback: in-process call for local monolith-style demos
        try:
            return await _local_qa_fallback(body, session_id, user_values)
        except Exception:
            raise HTTPException(status_code=503, detail="AI service unavailable") from exc

    return QAResponse(
        session_id=data.get("session_id", session_id),
        answer=data["answer"],
        answer_hi=data["answer_hi"],
        citations=[CitationOut(**c) for c in data.get("citations", [])],
        safety_triggered=bool(data.get("safety_triggered")),
    )


async def _local_qa_fallback(
    body: QARequest,
    session_id: str,
    user_values: list[dict],
) -> QAResponse:
    from services.ai_service.rag.retriever import retrieve
    from services.ai_service.rag.synthesizer import synthesize
    from services.ai_service.safety import check_safety

    safety_result = check_safety(body.question)
    if safety_result.triggered:
        return QAResponse(
            session_id=session_id,
            answer=safety_result.emergency_message_en or "",
            answer_hi=safety_result.emergency_message_hi or "",
            citations=[],
            safety_triggered=True,
        )

    chunks = retrieve(query=body.question, user_report_values=user_values, top_k=5)
    result = synthesize(question=body.question, chunks=chunks, locale=body.locale)
    return QAResponse(
        session_id=session_id,
        answer=result["answer_en"],
        answer_hi=result["answer_hi"],
        citations=[
            CitationOut(index=c["index"], source=c["source"], url=c.get("url"))
            for c in result["citations"]
        ],
        safety_triggered=False,
    )
