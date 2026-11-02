"""Patient, consent and care APIs. Every record operation passes the same policy."""
import hashlib
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db
from ..routers.timeline import _get_owner_id
from .models import Allergy, Appointment, AuditEvent, Clinician, Encounter, Grant, Medication, Patient, RecordRevision, now
from .models import Referral, Claim, BenefitCard, Vaccination
from .schemas import SCOPES, ReferralIn, ClaimIn, BenefitIn, VaccinationIn
from .policy import audit, authorize, manages
from .schemas import AcceptGrant, AllergyIn, AppointmentIn, ClinicianIn, EncounterIn, GrantIn, MedicationIn, PatientIn

router = APIRouter(prefix="/care", tags=["care"])
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[uuid.UUID, Depends(_get_owner_id)]


def serialize(record, *, omit=()):
    return jsonable_encoder({c.name: getattr(record, c.name) for c in record.__table__.columns if c.name not in omit})


@router.get("/patients")
async def patients(db: DB, actor: Actor):
    grant_ids = select(Grant.patient_id).where(Grant.recipient_id == actor, Grant.revoked_at.is_(None), Grant.expires_at > now())
    rows = (await db.scalars(select(Patient).where(or_(
        Patient.account_id == actor, Patient.created_by == actor, Patient.id.in_(grant_ids)
    )).order_by(Patient.created_at))).all()
    result = []
    for row in rows:
        own = manages(row, actor)
        scopes, writable = [], []
        for scope in SCOPES:
            try:
                await authorize(db, row.id, actor, scope)
                scopes.append(scope)
                await authorize(db, row.id, actor, scope, write=True)
                writable.append(scope)
            except HTTPException:
                pass
        # Creators see pending child registration, never a former adult's health.
        if scopes or row.created_by == actor:
            result.append({**serialize(row), "can_manage": own, "scopes": scopes, "writable_scopes": writable})
    return result


@router.post("/patients", status_code=201)
async def create_patient(body: PatientIn, db: DB, actor: Actor):
    row = Patient(**body.model_dump(), created_by=actor,
                  account_id=actor if body.relationship == "self" else None)
    db.add(row)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Your personal patient profile already exists") from None
    audit(db, row.id, actor, "patient.created", row.id)
    return serialize(row)


@router.get("/clinician")
async def clinician_profile(db: DB, actor: Actor):
    row = await db.get(Clinician, actor)
    return serialize(row) if row else None


@router.post("/clinician", status_code=201)
async def register_clinician(body: ClinicianIn, db: DB, actor: Actor):
    if await db.get(Clinician, actor):
        raise HTTPException(409, "A clinician application already exists")
    row = Clinician(account_id=actor, **body.model_dump(), verified=False)
    db.add(row)
    await db.flush()
    return serialize(row)


@router.get("/patients/{patient_id}/grants")
async def list_grants(patient_id: uuid.UUID, db: DB, actor: Actor):
    await authorize(db, patient_id, actor, "", manage=True)
    rows = (await db.scalars(select(Grant).where(Grant.patient_id == patient_id).order_by(Grant.created_at.desc()))).all()
    return [serialize(g, omit=("token_hash",)) for g in rows]


@router.post("/patients/{patient_id}/grants", status_code=201)
async def create_grant(patient_id: uuid.UUID, body: GrantIn, db: DB, actor: Actor):
    await authorize(db, patient_id, actor, "", manage=True)
    token = secrets.token_urlsafe(32)
    row = Grant(patient_id=patient_id, issued_by=actor,
                token_hash=hashlib.sha256(token.encode()).hexdigest(), **body.model_dump())
    db.add(row)
    await db.flush()
    audit(db, patient_id, actor, "consent.issued", row.id)
    return {**serialize(row, omit=("token_hash",)), "token": token}


