"""One authorization policy for patient-specific operations. Deny by default."""
import uuid
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from .models import AuditEvent, Clinician, Grant, Patient, now


def is_minor(patient):
    today = date.today()
    dob = patient.birth_date
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)) < 18


def manages(patient, actor):
    return patient.account_id == actor or (
        patient.relationship == "child" and is_minor(patient)
        and patient.created_by == actor and patient.guardian_verified
    )


async def authorize(db, patient_id: uuid.UUID, actor: uuid.UUID, scope: str, *, write=False, manage=False):
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(404, "Patient record not available")
    if manages(patient, actor):
        return patient
    # No sharing until guardian verification; no silent extension after age 18.
    if patient.relationship == "child" and (not patient.guardian_verified or not is_minor(patient)):
        raise HTTPException(404, "Patient record not available")
    if manage:
        raise HTTPException(404, "Patient record not available")
    grants = (await db.scalars(select(Grant).where(
        Grant.patient_id == patient_id, Grant.recipient_id == actor,
        Grant.revoked_at.is_(None), Grant.expires_at > now(),
    ))).all()
    for grant in grants:
        if scope not in grant.scopes or (write and not grant.can_write):
            continue
        if grant.recipient_kind == "doctor":
            clinician = await db.get(Clinician, actor)
            if not clinician or not clinician.verified:
                continue
        return patient
    raise HTTPException(404, "Patient record not available")


def audit(db, patient_id, actor, action, resource_id=None):
    db.add(AuditEvent(patient_id=patient_id, actor_id=actor, action=action, resource_id=resource_id))
