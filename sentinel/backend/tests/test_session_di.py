"""
Phase 8 Step 1 Tests: Database Session & Repository Dependency Injection Engine.

Tests:
1. PostgreSQL repository dependency resolves correctly when PostgreSQL mode is active.
2. Development/test mode can intentionally resolve InMemoryCaseRepository.
3. PostgreSQL-unavailable production mode does NOT silently fall back to data_store (fails fast).
4. AsyncSession is closed after dependency lifecycle completion.
5. Exceptions trigger session rollback.
6. Existing disposition/history API contracts remain unchanged.
"""

import os
import unittest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.db.config import get_database_url
from app.db.session import get_async_engine, get_async_session_factory, get_db_session
from app.repositories.base import AbstractCaseRepository
from app.repositories.postgres import PostgreSQLCaseRepository
from app.repositories.in_memory import InMemoryCaseRepository
from app.core.data_store import data_store
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.case import Case
from main import app, get_repository


class TestDatabaseSessionDI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_url = os.getenv("DATABASE_URL")
        if not cls.db_url:
            cls.db_url = get_database_url(async_driver=True)
        cls.has_postgres = bool(cls.db_url and cls.db_url.startswith("postgresql"))

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_di_01_postgres_mode_resolves_postgres_repository(self):
        """Step 1.1: Dependency Injection yields PostgreSQLCaseRepository when PostgreSQL session is active."""
        if not self.has_postgres:
            self.skipTest("PostgreSQL not active")

        async def run_test():
            gen = get_db_session()
            session = await gen.__anext__()
            try:
                self.assertIsInstance(session, AsyncSession)
                repo = get_repository(session)
                self.assertIsInstance(repo, PostgreSQLCaseRepository)
            finally:
                try:
                    await gen.__anext__()
                except StopAsyncIteration:
                    pass

        self.run_async(run_test())

    def test_di_02_dev_mode_resolves_in_memory_repository(self):
        """Step 1.2: Dependency Injection yields InMemoryCaseRepository when session is None in development mode."""
        with patch.dict(os.environ, {"DATABASE_URL": "", "SENTINEL_MODE": "development"}):
            repo = get_repository(session=None)
            self.assertIsInstance(repo, InMemoryCaseRepository)

    def test_di_03_production_mode_fails_fast_when_postgres_unavailable(self):
        """Step 1.3: Production mode fails fast with RuntimeError when PostgreSQL is unavailable (no silent fallback)."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://invalid:invalid@localhost:9999/invalid", "SENTINEL_MODE": "production"}):
            with self.assertRaises(RuntimeError) as ctx:
                get_repository(session=None)
            self.assertIn("POSTGRESQL PERSISTENCE FAILURE", str(ctx.exception))

    def test_di_04_session_closed_after_lifecycle(self):
        """Step 1.4: AsyncSession generator closes the session post-lifecycle."""
        if not self.has_postgres:
            self.skipTest("PostgreSQL not active")

        async def run_test():
            gen = get_db_session()
            session = await gen.__anext__()
            with patch.object(session, "close", wraps=session.close) as mock_close:
                try:
                    await gen.__anext__()
                except StopAsyncIteration:
                    pass
                mock_close.assert_called_once()

        self.run_async(run_test())


    def test_di_05_session_rollback_on_exception(self):
        """Step 1.5: Generator performs session rollback when an exception occurs inside the endpoint block."""
        if not self.has_postgres:
            self.skipTest("PostgreSQL not active")

        async def run_test():
            gen = get_db_session()
            session = await gen.__anext__()
            
            with patch.object(session, 'rollback', wraps=session.rollback) as mock_rollback:
                with self.assertRaises(ValueError):
                    try:
                        raise ValueError("Simulated handler failure")
                    except Exception as e:
                        await gen.athrow(e)
                mock_rollback.assert_called_once()

        self.run_async(run_test())

    def test_di_06_disposition_and_history_api_contracts(self):
        """Step 1.6: /cases/{case_id}/disposition and /cases/{case_id}/history APIs preserve existing response schema."""
        client = TestClient(app)
        
        # Test Case Not Found history response contract
        res_hist = client.get("/cases/NON-EXISTENT-CASE/history")
        self.assertEqual(res_hist.status_code, 200)
        data_hist = res_hist.json()
        self.assertFalse(data_hist["found"])
        self.assertEqual(data_hist["status"], "INSUFFICIENT_DATA")
        self.assertIn("disposition_history", data_hist)
        self.assertIn("audit_history", data_hist)

        # Test Case Not Found disposition response contract
        res_disp = client.post(
            "/cases/NON-EXISTENT-CASE/disposition",
            json={"action_code": "APPROVE_TRANSACTION", "analyst_notes": "Test"}
        )
        self.assertEqual(res_disp.status_code, 200)
        data_disp = res_disp.json()
        self.assertFalse(data_disp["ok"])
        self.assertEqual(data_disp["status"], "INVALID_INPUT")
        self.assertFalse(data_disp["acknowledged"])


if __name__ == "__main__":
    unittest.main()
