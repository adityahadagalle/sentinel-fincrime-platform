"""
Repository Dependency Provider for SENTINEL (Phase 8 Step 1 / Hardening).

Decoupled provider for AbstractCaseRepository to enable dependency injection
across route modules (main.py, intelligence.py, etc.) without circular imports.
"""

import os
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.base import AbstractCaseRepository
from app.repositories.postgres import PostgreSQLCaseRepository
from app.repositories.in_memory import InMemoryCaseRepository
from app.core.data_store import data_store


def get_repository(
    session: Optional[AsyncSession] = Depends(get_db_session)
) -> AbstractCaseRepository:
    """
    FastAPI Dependency Provider for AbstractCaseRepository.
    - If AsyncSession is active: returns PostgreSQLCaseRepository(session).
    - If AsyncSession is None and in dev/test mode: returns InMemoryCaseRepository(data_store).
    - If in production mode or PostgreSQL configured but session is None: FAILS FAST (raises RuntimeError).
    """
    sentinel_mode = os.getenv("SENTINEL_MODE", "development").lower()
    db_url = os.getenv("DATABASE_URL")
    is_postgres_env = bool(db_url and db_url.startswith("postgresql"))

    if session is not None:
        return PostgreSQLCaseRepository(session)

    if sentinel_mode == "production" or is_postgres_env:
        raise RuntimeError("POSTGRESQL PERSISTENCE FAILURE: Database session unavailable in production mode.")

    return InMemoryCaseRepository(data_store)
