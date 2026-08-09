"""Create users table (auth-service)

Revision ID: 001
Revises: (initial)
Create Date: 2026-08-08

PRIVACY: users table is the identity anchor for owner_id FKs in subsequent
migrations. Soft-delete (deleted_at) is supported; hard-delete via the API
cascades to all owned health data via DB-level ON DELETE CASCADE FKs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (needed for knowledge_documents in a later migration)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        # locale_preference constrained to the two MVP-supported locales.
        # See DEV_LOG [2026-08-08] for the Hindi decision.
        sa.Column(
            "locale_preference",
            sa.String(10),
            nullable=False,
            server_default="en-IN",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.CheckConstraint(
            "locale_preference IN ('en-IN', 'hi-IN')",
            name="users_locale_preference_check",
        ),
    )
    op.create_index("users_email_idx", "users", ["email"])


def downgrade() -> None:
    op.drop_index("users_email_idx", table_name="users")
    op.drop_table("users")
