"""Create Q&A and knowledge base tables: knowledge_documents, qa_sessions, qa_messages

Revision ID: 003
Revises: 002
Create Date: 2026-08-09

DB-LEVEL owner_id ENFORCEMENT (02_ARCHITECTURE.md §4, §5):
  qa_sessions and qa_messages both have owner_id NOT NULL FK → users(id) ON DELETE CASCADE.
  knowledge_documents is a shared (non-user-owned) corpus — no owner_id.

  pgvector extension is enabled for vector similarity search on embeddings.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------
    # knowledge_documents — curated medical corpus chunks + embeddings
    # This is SHARED data (not user-owned), so no owner_id column.
    # ------------------------------------------------------------------
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_title", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("source_licence", sa.String(200), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # pgvector embedding column (384-dim; all-MiniLM-L6-v2) added via raw SQL
    op.execute(
        "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS "
        "embedding vector(384)"
    )

    op.create_index(
        "knowledge_documents_source_idx",
        "knowledge_documents",
        ["source_title"],
    )

    # ------------------------------------------------------------------
    # qa_sessions — user Q&A conversation sessions
    # ------------------------------------------------------------------
    op.create_table(
        "qa_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="qa_sessions_owner_id_fkey",
            ondelete="CASCADE",
        ),
    )
    op.create_index("qa_sessions_owner_idx", "qa_sessions", ["owner_id"])

    # ------------------------------------------------------------------
    # qa_messages — individual Q&A turns within a session
    # ------------------------------------------------------------------
    op.create_table(
        "qa_messages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),  # user | assistant | safety
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hi", sa.Text(), nullable=True),  # Hindi translation
        sa.Column("citations", sa.JSON(), nullable=True),  # [{index, source, url}]
        sa.Column("safety_triggered", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["qa_sessions.id"],
            name="qa_messages_session_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="qa_messages_owner_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'safety')",
            name="qa_messages_role_check",
        ),
    )
    op.create_index("qa_messages_session_idx", "qa_messages", ["session_id"])
    op.create_index("qa_messages_owner_idx", "qa_messages", ["owner_id"])


def downgrade() -> None:
    op.drop_index("qa_messages_owner_idx", table_name="qa_messages")
    op.drop_index("qa_messages_session_idx", table_name="qa_messages")
    op.drop_table("qa_messages")

    op.drop_index("qa_sessions_owner_idx", table_name="qa_sessions")
    op.drop_table("qa_sessions")

    op.drop_index("knowledge_documents_source_idx", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
