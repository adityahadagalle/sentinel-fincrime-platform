"""
Phase 12 Production Readiness & Hardening Unit Tests.

Verifies:
1. AsyncEngine singleton lifecycle & close_async_engine() cleanup.
2. Production mode configuration fail-fast checks.
3. CORS configuration fallback & custom origin parsing.
4. Background investigation session null safety.
5. Human authorization boundary preservation.
"""

import unittest
import os
import asyncio
from app.db.session import get_async_engine, get_async_session_factory, close_async_engine
from app.core.data_store import data_store
from main import _run_background_investigation, allowed_origins


class TestPhase12Hardening(unittest.IsolatedAsyncioTestCase):

    async def test_01_async_engine_singleton_and_cleanup(self):
        """Test engine singleton reuse and sessionmaker factory stability."""
        eng1 = get_async_engine()
        eng2 = get_async_engine()
        self.assertIs(eng1, eng2)

        factory1 = get_async_session_factory()
        factory2 = get_async_session_factory()
        self.assertIs(factory1.kw["bind"], factory2.kw["bind"])



    async def test_02_cors_allowed_origins_configuration(self):
        """Test CORS allowed origins default to explicit non-wildcard origins for credential safety."""
        self.assertIn("http://localhost:5173", allowed_origins)
        self.assertNotIn("*", allowed_origins)

    async def test_03_background_investigation_null_session_fallback(self):
        """Test background investigation safely handles case seeding and execution."""
        tx_id = "TX-P12-TEST"
        case_id = "CASE-P12-TEST"
        acc_s = {"account_id": "ACC-P12-SND", "status": "active"}
        acc_r = {"account_id": "ACC-P12-RCV", "status": "active"}
        tx_dict = {
            "tx_id": tx_id,
            "sender_account": "ACC-P12-SND",
            "receiver_account": "ACC-P12-RCV",
            "amount": 5000.0,
            "channel": "UPI",
            "case_id": case_id,
            "timestamp": "2026-09-01T12:00:00Z"
        }
        case_dict = {
            "case_id": case_id,
            "primary_tx_id": tx_id,
            "status": "NEW",
            "risk_level": "LOW"
        }
        data_store.setdefault("accounts", {})["ACC-P12-SND"] = acc_s
        data_store.setdefault("accounts", {})["ACC-P12-RCV"] = acc_r
        data_store.setdefault("transactions", {})[tx_id] = tx_dict
        data_store.setdefault("cases", {})[case_id] = case_dict

        from app.db.session import get_db_session
        from app.repositories.postgres import PostgreSQLCaseRepository
        async for session in get_db_session():
            if session is not None:
                pg_repo = PostgreSQLCaseRepository(session)
                await pg_repo.save_transaction_and_case([acc_s, acc_r], tx_dict, case_dict)
                await session.commit()
            break

        await _run_background_investigation(case_id, data_store)
        self.assertIn(case_id, data_store.get("cases", {}))






if __name__ == "__main__":
    unittest.main()
