"""
Alembic migration environment.

Reads POSTGRES_* env vars at runtime so the DSN is never hardcoded.
Runs in offline mode (emit SQL) or online mode (direct connection).
"""

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Load repo-root .env when running `alembic -c infra/migrations/alembic.ini upgrade head`
try:
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Wire Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Build DSN from environment variables
# ---------------------------------------------------------------------------
_host = os.environ.get("POSTGRES_HOST", "localhost")
_port = os.environ.get("POSTGRES_PORT", "5432")
_db = os.environ.get("POSTGRES_DB", "medivault")
_user = os.environ.get("POSTGRES_USER", "medivault_user")
_pass = os.environ.get("POSTGRES_PASSWORD", "")

# Use psycopg2 (sync) for Alembic — asyncpg is for runtime FastAPI use
_dsn = f"postgresql+psycopg2://{_user}:{_pass}@{_host}:{_port}/{_db}"
config.set_main_option("sqlalchemy.url", _dsn)

# ---------------------------------------------------------------------------
# Target metadata — None for now; we use raw SQL in migrations.
# If we later switch to autogenerate, import all models here.
# ---------------------------------------------------------------------------
target_metadata = None


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
