"""Care domain. Account identity and patient identity are deliberately separate."""
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.models import Base


def now():
    return datetime.now(UTC)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    birth_date: Mapped[date] = mapped_column(Date)
    relationship: Mapped[str] = mapped_column(String(30), default="self")
    guardian_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    allergy_status: Mapped[str] = mapped_column(String(30), default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Clinician(Base):
    __tablename__ = "clinicians"
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    registration_number: Mapped[str] = mapped_column(String(100))
    council: Mapped[str] = mapped_column(String(120))
    specialty: Mapped[str] = mapped_column(String(120))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Grant(Base):
    __tablename__ = "care_grants"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    issued_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    recipient_kind: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(100))
    scopes: Mapped[list] = mapped_column(JSON)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RecordMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Medication(RecordMixin, Base):
    __tablename__ = "medications"
    name: Mapped[str] = mapped_column(String(200))
    dose: Mapped[str] = mapped_column(String(100))
    schedule: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(30))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    source_report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reports.id", ondelete="SET NULL"))


class Allergy(RecordMixin, Base):
    __tablename__ = "allergies"
    substance: Mapped[str] = mapped_column(String(200))
    reaction: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    occurred_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")


class PrescriptionReview(Base):
    __tablename__ = 'prescription_reviews'
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('reports.id', ondelete='CASCADE'), primary_key=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('patients.id'), index=True)
    reviewed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    medication_ids: Mapped[list] = mapped_column(JSON)
    approved_fields: Mapped[list] = mapped_column(JSON)


class Encounter(RecordMixin, Base):
    __tablename__ = "encounters"
    occurred_on: Mapped[date] = mapped_column(Date)
    facility: Mapped[str] = mapped_column(String(200))
    clinician: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str] = mapped_column(Text, default="")
    follow_up: Mapped[date | None] = mapped_column(Date)


class Appointment(RecordMixin, Base):
    __tablename__ = "appointments"
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    facility: Mapped[str] = mapped_column(String(200))
    clinician: Mapped[str] = mapped_column(String(120))
    purpose: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="planned")
    notes: Mapped[str] = mapped_column(Text, default="")


class AuditEvent(Base):
    __tablename__ = "care_audit_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[uuid.UUID | None] = mapped_column()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RecordRevision(Base):
    __tablename__ = "care_record_revisions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(index=True)
    resource_type: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    snapshot: Mapped[dict] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VerificationDecision(Base):
    __tablename__ = "verification_decisions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)
    subject_kind: Mapped[str] = mapped_column(String(30))
    operator: Mapped[str] = mapped_column(String(120))
    evidence_reference: Mapped[str] = mapped_column(String(200))
    approved: Mapped[bool] = mapped_column(Boolean)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Referral(RecordMixin, Base):
    __tablename__ = "referrals"
    facility: Mapped[str] = mapped_column(String(200))
    clinician: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(String(500))
    issued_on: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text, default="")


class Claim(RecordMixin, Base):
    __tablename__ = "claims"
    facility: Mapped[str] = mapped_column(String(200))
    scheme: Mapped[str] = mapped_column(String(120))
    reference: Mapped[str] = mapped_column(String(120))
    amount_rupees: Mapped[str] = mapped_column(String(20))
    submitted_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text, default="")


class BenefitCard(RecordMixin, Base):
    __tablename__ = "benefit_cards"
    scheme: Mapped[str] = mapped_column(String(120))
    member_reference: Mapped[str] = mapped_column(String(120))
    valid_until: Mapped[date | None] = mapped_column(Date)
    contact: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")


class Vaccination(RecordMixin, Base):
    __tablename__ = "vaccinations"
    name: Mapped[str] = mapped_column(String(200))
    dose: Mapped[str] = mapped_column(String(100))
    administered_on: Mapped[date] = mapped_column(Date)
    facility: Mapped[str] = mapped_column(String(200))
    next_due: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")


class StorageDeletion(Base):
    __tablename__ = "storage_deletions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    storage_path: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
