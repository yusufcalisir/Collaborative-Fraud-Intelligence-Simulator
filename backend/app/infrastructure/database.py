"""Async database engine and session management.

Uses SQLAlchemy 2.0 async API with asyncpg for non-blocking PostgreSQL/CockroachDB access.
Sessions are scoped to FastAPI requests via dependency injection.
"""

import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


settings = get_settings()

# Configure engine options tailored for distributed high-write databases like CockroachDB
engine_kwargs: dict[str, Any] = {
    "echo": settings.app_debug,
    "pool_size": 10 if settings.database_type == "cockroachdb" else 5,
    "max_overflow": 20 if settings.database_type == "cockroachdb" else 10,
    "pool_pre_ping": True,
}

# CockroachDB connection tuning arguments
if settings.database_type == "cockroachdb":
    engine_kwargs["connect_args"] = {
        "application_name": "cfi_platform",
    }

engine = create_async_engine(settings.database_url, **engine_kwargs)

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


async def run_cockroach_transaction(
    session_factory: async_sessionmaker[AsyncSession],
    callback: Callable[[AsyncSession], Coroutine[Any, Any, Any]],
    max_retries: int = 5,
) -> Any:
    """Execute a database transaction block with CockroachDB serializable isolation conflict retry loops.

    Saves state by handling SQLSTATE 40001 (serialization_failure) and transparently retrying.
    """
    for attempt in range(max_retries):
        async with session_factory() as session, session.begin():
            try:
                return await callback(session)
            except DBAPIError as err:
                # SQLSTATE 40001 represents a retryable transaction failure in CockroachDB/PostgreSQL
                if (
                    err.orig
                    and hasattr(err.orig, "pgcode")
                    and err.orig.pgcode == "40001"
                    and attempt < max_retries - 1
                ):
                    logger.warning(
                        "CockroachDB serializable transaction conflict (40001) detected. "
                        "Retrying transaction attempt %d/%d...",
                        attempt + 1,
                        max_retries,
                    )
                    continue
                raise
