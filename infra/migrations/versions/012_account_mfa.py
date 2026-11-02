"""Optional authenticator MFA and single-use recovery codes."""
import sqlalchemy as sa
from alembic import op
revision = "012"
down_revision = "011"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users",sa.Column("otp_secret",sa.Text()))
    op.add_column("users",sa.Column("otp_enabled",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column("users",sa.Column("otp_last_counter",sa.BigInteger(),nullable=False,server_default="-1"))
    op.add_column("users",sa.Column("otp_recovery",sa.JSON()))


def downgrade():
    for name in ("otp_recovery","otp_last_counter","otp_enabled","otp_secret"):
        op.drop_column("users",name)
