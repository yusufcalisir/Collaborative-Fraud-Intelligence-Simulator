"""Async database engine and session management.

Uses SQLAlchemy 2.0 async API with asyncpg for non-blocking PostgreSQL access.
Sessions are scoped to FastAPI requests via dependency injection.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session scoped to the current request.

    The session is automatically closed when the request completes.
    Commits are managed by the service layer, not here.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
