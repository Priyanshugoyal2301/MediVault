"""Source-linked medications, retained corrections and operator decisions."""
import sqlalchemy as sa
from alembic import op
revision = "009"
down_revision = "008"
branch_labels = depends_on = None


def upgrade():
    op.add_column("medications", sa.Column("source_report_id",sa.Uuid(),sa.ForeignKey("reports.id",ondelete="SET NULL",name="fk_medication_source")))
    op.create_table("care_record_revisions",sa.Column("id",sa.Uuid(),primary_key=True),
        sa.Column("patient_id",sa.Uuid(),sa.ForeignKey("patients.id"),nullable=False),
        sa.Column("resource_id",sa.Uuid(),nullable=False),sa.Column("resource_type",sa.String(30),nullable=False),
        sa.Column("actor_id",sa.Uuid(),sa.ForeignKey("users.id"),nullable=False),sa.Column("snapshot",sa.JSON(),nullable=False),
        sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_care_record_revisions_patient_id","care_record_revisions",["patient_id"])
    op.create_index("ix_care_record_revisions_resource_id","care_record_revisions",["resource_id"])
    op.create_table("verification_decisions",sa.Column("id",sa.Uuid(),primary_key=True),
        sa.Column("subject_id",sa.Uuid(),nullable=False),sa.Column("subject_kind",sa.String(30),nullable=False),
        sa.Column("operator",sa.String(120),nullable=False),sa.Column("evidence_reference",sa.String(200),nullable=False),
        sa.Column("approved",sa.Boolean(),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_verification_decisions_subject_id","verification_decisions",["subject_id"])


def downgrade():
    op.drop_table("verification_decisions")
    op.drop_table("care_record_revisions")
    op.drop_constraint("fk_medication_source","medications",type_="foreignkey")
    op.drop_column("medications","source_report_id")
