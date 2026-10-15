"""Database connection, engine configuration, and session management for PostgreSQL."""

import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.env import load_env_file

load_env_file()

DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/decision_blackjack",
)

# Convert standard postgresql:// to postgresql+asyncpg:// if needed
if DEFAULT_DATABASE_URL.startswith("postgresql://"):
    DEFAULT_DATABASE_URL = DEFAULT_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(url: str | None = None, **kwargs: Any) -> AsyncEngine:
    """Return the singleton or newly initialized async SQLAlchemy engine.

    Args:
        url: Optional database connection URL. If omitted, uses DEFAULT_DATABASE_URL.
        **kwargs: Additional parameters passed to create_async_engine.
    """
    global _engine
    target_url = url or DEFAULT_DATABASE_URL
    if target_url.startswith("postgresql://"):
        target_url = target_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if _engine is None or (url is not None and str(_engine.url) != target_url):
        engine_kwargs = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            **kwargs,
        }
        _engine = create_async_engine(target_url, **engine_kwargs)
    return _engine


def get_session_factory(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    """Return the async session factory associated with the active engine."""
    global _session_factory
    active_engine = engine or get_engine()
    if _session_factory is None or engine is not None:
        _session_factory = async_sessionmaker(
            bind=active_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_health(engine: AsyncEngine | None = None) -> bool:
    """Execute a simple query to verify PostgreSQL connectivity.

    Returns:
        True if the database responds, False otherwise.
    """
    active_engine = engine or get_engine()
    try:
        async with active_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return bool(result.scalar() == 1)
    except Exception:  # noqa: BLE001
        return False


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Auto-provision all defined tables, ENUMs, and indexes via Base.metadata.create_all."""
    try:
        from app.persistence.models import Base
    except ImportError:
        from backend.app.persistence.models import Base

    active_engine = engine or get_engine()
    async with active_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the active engine connection pool."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
