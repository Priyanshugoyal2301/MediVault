"""Patient identity, explicit consent, care records and access audit.

Existing reports remain in the account's personal vault until a profile is created.
No existing patient data is inferred or discarded.
"""
import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = depends_on = None


def identifier():
    return sa.Column("id", sa.Uuid(), primary_key=True)


def account(name, **kw):
    return sa.Column(name, sa.Uuid(), sa.ForeignKey("users.id"), **kw)


def patient():
    return sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False)


def timestamp(name, nullable=False):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def record_columns():
    return [identifier(), patient(), account("recorded_by", nullable=False),
            sa.Column("version", sa.Integer(), nullable=False), timestamp("created_at"), timestamp("updated_at")]


def upgrade():
    op.create_table("patients", identifier(), account("account_id", nullable=True, unique=True),
                    account("created_by", nullable=False), sa.Column("display_name", sa.String(120), nullable=False),
                    sa.Column("birth_date", sa.Date(), nullable=False), sa.Column("relationship", sa.String(30), nullable=False),
                    sa.Column("guardian_verified", sa.Boolean(), nullable=False),
                    sa.Column("allergy_status", sa.String(30), nullable=False), timestamp("created_at"))
    op.create_index("ix_patients_created_by", "patients", ["created_by"])
    op.create_table("clinicians", account("account_id", primary_key=True),
                    sa.Column("display_name", sa.String(120), nullable=False),
                    sa.Column("registration_number", sa.String(100), nullable=False),
                    sa.Column("council", sa.String(120), nullable=False), sa.Column("specialty", sa.String(120), nullable=False),
                    sa.Column("verified", sa.Boolean(), nullable=False), timestamp("created_at"))
    op.create_table("care_grants", identifier(), patient(), account("issued_by", nullable=False),
                    account("recipient_id", nullable=True), sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
                    sa.Column("recipient_kind", sa.String(20), nullable=False), sa.Column("label", sa.String(100), nullable=False),
                    sa.Column("scopes", sa.JSON(), nullable=False), sa.Column("can_write", sa.Boolean(), nullable=False),
                    timestamp("expires_at"), timestamp("revoked_at", True), timestamp("created_at"))
    op.create_index("ix_care_grants_recipient_id", "care_grants", ["recipient_id"])
    op.create_table("medications", *record_columns(), sa.Column("name", sa.String(200), nullable=False),
                    sa.Column("dose", sa.String(100), nullable=False), sa.Column("schedule", sa.String(200), nullable=False),
                    sa.Column("status", sa.String(30), nullable=False), sa.Column("source", sa.String(30), nullable=False),
                    sa.Column("start_date", sa.Date()), sa.Column("end_date", sa.Date()), sa.Column("notes", sa.Text(), nullable=False))
    op.create_table("allergies", *record_columns(), sa.Column("substance", sa.String(200), nullable=False),
                    sa.Column("reaction", sa.String(500), nullable=False), sa.Column("severity", sa.String(30), nullable=False),
                    sa.Column("status", sa.String(30), nullable=False), sa.Column("occurred_on", sa.Date()),
                    sa.Column("notes", sa.Text(), nullable=False))
    op.create_table("encounters", *record_columns(), sa.Column("occurred_on", sa.Date(), nullable=False),
                    sa.Column("facility", sa.String(200), nullable=False), sa.Column("clinician", sa.String(120), nullable=False),
                    sa.Column("reason", sa.String(500), nullable=False), sa.Column("notes", sa.Text(), nullable=False),
                    sa.Column("follow_up", sa.Date()))
    op.create_table("appointments", *record_columns(), timestamp("scheduled_at"),
                    sa.Column("facility", sa.String(200), nullable=False), sa.Column("clinician", sa.String(120), nullable=False),
                    sa.Column("purpose", sa.String(500), nullable=False), sa.Column("status", sa.String(30), nullable=False),
                    sa.Column("notes", sa.Text(), nullable=False))
    op.create_table("care_audit_events", identifier(), patient(), account("actor_id", nullable=False),
                    sa.Column("action", sa.String(60), nullable=False), sa.Column("resource_id", sa.Uuid()), timestamp("occurred_at"))
    for table in ("care_grants", "medications", "allergies", "encounters", "appointments", "care_audit_events"):
        op.create_index(f"ix_{table}_patient_id", table, ["patient_id"])
    op.add_column("reports", sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id", name="fk_reports_patient"), nullable=True))
    op.create_index("ix_reports_patient_id", "reports", ["patient_id"])


def downgrade():
    op.drop_index("ix_reports_patient_id", table_name="reports")
    op.drop_constraint("fk_reports_patient", "reports", type_="foreignkey")
    op.drop_column("reports", "patient_id")
    for table in ("care_audit_events", "appointments", "encounters", "allergies", "medications", "care_grants", "clinicians", "patients"):
        op.drop_table(table)
