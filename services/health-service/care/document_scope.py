"""Validated patient scope reused by reports, lab history and explanations."""
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import Report
from ..db.session import get_db
from .models import Patient
from .policy import audit, authorize, is_minor


@dataclass(frozen=True)
class DocumentScope:
    patient_id: UUID | None
    personal_owner: UUID | None
    pediatric: bool = False

    def predicate(self):
        conditions = []
        if self.patient_id:
            conditions.append(Report.patient_id == self.patient_id)
        if self.personal_owner:
            conditions.append(and_(Report.patient_id.is_(None), Report.owner_id == self.personal_owner))
        return or_(*conditions)


async def document_scope(request: Request, db: Annotated[AsyncSession, Depends(get_db)],
                         x_user_id: Annotated[str | None, Header()] = None,
                         patient_id: UUID | None = None):
    try:
        actor = UUID(x_user_id or "")
    except ValueError:
        raise HTTPException(401, "Invalid identity") from None
    if patient_id is None:
        patient = await db.scalar(select(Patient).where(Patient.account_id == actor))
        if patient is None:
            return DocumentScope(None, actor)
        patient_id = patient.id
    patient = await authorize(db, patient_id, actor, "documents", write=request.method not in ("GET", "HEAD") and not request.url.path.startswith("/qa"))
    audit(db, patient_id, actor, "documents." + request.method.lower())
    return DocumentScope(patient_id, patient.account_id, is_minor(patient))
