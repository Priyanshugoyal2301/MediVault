"""Authorized document review -> source-linked medicines in one transaction."""
import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Report
from ..db.repositories.report_repository import ReportRepository
from ..db.session import get_db
from ..routers.reports import _get_owner_id
from .document_scope import DocumentScope, document_scope
from .models import Medication, PrescriptionReview, now
from .policy import audit, authorize
from .prescription_candidates import candidates_from_text
from .schemas import Input

router = APIRouter(prefix='/reports', tags=['prescription review'])
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[uuid.UUID, Depends(_get_owner_id)]
Scope = Annotated[DocumentScope, Depends(document_scope)]


class ReviewedMedicine(Input):
    name: str = Field(min_length=1, max_length=200)
    dose: str = Field(default='', max_length=100)
    schedule: str = Field(default='', max_length=200)
    status: Literal['unknown', 'taking', 'stopped'] = 'unknown'
    start_date: date | None = None
    end_date: date | None = None
    notes: str = Field(default='', max_length=3000)

    @model_validator(mode='after')
    def dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError('End date must be on or after start date')
        return self


class ApprovePrescription(Input):
    confirm_review: Literal[True]
    document_date: date | None = None
    medications: list[ReviewedMedicine] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def distinct_rows(self):
        keys = [(m.name.casefold(), m.dose.casefold(), m.schedule.casefold()) for m in self.medications]
        if len(keys) != len(set(keys)):
            raise ValueError('Remove duplicate medicine rows before saving')
        if self.document_date and self.document_date > date.today():
            raise ValueError('Prescription date cannot be in the future')
        return self


async def scoped_report(report_id, db, actor, scope, *, lock=False):
    query = select(Report).where(Report.id == report_id, ReportRepository(db, scope).predicate(actor))
    if lock:
        query = query.with_for_update()
    report = await db.scalar(query)
    if report is None:
        raise HTTPException(404, 'Document not available')
    if not scope.patient_id:
        raise HTTPException(409, 'Create a patient profile before reviewing medicines')
    return report


@router.get('/{report_id}/prescription-review')
async def review_draft(report_id: uuid.UUID, db: DB, actor: Actor, scope: Scope):
    report = await scoped_report(report_id, db, actor, scope)
    # Do not reveal medication approvals to a documents-only recipient.
    await authorize(db, scope.patient_id, actor, 'medications')
    review = await db.get(PrescriptionReview, report_id)
    return dict(report_id=str(report.id), document_date=report.document_date,
        candidates=candidates_from_text(report.extracted_text) if report.parsed_status == 'complete' else [],
        reviewed=review is not None,
        reviewed_at=review.reviewed_at if review else None,
        medication_ids=review.medication_ids if review else [],
        notice='Draft transcription only. Compare every field with the original. Missing medicines may need manual entry; current use is unknown until you record it.')


@router.post('/{report_id}/prescription-review', status_code=201)
async def approve_prescription(report_id: uuid.UUID, body: ApprovePrescription, db: DB, actor: Actor, scope: Scope):
    report = await scoped_report(report_id, db, actor, scope, lock=True)
    await authorize(db, scope.patient_id, actor, 'medications', write=True)
    if report.parsed_status != 'complete':
        raise HTTPException(409, 'Wait for extraction to complete before reviewing this document')
    if await db.get(PrescriptionReview, report_id):
        raise HTTPException(409, 'This document was already reviewed. Edit its saved medicines in Medications.')
    medication_ids = []
    for approved in body.medications:
        fields = approved.model_dump()
        fields['notes'] = ('Transcribed from a document and reviewed by the account holder or delegate; not clinical verification.\n' + fields['notes']).strip()
        row = Medication(**fields, patient_id=scope.patient_id, recorded_by=actor,
                         source='prescription', source_report_id=report_id)
        db.add(row)
        await db.flush()
        medication_ids.append(str(row.id))
        audit(db, scope.patient_id, actor, 'medications.created', row.id)
    if body.document_date:
        report.document_date = body.document_date
    review = PrescriptionReview(report_id=report_id, patient_id=scope.patient_id,
        reviewed_by=actor, reviewed_at=now(), medication_ids=medication_ids,
        approved_fields=jsonable_encoder(body.medications))
    db.add(review)
    audit(db, scope.patient_id, actor, 'prescription.reviewed', report_id)
    await db.flush()
    return dict(report_id=str(report_id), medication_ids=medication_ids,
                reviewed_at=review.reviewed_at, saved_count=len(medication_ids))
