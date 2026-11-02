"""Atomic, attributed prescription approval with duplicate-submission protection."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '015'
down_revision = '014'
branch_labels = depends_on = None


def upgrade():
    op.create_table('prescription_reviews',
        sa.Column('report_id', UUID(as_uuid=True), sa.ForeignKey('reports.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('patient_id', UUID(as_uuid=True), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('reviewed_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('medication_ids', sa.JSON(), nullable=False),
        sa.Column('approved_fields', sa.JSON(), nullable=False))
    op.create_index('ix_prescription_reviews_patient_id', 'prescription_reviews', ['patient_id'])


def downgrade():
    op.drop_table('prescription_reviews')
