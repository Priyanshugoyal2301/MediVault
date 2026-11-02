"""Persist account authentication attempt limits across service restarts."""
import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("auth_failures", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("auth_window_started", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("users", "auth_window_started")
    op.drop_column("users", "auth_failures")
