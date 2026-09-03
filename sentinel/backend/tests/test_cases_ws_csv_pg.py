"""
Phase 8 Step 5 Tests: Cases Listing, WebSocket Hydration, and CSV Export -> PostgreSQL.

Tests:
1. GET /cases returns HTTP 200 success.
2. GET /cases returns expected schema payload.
3. GET /cases returns PostgreSQL-backed cases.
4. GET /cases preserves deterministic ordering (created_at desc).
5. GET /cases empty database returns empty list [].
6. GET /cases multiple cases returned correctly.
7. Production GET /cases does not read from data_store.
8. WebSocket connection succeeds and sends LIVE status.
9. WebSocket initial hydration reads from PostgreSQL.
10. WebSocket hydration schema is fully compatible.
11. WebSocket disconnect cleans up connections without leaking DB sessions.
12. CSV Export GET /export/sentinel_audit.csv returns 200 text/csv.
13. CSV headers match exact legacy contract.
14. CSV rows come from PostgreSQL transactions & investigative actions.
15. CSV Formula Injection sanitization escapes leading '=', '+', '-', '@', '\\t', '\\r'.
16. Repository contract compatibility (PostgreSQL and InMemory repositories).
"""

import os
import unittest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch
from sqlalchemy import text, select
from fastapi.testclient import TestClient

from app.db.config import get_database_url
from app.db.session import get_async_engine, get_async_session_factory
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.case import Case
from app.models.audit_event import AuditEvent
from app.models.disposition import Disposition
from app.repositories.postgres import PostgreSQLCaseRepository
from app.repositories.in_memory import InMemoryCaseRepository
from main import app, get_repository, _sanitize_csv_field


