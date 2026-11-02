"""Store safe processing feedback independently of private extraction content."""
import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = depends_on = None


def upgrade():
    op.add_column('reports', sa.Column('processing_note', sa.String(500)))


def downgrade():
    op.drop_column('reports', 'processing_note')
