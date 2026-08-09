"""health-service/db/session.py"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..core.config import get_settings

_settings = get_settings()
_engine = create_async_engine(_settings.async_db_url, echo=False, pool_pre_ping=True)
_SessionLocal = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