@router.post("/grants/accept")
async def accept_grant(body: AcceptGrant, db: DB, actor: Actor):
    row = await db.scalar(select(Grant).where(
        Grant.token_hash == hashlib.sha256(body.token.encode()).hexdigest(),
        Grant.recipient_id.is_(None), Grant.revoked_at.is_(None), Grant.expires_at > now()
    ).with_for_update())
    if row is None or row.issued_by == actor:
        raise HTTPException(404, "Invitation is unavailable or expired")
    await authorize(db, row.patient_id, row.issued_by, "", manage=True)
    if row.recipient_kind == "doctor":
        doctor = await db.get(Clinician, actor)
        if not doctor or not doctor.verified:
            raise HTTPException(403, "Clinician verification is required")
    row.recipient_id = actor
    audit(db, row.patient_id, actor, "consent.accepted", row.id)
    return {"patient_id": str(row.patient_id)}


@router.delete("/patients/{patient_id}/grants/{grant_id}", status_code=204)
async def revoke_grant(patient_id: uuid.UUID, grant_id: uuid.UUID, db: DB, actor: Actor):
    await authorize(db, patient_id, actor, "", manage=True)
    row = await db.scalar(select(Grant).where(Grant.id == grant_id, Grant.patient_id == patient_id).with_for_update())
    if not row:
        raise HTTPException(404, "Permission not found")
    row.revoked_at = now()
    audit(db, patient_id, actor, "consent.revoked", row.id)


@router.get("/patients/{patient_id}/audit")
async def activity(patient_id: uuid.UUID, db: DB, actor: Actor, offset: int = Query(0, ge=0)):
    await authorize(db, patient_id, actor, "", manage=True)
    rows = (await db.scalars(select(AuditEvent).where(AuditEvent.patient_id == patient_id)
                            .order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(100))).all()
    return [serialize(r) for r in rows]


@router.delete("/patients/{patient_id}/recipients/{recipient_id}/grants")
async def revoke_recipient_grants(patient_id: uuid.UUID, recipient_id: uuid.UUID, db: DB, actor: Actor):
    """Revoke all accepted grants for one recipient on this patient's record."""
    await authorize(db, patient_id, actor, "", manage=True)
    revoked_ids = (await db.scalars(
        update(Grant).where(
            Grant.patient_id == patient_id,
            Grant.recipient_id == recipient_id,
            Grant.revoked_at.is_(None),
        ).values(revoked_at=now()).returning(Grant.id)
    )).all()
    for grant_id in revoked_ids:
        audit(db, patient_id, actor, "consent.revoked", grant_id)
    return {"revoked_count": len(revoked_ids)}


@router.get("/patients/{patient_id}/summary")
async def consultation_summary(patient_id: uuid.UUID, db: DB, actor: Actor):
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(404, "Patient record not available")
    result = {"generated_at": now().isoformat(), "sections": {}, "unshared_sections": []}
    permitted = False
    for scope, model in [("medications", Medication), ("allergies", Allergy), ("encounters", Encounter), ("appointments", Appointment)]:
        try:
            await authorize(db, patient_id, actor, scope)
        except HTTPException:
            result["unshared_sections"].append(scope)
            continue
        permitted = True
        rows = (await db.scalars(select(model).where(model.patient_id == patient_id).order_by(model.created_at.desc()))).all()
        result["sections"][scope] = [serialize(row) for row in rows]
    if not permitted:
        raise HTTPException(404, "Patient record not available")
    result["patient"] = {"display_name": patient.display_name, "birth_date": patient.birth_date.isoformat()}
    result["allergy_status"] = "See reaction history" if result["sections"].get("allergies") else "Unknown or not shared; never assume no allergies"
    audit(db, patient_id, actor, "summary.read")
    return result


async def validate_clinical_claim(db, actor, body, patient_id):
    if isinstance(body, MedicationIn) and body.source_report_id:
        from .document_scope import DocumentScope
        from ..db.repositories.report_repository import ReportRepository
        patient = await authorize(db, patient_id, actor, "documents")
        report = await ReportRepository(db, DocumentScope(patient_id, patient.account_id)).get_by_id(body.source_report_id, actor)
        if not report:
            raise HTTPException(404, "Source document not available")
    if isinstance(body, AllergyIn) and body.status in ("confirmed", "refuted"):
        clinician = await db.get(Clinician, actor)
        if not clinician or not clinician.verified:
            raise HTTPException(403, "Only a verified clinician can confirm or refute an allergy")


