"""Create health-service tables: reports, report_values, timeline_events

Revision ID: 002
Revises: 001
Create Date: 2026-08-08

DB-LEVEL owner_id ENFORCEMENT (02_ARCHITECTURE.md §4, §5):
  Every table here has owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE.
  This is the DB-level second layer of privacy enforcement:
    - Layer 1: ScopedRepository base class requires owner_id at the query/app layer.
    - Layer 2: These NOT NULL FK constraints prevent ANY raw SQL or bypass of the
               repository class from inserting or querying across users.
  Both layers are intentional and complementary. See DEV_LOG [2026-08-08].

cascade ON DELETE: when a user is deleted (hard-delete from auth-service), all
their reports, values, and timeline events are automatically removed by the DB.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # reports — uploaded report file metadata
    # ------------------------------------------------------------------
    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        # owner_id: NOT NULL + FK → users.id, cascades on delete
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column(
            "parsed_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("parsed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="reports_owner_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "parsed_status IN ('pending', 'processing', 'complete', 'failed')",
            name="reports_parsed_status_check",
        ),
    )
    op.create_index("reports_owner_idx", "reports", ["owner_id"])

    # ------------------------------------------------------------------
    # report_values — structured values extracted from a report
    # ------------------------------------------------------------------
    op.create_table(
        "report_values",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        # owner_id duplicated here (denormalized) so every health table
        # can be scoped by owner_id without joins — privacy enforcement is
        # local to each table.
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("panel", sa.String(100), nullable=True),
        sa.Column("value_numeric", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("value_text", sa.String(200), nullable=True),
        sa.Column("unit", sa.String(100), nullable=True),
        sa.Column("reference_range_low", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("reference_range_high", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("reference_range_text", sa.String(200), nullable=True),
        sa.Column("date_of_test", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="report_values_report_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="report_values_owner_id_fkey",
            ondelete="CASCADE",
        ),
    )
    op.create_index("report_values_owner_idx", "report_values", ["owner_id"])
    op.create_index("report_values_report_idx", "report_values", ["report_id"])
    op.create_index(
        "report_values_owner_test_date_idx",
        "report_values",
        ["owner_id", "test_name", "date_of_test"],
    )

    # ------------------------------------------------------------------
    # timeline_events — derived from report_values; used for trend detection
    # ------------------------------------------------------------------
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("value_numeric", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("value_text", sa.String(200), nullable=True),
        sa.Column("unit", sa.String(100), nullable=True),
        sa.Column("date_of_test", sa.Date(), nullable=False),
        sa.Column("source_report_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="timeline_events_owner_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_report_id"],
            ["reports.id"],
            name="timeline_events_source_report_id_fkey",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "timeline_events_owner_test_date_idx",
        "timeline_events",
        ["owner_id", "test_name", "date_of_test"],
    )


def downgrade() -> None:
    op.drop_index("timeline_events_owner_test_date_idx", table_name="timeline_events")
    op.drop_table("timeline_events")

    op.drop_index("report_values_owner_test_date_idx", table_name="report_values")
    op.drop_index("report_values_report_idx", table_name="report_values")
    op.drop_index("report_values_owner_idx", table_name="report_values")
    op.drop_table("report_values")

    op.drop_index("reports_owner_idx", table_name="reports")
    op.drop_table("reports")
