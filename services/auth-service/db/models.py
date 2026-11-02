"""
auth-service/db/models.py

SQLAlchemy ORM model for the users table.
Schema defined in infra/migrations/versions/001_create_users_table.py.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, ForeignKey, BigInteger, JSON, Text, Integer, Index
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
    otp_secret: Mapped[str | None] = mapped_column(Text)
    otp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    otp_last_counter: Mapped[int] = mapped_column(BigInteger, default=-1)
    otp_recovery: Mapped[list | None] = mapped_column(JSON)
    auth_failures: Mapped[int] = mapped_column(Integer, default=0)
    auth_window_started: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),default=uuid.uuid4,unique=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(UTC))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthLoginAttempt(Base):
    __tablename__ = "auth_login_attempts"
    __table_args__ = (Index("ix_auth_login_attempts_window_started_at", "window_started_at"),)

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
