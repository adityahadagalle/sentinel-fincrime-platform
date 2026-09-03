"""
SQLAlchemy Async Engine & Session Management (Phase 7 / Phase 8 Step 1 / Phase 12 Hardening).
"""

import os
import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


from app.db.config import get_database_url


class Base(DeclarativeBase):
    """Base declarative class for all Phase 7 SQLAlchemy ORM models."""
    pass


_async_engine: Optional[AsyncEngine] = None
_engine_loop: Optional[asyncio.AbstractEventLoop] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine(db_url: str = None) -> AsyncEngine:
    """
    Returns a singleton async SQLAlchemy engine instance bound to the active event loop.
    """
    global _async_engine, _engine_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _async_engine is None or db_url is not None or (_engine_loop is not None and current_loop != _engine_loop):
        url = db_url or get_database_url(async_driver=True)
        engine = create_async_engine(
            url,
            echo=False,
            future=True,
            pool_pre_ping=True
        )
        if db_url is None:
            _async_engine = engine
            _engine_loop = current_loop
            return _async_engine
        return engine
    return _async_engine


def get_async_session_factory(engine=None) -> async_sessionmaker[AsyncSession]:
    """
    Returns an async sessionmaker factory for the active engine.
    """
    eng = engine or get_async_engine()
    return async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )



async def close_async_engine() -> None:
    """
    Disposes of the singleton database engine connection pool on app shutdown.
    """
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None


async def get_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    FastAPI Dependency yielding scoped AsyncSession.
    Handles exception rollback and session cleanup.

    Mode Behavior:
    - Production Mode (SENTINEL_MODE=production or explicit PostgreSQL configuration):
      Must resolve to PostgreSQL. If connection/session fails, FAILS FAST.
    - Development / Test Mode (SENTINEL_MODE=development and DATABASE_URL unset):
      Yields None to allow explicit development fallback to InMemoryCaseRepository.
    """
    db_url = os.getenv("DATABASE_URL")
    sentinel_mode = os.getenv("SENTINEL_MODE", "development").lower()

    if not db_url and sentinel_mode != "production":
        yield None
        return

    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
    except Exception as exc:
        await session.rollback()
        raise exc
    finally:
        await session.close()
