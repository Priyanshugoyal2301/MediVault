"""
ai-service/routers/embed_report.py

Endpoints for embedding user report data for RAG retrieval.

POST /embed-report — embed a user's parsed report values for later retrieval.
DELETE /embeddings/{owner_id}/{report_id} — remove embeddings when a report is deleted.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from packages.shared_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


class EmbedReportRequest(BaseModel):
    report_id: str
    values: list[dict] = Field(
        ...,
        description="Parsed report values (test_name, value_numeric, unit, date_of_test, panel).",
    )


class EmbedReportResponse(BaseModel):
    report_id: str
    chunks_embedded: int


@router.post("/embed-report", response_model=EmbedReportResponse)
async def embed_report(
    body: EmbedReportRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
) -> EmbedReportResponse:
    """Embed a user's parsed report values for RAG retrieval.

    Called by health-service after a successful report parse.
    In the MVP, user report data is retrieved via keyword matching in the
    retriever (no separate vector embedding needed for report values).
    This endpoint is a placeholder for future vector-based user data search.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")

    logger.info(
        "Embed-report request for report=%s, values=%d",
        body.report_id,
        len(body.values),
    )

    # MVP: report values are retrieved via keyword matching in retriever.py.
    # No additional vector embedding needed for the user's own data.
    # This endpoint exists to satisfy the API contract and for future extension.
    return EmbedReportResponse(
        report_id=body.report_id,
        chunks_embedded=len(body.values),
    )


@router.delete("/{owner_id}/{report_id}")
async def delete_report_embeddings(
    owner_id: str,
    report_id: str,
    x_user_id: str = Header(..., alias="X-User-Id"),
) -> dict:
    """Remove embeddings for a deleted report.

    PRIVACY RULE: Only the owning user can delete their own embeddings.
    """
    if x_user_id != owner_id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's embeddings")

    logger.info(
        "Delete embeddings for owner=%s, report=%s",
        owner_id,
        report_id,
    )

    # MVP: No separate vector store for user data — deletion cascades at DB level.
    return {"status": "deleted", "owner_id": owner_id, "report_id": report_id}
