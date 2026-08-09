"""
auth-service/db/models.py

SQLAlchemy ORM model for the users table.
Schema defined in infra/migrations/versions/001_create_users_table.py.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "locale_preference IN ('en-IN', 'hi-IN')",
            name="users_locale_preference_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    locale_preference: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en-IN"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
