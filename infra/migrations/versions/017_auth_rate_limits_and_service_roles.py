"""Isolate runtime database roles and persist source-based login limits."""

import os

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = depends_on = None

HEALTH_TABLES = (
    "reports", "report_values", "timeline_events", "qa_sessions", "qa_messages",
    "patients", "clinicians", "care_grants", "medications", "allergies",
    "encounters", "appointments", "care_audit_events", "care_record_revisions",
    "verification_decisions", "referrals", "claims", "benefit_cards", "vaccinations",
    "storage_deletions", "prescription_reviews",
)


def _sql_literal(value: str) -> str:
    """Quote a secret as a PostgreSQL string literal without logging it."""
    return "'" + value.replace("'", "''") + "'"


def _role_password(name: str) -> str:
    password = os.environ.get(name, "")
    if len(password) < 32 or "CHANGE_ME" in password:
        raise RuntimeError(f"Set {name} to a unique random value of at least 32 characters before migration.")
    return _sql_literal(password)


def _ensure_login_role(role: str, password: str) -> None:
    op.execute(
        f"""DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}') THEN
                CREATE ROLE {role} LOGIN PASSWORD {password}
                    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
            ELSE
                ALTER ROLE {role} WITH LOGIN PASSWORD {password}
                    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS INHERIT;
            END IF;
        END
        $$;"""
    )


def upgrade() -> None:
    auth_password = _role_password("POSTGRES_AUTH_PASSWORD")
    health_password = _role_password("POSTGRES_HEALTH_PASSWORD")
    _ensure_login_role("medivault_auth", auth_password)
    _ensure_login_role("medivault_health", health_password)

    op.create_table(
        "auth_login_attempts",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_auth_login_attempts_window_started_at",
        "auth_login_attempts",
        ["window_started_at"],
    )

    op.execute("GRANT USAGE ON SCHEMA public TO medivault_auth, medivault_health")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.users, public.auth_sessions, public.auth_login_attempts TO medivault_auth")
    op.execute("GRANT SELECT (id) ON TABLE public.users TO medivault_health")
    for table_name in HEALTH_TABLES:
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public."{table_name}" TO medivault_health')


def downgrade() -> None:
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM medivault_auth, medivault_health")
    op.execute("REVOKE SELECT (id) ON TABLE public.users FROM medivault_health")
    op.execute("REVOKE ALL PRIVILEGES ON SCHEMA public FROM medivault_auth, medivault_health")
    op.drop_index("ix_auth_login_attempts_window_started_at", table_name="auth_login_attempts")
    op.drop_table("auth_login_attempts")
    op.execute("DROP ROLE IF EXISTS medivault_health")
    op.execute("DROP ROLE IF EXISTS medivault_auth")
