from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PatientIn(Input):
    display_name: str = Field(min_length=1, max_length=120)
    birth_date: date
    relationship: Literal["self", "child"] = "self"

    @model_validator(mode="after")
    def valid_age(self):
        today = date.today()
        age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        if self.birth_date > today or age > 120:
            raise ValueError("Enter a valid date of birth")
        if self.relationship == "self" and age < 18:
            raise ValueError("An adult account is required; a guardian can add a child")
        if self.relationship == "child" and age >= 18:
            raise ValueError("Adults must create their own account and share access")
        return self


class ClinicianIn(Input):
    display_name: str = Field(min_length=1, max_length=120)
    registration_number: str = Field(min_length=1, max_length=100)
    council: str = Field(min_length=1, max_length=120)
    specialty: str = Field(min_length=1, max_length=120)


Scope = Literal["documents", "medications", "allergies", "encounters", "appointments", "referrals", "claims", "benefits", "vaccinations"]
SCOPES = ("documents", "medications", "allergies", "encounters", "appointments", "referrals", "claims", "benefits", "vaccinations")


class GrantIn(Input):
    recipient_kind: Literal["caregiver", "doctor"]
    label: str = Field(min_length=1, max_length=100)
    scopes: list[Scope] = Field(min_length=1, max_length=9)
    can_write: bool = False
    expires_at: datetime

    @model_validator(mode="after")
    def valid_expiry(self):
        if self.expires_at.tzinfo is None:
            raise ValueError("Expiry must include a timezone")
        seconds = (self.expires_at - datetime.now(UTC)).total_seconds()
        if not 0 < seconds <= 90 * 86400:
            raise ValueError("Expiry must be in the next 90 days")
        self.scopes = sorted(set(self.scopes))
        return self


class AcceptGrant(Input):
    token: str = Field(min_length=40, max_length=100)


class MedicationIn(Input):
    name: str = Field(min_length=1, max_length=200)
    dose: str = Field(default="", max_length=100)
    schedule: str = Field(default="", max_length=200)
    status: Literal["taking", "stopped", "unknown"] = "unknown"
    source: Literal["patient_reported", "prescription"] = "patient_reported"
    start_date: date | None = None
    end_date: date | None = None
    notes: str = Field(default="", max_length=4000)
    source_report_id: UUID | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class AllergyIn(Input):
    substance: str = Field(min_length=1, max_length=200)
    reaction: str = Field(min_length=1, max_length=500)
    severity: Literal["unknown", "mild", "moderate", "severe"] = "unknown"
    status: Literal["reported", "confirmed", "refuted"] = "reported"
    occurred_on: date | None = None
    notes: str = Field(default="", max_length=4000)


class EncounterIn(Input):
    occurred_on: date
    facility: str = Field(min_length=1, max_length=200)
    clinician: str = Field(default="", max_length=120)
    reason: str = Field(min_length=1, max_length=500)
    notes: str = Field(default="", max_length=4000)
    follow_up: date | None = None


class AppointmentIn(Input):
    scheduled_at: datetime
    facility: str = Field(min_length=1, max_length=200)
    clinician: str = Field(default="", max_length=120)
    purpose: str = Field(min_length=1, max_length=500)
    status: Literal["planned", "confirmed", "completed", "cancelled"] = "planned"
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def timezone(self):
        if self.scheduled_at.tzinfo is None:
            raise ValueError("Appointment time must include a timezone")
        return self


class ReferralIn(Input):
    facility: str = Field(min_length=1, max_length=200)
    clinician: str = Field(default="", max_length=120)
    reason: str = Field(min_length=1, max_length=500)
    issued_on: date
    valid_until: date | None = None
    status: Literal["issued", "scheduled", "completed", "cancelled"] = "issued"
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def dates(self):
        if self.valid_until and self.valid_until < self.issued_on:
            raise ValueError("Validity date must follow the issue date")
        return self


class ClaimIn(Input):
    facility: str = Field(min_length=1, max_length=200)
    scheme: str = Field(min_length=1, max_length=120)
    reference: str = Field(default="", max_length=120)
    amount_rupees: str = Field(pattern=r"^\d{1,9}(\.\d{1,2})?$")
    submitted_on: date | None = None
    status: Literal["preparing", "submitted", "information_requested", "approved", "paid", "rejected"] = "preparing"
    notes: str = Field(default="", max_length=4000)


class BenefitIn(Input):
    scheme: str = Field(min_length=1, max_length=120)
    member_reference: str = Field(default="", max_length=120)
    valid_until: date | None = None
    contact: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=4000)


class VaccinationIn(Input):
    name: str = Field(min_length=1, max_length=200)
    dose: str = Field(default="", max_length=100)
    administered_on: date
    facility: str = Field(default="", max_length=200)
    next_due: date | None = None
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def dates(self):
        if self.administered_on > date.today():
            raise ValueError("Administration date cannot be in the future")
        if self.next_due and self.next_due < self.administered_on:
            raise ValueError("Next due date must follow administration")
        return self