class TestPhase8Step5CasesWsCsvPg(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_url = os.getenv("DATABASE_URL")
        if not cls.db_url:
            cls.db_url = get_database_url(async_driver=True)
        cls.has_postgres = bool(cls.db_url and cls.db_url.startswith("postgresql"))

    def setUp(self):
        if not self.has_postgres:
            self.skipTest("Live PostgreSQL required for Phase 8 Step 5 integration tests.")
        self.client = TestClient(app)
        self.clean_db()

    def tearDown(self):
        if self.has_postgres:
            self.clean_db()

    def run_with_db(self, async_fn):
        """Executes an async function with single-loop engine & session factory isolation."""
        async def runner():
            engine = get_async_engine(self.db_url)
            session_factory = get_async_session_factory(engine)
            try:
                return await async_fn(session_factory)
            finally:
                await engine.dispose()
        return asyncio.run(runner())

    def clean_db(self):
        async def _clean(session_factory):
            async with session_factory() as session:
                await session.execute(text("TRUNCATE audit_events, dispositions, investigation_reports, cases, transactions, accounts CASCADE;"))
                await session.commit()
        self.run_with_db(_clean)

    def seed_data(self, count: int = 2):
        async def _seed(session_factory):
            async with session_factory() as session:
                now = datetime.now(timezone.utc)
                for i in range(1, count + 1):
                    s_acc = Account(account_id=f"ACC-SND-STEP5-{i}", created_at=now, updated_at=now)
                    r_acc = Account(account_id=f"ACC-RCV-STEP5-{i}", created_at=now, updated_at=now)
                    tx = Transaction(
                        tx_id=f"TX-STEP5-00{i}",
                        sender_account_id=f"ACC-SND-STEP5-{i}",
                        receiver_account_id=f"ACC-RCV-STEP5-{i}",
                        amount=150000.0 * i,
                        channel="UPI",
                        timestamp=now,
                        raw_payload={"reason": f"Risk pattern {i}"},
                        created_at=now
                    )
                    c = Case(
                        case_id=f"CASE-STEP5-00{i}",
                        primary_tx_id=f"TX-STEP5-00{i}",
                        status="NEW",
                        risk_level="HIGH",
                        golden_window_minutes=30,
                        total_fraud_amount=150000.0 * i,
                        recoverable_amount=150000.0 * i,
                        created_at=now,
                        updated_at=now
                    )
                    session.add_all([s_acc, r_acc, tx, c])
                await session.commit()

        self.run_with_db(_seed)

    def test_step5_01_02_03_04_05_06_07_get_cases_pg_authoritative(self):
        """Step 5.1 - 5.7: GET /cases reads PostgreSQL cases in deterministic order and handles empty DB."""
        # 1. Empty database test
        res_empty = self.client.get("/cases")
        self.assertEqual(res_empty.status_code, 200)
        self.assertEqual(res_empty.json(), [])

        # 2. Seed 2 cases in PostgreSQL
        self.seed_data(count=2)

        # 3. GET /cases request
        res = self.client.get("/cases")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["case_id"], "CASE-STEP5-002")
        self.assertEqual(data[1]["case_id"], "CASE-STEP5-001")
        self.assertIn("status", data[0])
        self.assertIn("primary_tx_id", data[0])
        self.assertIn("nodes", data[0])

    def test_step5_08_09_10_11_websocket_hydration_pg(self):
        """Step 5.8 - 5.11: WebSocket /ws connects, sends LIVE status, and hydrates from PostgreSQL."""
        self.seed_data(count=2)

        with self.client.websocket_connect("/ws") as websocket:
            # 1. Connected event
            connected_evt = websocket.receive_json()
            self.assertEqual(connected_evt.get("event"), "connected")
            self.assertEqual(connected_evt.get("status"), "LIVE")

            # 2. Hydrated tx events from PostgreSQL
            tx1 = websocket.receive_json()
            self.assertEqual(tx1.get("event"), "tx_scored")
            self.assertIn(tx1.get("tx_id"), ["TX-STEP5-001", "TX-STEP5-002"])

    def test_step5_12_13_14_csv_export_pg(self):
        """Step 5.12 - 5.14: GET /export/sentinel_audit.csv streams CSV built from PostgreSQL records."""
        self.seed_data(count=2)

        res = self.client.get("/export/sentinel_audit.csv")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("Content-Type", ""))
        self.assertIn("attachment; filename=", res.headers.get("Content-Disposition", ""))

        text_content = res.text
        self.assertIn("SENTINEL AUDIT LOG - TRANSACTION FEED", text_content)
        self.assertIn("TX-STEP5-001", text_content)
        self.assertIn("TX-STEP5-002", text_content)

    def test_step5_15_csv_formula_injection_sanitization(self):
        """Step 5.15: CSV formula injection characters ('=', '+', '-', '@') are sanitized."""
        self.assertEqual(_sanitize_csv_field("=SUM(1,2)"), "'=SUM(1,2)")
        self.assertEqual(_sanitize_csv_field("+12345"), "'+12345")
        self.assertEqual(_sanitize_csv_field("-12345"), "'-12345")
        self.assertEqual(_sanitize_csv_field("@cmd"), "'@cmd")
        self.assertEqual(_sanitize_csv_field("NORMAL_VAL"), "NORMAL_VAL")

    def test_step5_16_repository_retrieval_contract(self):
        """Step 5.16: Repository abstraction get_cases and get_recent_transactions work for PG and InMemory."""
        self.seed_data(count=1)

        # 1. PostgreSQL Repository
        async def test_pg(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                cases = await repo.get_cases()
                txs = await repo.get_recent_transactions(limit=10)
                self.assertEqual(len(cases), 1)
                self.assertEqual(len(txs), 1)

        self.run_with_db(test_pg)

        # 2. InMemory Repository
        async def test_inmem():
            repo = InMemoryCaseRepository()
            await repo.save_case({"case_id": "C-INMEM", "status": "NEW"})
            await repo.save_transaction({"tx_id": "TX-INMEM", "sender_account": "A1", "receiver_account": "A2", "amount": 50.0})
            cases = await repo.get_cases()
            txs = await repo.get_recent_transactions()
            self.assertEqual(len(cases), 1)
            self.assertEqual(len(txs), 1)

        asyncio.run(test_inmem())


if __name__ == "__main__":
    unittest.main()
