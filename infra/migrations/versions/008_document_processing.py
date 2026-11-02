"""Document metadata and recoverable processing leases."""
import sqlalchemy as sa
from alembic import op
revision = "008"
down_revision = "007"
branch_labels = depends_on = None


def upgrade():
    op.add_column("reports", sa.Column("document_kind", sa.String(30), nullable=False, server_default="report"))
    op.add_column("reports", sa.Column("document_date", sa.Date()))
    op.add_column("reports", sa.Column("extracted_text", sa.Text()))
    op.add_column("reports", sa.Column("processing_started_at", sa.DateTime(timezone=True)))
    op.add_column("reports", sa.Column("processing_token", sa.Uuid()))
    op.create_index("ix_reports_processing_queue", "reports", ["parsed_status", "uploaded_at"])


def downgrade():
    op.drop_index("ix_reports_processing_queue", table_name="reports")
    for name in ("processing_token", "processing_started_at", "extracted_text", "document_date", "document_kind"):
        op.drop_column("reports", name)
