"""
auth-service/db/repositories/user_repository.py

User data access. Does NOT subclass ScopedRepository because users
own themselves — there is no outer owner. However, it follows the same
discipline: methods that look up by ID always require either the requesting
user's own ID or email-based lookup (for login), never a global list.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email.lower(), User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: str,
        locale_preference: str = "en-IN",
    ) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            locale_preference=locale_preference,
            created_at=datetime.now(UTC),
            is_active=True,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def soft_delete(self, user_id: uuid.UUID) -> bool:
        """Soft-delete: sets deleted_at and is_active=False."""
        result = await self._session.execute(
            update(User)
            .where(User.id == user_id, User.is_active.is_(True))
            .values(deleted_at=datetime.now(UTC), is_active=False)
        )
        return result.rowcount > 0
