"""Add canonical clinical concept fields to report_values and timeline_events

Revision ID: 005
Revises: 004
Create Date: 2026-10-08

CP-04: Longitudinal Evidence Schema & Database Migration

DESIGN RATIONALE (ADR-10):
  The atomic retrieval unit in MediVault's longitudinal IR system is the
  EVIDENCE OBSERVATION — a single dated laboratory measurement for a specific
  clinical concept belonging to a specific patient.

  Each observation must be independently addressable so that later retrieval
  and re-ranking layers can operate at evidence-observation granularity.

SCHEMA CHANGES:

  report_values (extended):
    + analyte_canonical    VARCHAR(200) NULL  — canonical analyte name after terminology mapping
    + concept_id           VARCHAR(100) NULL  — LOINC:code or CANONICAL:name
    + loinc_code           VARCHAR(20)  NULL  — LOINC code without prefix (e.g. "718-7")
    + date_type            VARCHAR(50)  NULL  — source of observation_date (collection/test/result/report)
    + date_confidence      VARCHAR(20)  NULL  — high/medium/low/fallback
    + source_provenance    VARCHAR(200) NULL  — human-readable data provenance string

  timeline_events (extended):
    + analyte_canonical    VARCHAR(200) NULL  — canonical analyte name
    + concept_id           VARCHAR(100) NULL  — LOINC:code or CANONICAL:name
    + loinc_code           VARCHAR(20)  NULL  — LOINC code
    + date_type            VARCHAR(50)  NULL  — source of observation_date
    + date_confidence      VARCHAR(20)  NULL  — confidence level of the observation date
    + source_provenance    VARCHAR(200) NULL  — provenance string
    + reference_range_low  NUMERIC(10,4) NULL — lower reference bound (duplicate from report_values for stand-alone evidence access)
    + reference_range_high NUMERIC(10,4) NULL — upper reference bound
    + flag                 VARCHAR(50)  NULL  — 'normal'/'high'/'low'/'abnormal'

EXPLICIT NON-CHANGES:
  - test_name is RETAINED. raw analyte name must be preserved for auditing.
  - No vector/embedding column. CP-06 (dense retrieval) is the correct owner.
  - No encounter_id. Not yet present in ingestion pipeline; deferring to CP-07.
  - No research-cohort patient identifiers. App/research separation maintained.
  - qa_sessions/qa_messages: DEFERRED (see ADR-10). Dormant tables, not touched.
  - knowledge_documents: DEFERRED. Populated by CP-06 KB ingestion.

INDEX STRATEGY (based on verified access patterns):
  report_values:
    + (owner_id, loinc_code)               — concept-scoped evidence retrieval
    + (owner_id, analyte_canonical, date_of_test) — longitudinal trajectory queries
  timeline_events:
    + (owner_id, loinc_code)               — concept-scoped timeline access
    + (owner_id, analyte_canonical, date_of_test) — chronological evidence selection

DUPLICATE POLICY (documented):
  Two timeline_events are distinct if they differ in ANY of:
    (owner_id, test_name, date_of_test, source_report_id)
  Legitimate repeated laboratory measurements (same test, same date, different
  report — e.g., repeat CBC on the same day) are preserved. The application
  does NOT silently deduplicate. Deduplication is a caller decision, not a
  schema constraint.

NORMALIZATION:
  test_name   = raw analyte text (ALWAYS preserved)
  analyte_canonical = normalized form (may be None if unmapped)
  loinc_code  = LOINC identifier string (may be None if unmapped)
  concept_id  = LOINC:code | CANONICAL:name | None
  Both raw and canonical survive persistence so normalization remains auditable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # report_values — add canonical clinical concept columns
    # ------------------------------------------------------------------
    op.add_column(
        "report_values",
        sa.Column("analyte_canonical", sa.String(200), nullable=True),
    )
    op.add_column(
        "report_values",
        sa.Column("concept_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "report_values",
        sa.Column("loinc_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "report_values",
        sa.Column("date_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "report_values",
        sa.Column("date_confidence", sa.String(20), nullable=True),
    )
    op.add_column(
        "report_values",
        sa.Column("source_provenance", sa.String(200), nullable=True),
    )

    # Compound indexes for evidence retrieval access patterns on report_values
    op.create_index(
        "report_values_owner_loinc_idx",
        "report_values",
        ["owner_id", "loinc_code"],
    )
    op.create_index(
        "report_values_owner_canonical_date_idx",
        "report_values",
        ["owner_id", "analyte_canonical", "date_of_test"],
    )

    # ------------------------------------------------------------------
    # timeline_events — add canonical clinical concept + measurement columns
    # ------------------------------------------------------------------
    op.add_column(
        "timeline_events",
        sa.Column("analyte_canonical", sa.String(200), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("concept_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("loinc_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("date_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("date_confidence", sa.String(20), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("source_provenance", sa.String(200), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("reference_range_low", sa.Numeric(precision=10, scale=4), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("reference_range_high", sa.Numeric(precision=10, scale=4), nullable=True),
    )
    op.add_column(
        "timeline_events",
        sa.Column("flag", sa.String(50), nullable=True),
    )

    # Compound indexes for longitudinal trajectory access patterns
    op.create_index(
        "timeline_events_owner_loinc_idx",
        "timeline_events",
        ["owner_id", "loinc_code"],
    )
    op.create_index(
        "timeline_events_owner_canonical_date_idx",
        "timeline_events",
        ["owner_id", "analyte_canonical", "date_of_test"],
    )


def downgrade() -> None:
    # timeline_events — remove indexes then columns
    op.drop_index("timeline_events_owner_canonical_date_idx", table_name="timeline_events")
    op.drop_index("timeline_events_owner_loinc_idx", table_name="timeline_events")
    op.drop_column("timeline_events", "flag")
    op.drop_column("timeline_events", "reference_range_high")
    op.drop_column("timeline_events", "reference_range_low")
    op.drop_column("timeline_events", "source_provenance")
    op.drop_column("timeline_events", "date_confidence")
    op.drop_column("timeline_events", "date_type")
    op.drop_column("timeline_events", "loinc_code")
    op.drop_column("timeline_events", "concept_id")
    op.drop_column("timeline_events", "analyte_canonical")

    # report_values — remove indexes then columns
    op.drop_index("report_values_owner_canonical_date_idx", table_name="report_values")
    op.drop_index("report_values_owner_loinc_idx", table_name="report_values")
    op.drop_column("report_values", "source_provenance")
    op.drop_column("report_values", "date_confidence")
    op.drop_column("report_values", "date_type")
    op.drop_column("report_values", "loinc_code")
    op.drop_column("report_values", "concept_id")
    op.drop_column("report_values", "analyte_canonical")
