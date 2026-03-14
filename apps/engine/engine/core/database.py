"""Async SQLAlchemy engine and session factory for TimescaleDB."""

import threading
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from engine.core.config import settings
from engine.core.logging import get_logger

log = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_init_lock = threading.Lock()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def get_engine() -> AsyncEngine:
    """Get or create the async SQLAlchemy engine (thread-safe)."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        with _init_lock:
            if _engine is None:
                _engine = create_async_engine(
                    settings.database_url,
                    echo=settings.debug,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory (thread-safe)."""
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        with _init_lock:
            if _session_factory is None:
                _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def check_db_health() -> bool:
    """Check if the database is reachable."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        log.warning("db_health_check_failed", exc_info=True)
        return False


async def dispose_engine() -> None:
    """Dispose the database engine on shutdown."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