def register_records(scope, model, schema):
    """Identical consent, concurrency and audit rules across typed care resources."""
    async def listing(patient_id: uuid.UUID, db: DB, actor: Actor, offset: int = Query(0, ge=0)):
        await authorize(db, patient_id, actor, scope)
        rows = (await db.scalars(select(model).where(model.patient_id == patient_id)
                                .order_by(model.created_at.desc(), model.id).offset(offset).limit(100))).all()
        audit(db, patient_id, actor, f"{scope}.read")
        return [serialize(row) for row in rows]

    async def create(patient_id: uuid.UUID, body, db: DB, actor: Actor):
        await authorize(db, patient_id, actor, scope, write=True)
        await validate_clinical_claim(db, actor, body, patient_id)
        row = model(patient_id=patient_id, recorded_by=actor, **body.model_dump())
        db.add(row)
        await db.flush()
        audit(db, patient_id, actor, f"{scope}.created", row.id)
        return serialize(row)

    async def history(patient_id: uuid.UUID, record_id: uuid.UUID, db: DB, actor: Actor):
        await authorize(db, patient_id, actor, scope)
        current = await db.scalar(select(model).where(model.id == record_id, model.patient_id == patient_id))
        if current is None:
            raise HTTPException(404, "Record not found")
        rows = (await db.scalars(select(RecordRevision).where(RecordRevision.patient_id == patient_id,
            RecordRevision.resource_id == record_id, RecordRevision.resource_type == scope).order_by(RecordRevision.occurred_at))).all()
        audit(db, patient_id, actor, f"{scope}.history.read", record_id)
        return {"current": serialize(current), "previous": [serialize(row) for row in rows]}

    async def replace(patient_id: uuid.UUID, record_id: uuid.UUID, body, db: DB, actor: Actor,
                      if_match: Annotated[int, Header(ge=1)]):
        await authorize(db, patient_id, actor, scope, write=True)
        await validate_clinical_claim(db, actor, body, patient_id)
        row = await db.scalar(select(model).where(model.id == record_id, model.patient_id == patient_id).with_for_update())
        if not row:
            raise HTTPException(404, "Record not found")
        if row.version != if_match:
            raise HTTPException(409, "This record changed. Reload before saving again.")
        db.add(RecordRevision(patient_id=patient_id, resource_id=row.id, resource_type=scope,
                              actor_id=actor, snapshot=serialize(row)))
        for key, value in body.model_dump().items():
            setattr(row, key, value)
        row.version += 1
        row.updated_at = now()
        audit(db, patient_id, actor, f"{scope}.updated", row.id)
        await db.flush()
        return serialize(row)

    create.__annotations__["body"] = schema
    replace.__annotations__["body"] = schema
    path = f"/patients/{{patient_id}}/{scope}"
    router.add_api_route(path, listing, methods=["GET"], name=f"list_{scope}")
    router.add_api_route(path, create, methods=["POST"], status_code=201, name=f"create_{scope}")
    router.add_api_route(path + "/{record_id}", replace, methods=["PUT"], name=f"update_{scope}")
    router.add_api_route(path + "/{record_id}/history", history, methods=["GET"], name=f"history_{scope}")


for args in [("medications", Medication, MedicationIn), ("allergies", Allergy, AllergyIn),
             ("encounters", Encounter, EncounterIn), ("appointments", Appointment, AppointmentIn),
             ("referrals", Referral, ReferralIn), ("claims", Claim, ClaimIn),
             ("benefits", BenefitCard, BenefitIn), ("vaccinations", Vaccination, VaccinationIn)]:
    register_records(*args)
