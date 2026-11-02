"""Document accounting/integrity and public session identifiers."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision='016'
down_revision='015'
branch_labels=depends_on=None


def upgrade():
    op.add_column('reports',sa.Column('original_size_bytes',sa.BigInteger(),nullable=True))
    op.add_column('reports',sa.Column('stored_size_bytes',sa.BigInteger(),nullable=True))
    op.add_column('reports',sa.Column('content_sha256',sa.String(64),nullable=True))
    op.create_check_constraint('reports_nonnegative_sizes','reports',
        '(original_size_bytes IS NULL OR original_size_bytes >= 0) AND (stored_size_bytes IS NULL OR stored_size_bytes >= 0)')
    op.add_column('auth_sessions',sa.Column('public_id',UUID(as_uuid=True),server_default=sa.text('gen_random_uuid()'),nullable=False))
    op.create_unique_constraint('auth_sessions_public_id_key','auth_sessions',['public_id'])
    # Earlier sessions have no trustworthy creation timestamp; display unknown.
    op.add_column('auth_sessions',sa.Column('created_at',sa.DateTime(timezone=True),nullable=True))


def downgrade():
    op.drop_column('auth_sessions','created_at')
    op.drop_constraint('auth_sessions_public_id_key','auth_sessions',type_='unique')
    op.drop_column('auth_sessions','public_id')
    op.drop_constraint('reports_nonnegative_sizes','reports',type_='check')
    for name in ['content_sha256','stored_size_bytes','original_size_bytes']: op.drop_column('reports',name)
