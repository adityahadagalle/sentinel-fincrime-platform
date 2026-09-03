"""
Database Environment Configuration for SENTINEL (Phase 7).
"""

import os

DEFAULT_ASYNC_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/sentinel_db"
DEFAULT_SYNC_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/sentinel_db"


def get_database_url(async_driver: bool = True) -> str:
    """
    Returns the database connection URL from environment variable DATABASE_URL,
    falling back to DEFAULT_ASYNC_DATABASE_URL or DEFAULT_SYNC_DATABASE_URL.
    """
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        if async_driver and env_url.startswith("postgresql://"):
            return env_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not async_driver and env_url.startswith("postgresql+asyncpg://"):
            return env_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        return env_url
    return DEFAULT_ASYNC_DATABASE_URL if async_driver else DEFAULT_SYNC_DATABASE_URL
