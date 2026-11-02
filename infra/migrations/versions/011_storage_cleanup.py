"""Transactional outbox for deleting stored originals after record deletion."""
import sqlalchemy as sa
from alembic import op
revision = "011"
down_revision = "010"
branch_labels = depends_on = None


def upgrade():
    op.create_table("storage_deletions",sa.Column("id",sa.Uuid(),primary_key=True),
        sa.Column("storage_path",sa.String(1000),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))


def downgrade():
    op.drop_table("storage_deletions")
