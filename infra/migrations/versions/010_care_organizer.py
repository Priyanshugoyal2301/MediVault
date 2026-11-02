"""Patient-entered referrals, claim diary, benefits wallet and vaccinations."""
import sqlalchemy as sa
from alembic import op
revision = "010"
down_revision = "009"
branch_labels = depends_on = None


def common():
    return [sa.Column("id",sa.Uuid(),primary_key=True),
        sa.Column("patient_id",sa.Uuid(),sa.ForeignKey("patients.id"),nullable=False),
        sa.Column("recorded_by",sa.Uuid(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("version",sa.Integer(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("notes",sa.Text(),nullable=False)]


def string(name,size=200):
    return sa.Column(name,sa.String(size),nullable=False)


def upgrade():
    op.create_table("referrals",*common(),string("facility"),string("clinician",120),string("reason",500),
        sa.Column("issued_on",sa.Date(),nullable=False),sa.Column("valid_until",sa.Date()),string("status",30))
    op.create_table("claims",*common(),string("facility"),string("scheme",120),string("reference",120),
        string("amount_rupees",20),sa.Column("submitted_on",sa.Date()),string("status",30))
    op.create_table("benefit_cards",*common(),string("scheme",120),string("member_reference",120),
        sa.Column("valid_until",sa.Date()),string("contact"))
    op.create_table("vaccinations",*common(),string("name"),string("dose",100),
        sa.Column("administered_on",sa.Date(),nullable=False),string("facility"),sa.Column("next_due",sa.Date()))
    for table in ("referrals","claims","benefit_cards","vaccinations"):
        op.create_index(f"ix_{table}_patient_id",table,["patient_id"])


def downgrade():
    for table in ("vaccinations","benefit_cards","claims","referrals"):
        op.drop_table(table)
