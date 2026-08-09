"""
health-service/db/base_repository.py

Base repository that structurally enforces owner_id scoping at the query layer.

PRIVACY RULE (02_ARCHITECTURE.md §4, §5):
  Every table storing personal health data is scoped by owner_id at the
  QUERY layer, not just the API layer. This base class makes it structurally
  impossible to retrieve health data without supplying an owner_id.

  Concretely: no subclass of ScopedRepository can issue a SELECT on a scoped
  table without going through a method that requires an owner_id parameter.
  Do not add methods that accept owner_id=None — reject that in code review.
"""

from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for health-service models."""
    pass


ModelT = TypeVar("ModelT", bound=Base)


class ScopedRepository(Generic[ModelT]):
    """
    Owner-scoped repository base class.

    Every subclass targets a single SQLAlchemy model that has an `owner_id`
    column (UUID). All data-access methods require `owner_id` as a mandatory
    parameter — there is no method to list or fetch records without it.

    This is the *structural* enforcement of the query-layer scoping rule.
    It is not a substitute for also validating the token-authenticated user
    in the API handler, but it prevents the repository layer from ever
    returning cross-user data even if the handler forgets.
    """

    model: Type[ModelT]  # set by subclass

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, record_id: UUID, owner_id: UUID) -> ModelT | None:
        """
        Fetch a single record by primary key, scoped to owner_id.
        Returns None if the record doesn't exist OR belongs to a different user —
        callers cannot distinguish the two cases, which is intentional (no enumeration).
        """
        result = await self._session.execute(
            select(self.model).where(
                self.model.id == record_id,
                self.model.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_owner(
        self,
        owner_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ModelT]:
        """List all records belonging to owner_id, paginated."""
        result = await self._session.execute(
            select(self.model)
            .where(self.model.owner_id == owner_id)
            .limit(limit)
            .offset(offset)
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def create(self, owner_id: UUID, **kwargs: Any) -> ModelT:
        """
        Create a new record, always stamping owner_id from the caller.
        Never trust an owner_id that comes from the request body — the caller
        (API handler) must pass the authenticated user's ID here directly.
        """
        record = self.model(owner_id=owner_id, **kwargs)
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def delete_for_owner(self, record_id: UUID, owner_id: UUID) -> bool:
        """
        Hard-delete a record, scoped to owner_id.
        Returns True if a row was deleted, False if not found or wrong owner.
        Callers should treat both False cases identically (404 to the API consumer).
        """
        result = await self._session.execute(
            delete(self.model).where(
                self.model.id == record_id,
                self.model.owner_id == owner_id,
            )
        )
        await self._session.flush()
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Intentionally absent: any method that queries WITHOUT owner_id.
    # If you find yourself needing one (e.g. for a background job), add it
    # to a separate AdminRepository subclass, never to this class, and
    # add a DEV_LOG entry explaining why it's safe.
    # ------------------------------------------------------------------
