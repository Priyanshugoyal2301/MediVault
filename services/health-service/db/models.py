"""
health-service/db/models.py

SQLAlchemy models for reports, report_values, timeline_events.
Schema defined in infra/migrations/versions/002_create_health_tables.py,
extended in infra/migrations/versions/005_longitudinal_evidence_schema.py.

All tables have owner_id NOT NULL — see migration 002 for DB-level enforcement.

CP-04 EVIDENCE MODEL:
  The atomic retrieval unit is the EVIDENCE OBSERVATION — a single dated
  laboratory measurement for a specific clinical concept owned by a specific
  patient. Every observation is independently addressable via its UUID.

  Normalization is auditable:
    test_name           = raw analyte text (ALWAYS retained)
    analyte_canonical   = normalized canonical form (may be None if unmapped)
    loinc_code          = LOINC identifier (may be None if unmapped)
    concept_id          = LOINC:code | CANONICAL:name | None

  Vectors are NOT stored here. Vector persistence belongs to CP-06.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """Stub for auth-owned ``users`` table — FK resolution only (not written here)."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "parsed_status IN ('pending', 'processing', 'complete', 'failed')",
            name="reports_parsed_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)
    document_kind: Mapped[str] = mapped_column(String(30), default="report")
    document_date: Mapped[date | None] = mapped_column(Date)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    processing_note: Mapped[str | None] = mapped_column(String(500))
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    stored_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    parsed_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportValue(Base):
    """
    A single extracted laboratory measurement from an uploaded report.

    EVIDENCE MODEL (CP-04):
      - test_name: ALWAYS retained (raw analyte text from the source document).
      - analyte_canonical: Normalized canonical analyte after terminology mapping.
      - concept_id: Structured concept reference (e.g. 'LOINC:718-7').
      - loinc_code: Plain LOINC code string (e.g. '718-7'), without prefix.
      - date_type: Classification of the date source (collection/test/result/report).
      - date_confidence: high/medium/low/fallback.
      - source_provenance: Human-readable data provenance string.

    Non-changes: no embedding column (belongs to CP-06).
    """
    __tablename__ = "report_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Raw identity — ALWAYS retained
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    panel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Measurement
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_range_low: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    reference_range_high: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    reference_range_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Temporal
    date_of_test: Mapped[date | None] = mapped_column(Date(), nullable=True)
    date_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Canonical clinical concept (CP-04)
    analyte_canonical: Mapped[str | None] = mapped_column(String(200), nullable=True)
    concept_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    loinc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_provenance: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Generated explanations
    explanation_en: Mapped[str | None] = mapped_column(Text(), nullable=True)
    explanation_hi: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TimelineEvent(Base):
    """
    A single longitudinal evidence observation in a patient's health timeline.

    This is the ATOMIC RETRIEVAL UNIT for MediVault's longitudinal IR system.

    EVIDENCE MODEL (CP-04):
      - test_name: ALWAYS retained (raw analyte text).
      - analyte_canonical: Normalized form. Used for concept-scoped trajectory queries.
      - concept_id: Structured reference e.g. 'LOINC:718-7'.
      - loinc_code: Plain LOINC code string.
      - reference_range_low/high: Stored here so each event is a stand-alone
        evidence unit. The retrieval layer does not need to join to report_values.
      - flag: Abnormality indicator at measurement time ('normal', 'high', 'low', 'abnormal').
      - date_type / date_confidence: Provenance of the observation_date (CP-02 semantics).
      - source_provenance: Human-readable provenance string.

    DUPLICATE POLICY:
      Two events are distinct if (owner_id, test_name, date_of_test, source_report_id)
      differ in any dimension. Repeated legitimate measurements are preserved.

    NON-CHANGES: no embedding column (CP-06).
    """
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Raw identity — ALWAYS retained
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Measurement
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_range_low: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    reference_range_high: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    flag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Temporal
    date_of_test: Mapped[date] = mapped_column(Date(), nullable=False)
    date_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Canonical clinical concept (CP-04)
    analyte_canonical: Mapped[str | None] = mapped_column(String(200), nullable=True)
    concept_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    loinc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_provenance: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
