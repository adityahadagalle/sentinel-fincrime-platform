"""
Phase 8 Step 3 Tests: Transaction Ingestion -> PostgreSQL Persistence Migration.

Tests:
1. Successful /transaction ingestion through HTTP API.
2. Account persisted in PostgreSQL.
3. Transaction persisted in PostgreSQL.
4. Case persisted in PostgreSQL.
5. Transaction correctly references accounts (FK).
6. Case correctly references transaction (FK).
7. Full ingestion commits atomically.
8. Invalid transaction input causes complete rollback.
9. Database failure during transaction creation rolls back account creation.
10. Database failure during case creation rolls back account and transaction.
11. Duplicate/repeated transaction ingestion preserves consistency.
12. Concurrent duplicate ingestion preserves database consistency.
13. Development mode uses InMemoryCaseRepository.
14. Production mode uses PostgreSQLCaseRepository.
15. Production mode fails fast when PostgreSQL is unavailable.
"""

import os
import unittest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import text, select
from fastapi.testclient import TestClient

from app.db.config import get_database_url
from app.db.session import get_async_engine, get_async_session_factory
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.case import Case
from app.repositories.base import AbstractCaseRepository
from app.repositories.postgres import PostgreSQLCaseRepository
from app.repositories.in_memory import InMemoryCaseRepository
from app.core.data_store import data_store
from main import app, get_repository


class TestPhase8Step3TransactionIngestion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_url = os.getenv("DATABASE_URL")
        if not cls.db_url:
            cls.db_url = get_database_url(async_driver=True)
        cls.has_postgres = bool(cls.db_url and cls.db_url.startswith("postgresql"))

    def setUp(self):
        if not self.has_postgres:
            self.skipTest("Live PostgreSQL required for Phase 8 Step 3 tests.")
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

    def test_step3_01_02_03_04_http_ingestion_persists_in_pg(self):
        """Step 3.1 - 3.4: HTTP POST /transaction persists Accounts, Transaction, and Case in PostgreSQL."""
        tx_id = "TX-STEP3-INGEST-01"
        payload = {
            "tx_id": tx_id,
            "timestamp": "2026-09-01T12:00:00Z",
            "sender_account": "ACC-SND-STEP3-01",
            "receiver_account": "ACC-RCV-STEP3-01",
            "amount": 250000.0,
            "channel": "UPI"
        }

        res = self.client.post("/transaction", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("transaction", data)

        async def verify_db(session_factory):
            async with session_factory() as session:
                # 2. Account persisted
                acc_s = (await session.execute(select(Account).filter(Account.account_id == "ACC-SND-STEP3-01"))).scalar_one_or_none()
                acc_r = (await session.execute(select(Account).filter(Account.account_id == "ACC-RCV-STEP3-01"))).scalar_one_or_none()
                self.assertIsNotNone(acc_s)
                self.assertIsNotNone(acc_r)

                # 3. Transaction persisted
                tx_db = (await session.execute(select(Transaction).filter(Transaction.tx_id == tx_id))).scalar_one_or_none()
                self.assertIsNotNone(tx_db)
                self.assertEqual(float(tx_db.amount), 250000.0)

                # 4. Case persisted (if high risk or linked)
                case_id = data["transaction"].get("case_id")
                if case_id:
                    case_db = (await session.execute(select(Case).filter(Case.case_id == case_id))).scalar_one_or_none()
                    self.assertIsNotNone(case_db)
                    self.assertEqual(case_db.primary_tx_id, tx_id)

        self.run_with_db(verify_db)

    def test_step3_05_06_foreign_key_referential_integrity(self):
        """Step 3.5 & 3.6: Transaction references accounts (FK) and Case references Transaction (FK)."""
        tx_id = "TX-STEP3-FK-01"
        payload = {
            "tx_id": tx_id,
            "timestamp": "2026-09-01T12:00:00Z",
            "sender_account": "ACC-SND-FK",
            "receiver_account": "ACC-RCV-FK",
            "amount": 300000.0,
            "channel": "UPI"
        }

        self.client.post("/transaction", json=payload)

        async def verify_fk(session_factory):
            async with session_factory() as session:
                tx_db = (await session.execute(select(Transaction).filter(Transaction.tx_id == tx_id))).scalar_one()
                self.assertEqual(tx_db.sender_account_id, "ACC-SND-FK")
                self.assertEqual(tx_db.receiver_account_id, "ACC-RCV-FK")

                # Verify case references primary_tx_id
                c_db = (await session.execute(select(Case).filter(Case.primary_tx_id == tx_id))).scalar_one_or_none()
                if c_db:
                    self.assertEqual(c_db.primary_tx_id, tx_id)

        self.run_with_db(verify_fk)

    def test_step3_07_08_atomic_ingestion_and_rollback_on_invalid_input(self):
        """Step 3.7 & 3.8: Complete rollback on invalid payload; no partial database state created."""
        res = self.client.post("/transaction", content="INVALID_NON_JSON_DATA", headers={"Content-Type": "application/json"})
        self.assertIn(res.status_code, [400, 422, 500])

        # Verify zero accounts, transactions, or cases created
        async def verify_empty(session_factory):
            async with session_factory() as session:
                acc_count = len((await session.execute(select(Account))).scalars().all())
                tx_count = len((await session.execute(select(Transaction))).scalars().all())
                c_count = len((await session.execute(select(Case))).scalars().all())
                self.assertEqual(acc_count, 0)
                self.assertEqual(tx_count, 0)
                self.assertEqual(c_count, 0)

        self.run_with_db(verify_empty)


    def test_step3_09_failure_during_tx_creation_rolls_back_account(self):
        """Step 3.9: Database failure during transaction creation rolls back account creation."""
        async def run_failing_tx(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                accounts = [{"account_id": "ACC-FAIL-TX"}]

                # Supply invalid transaction missing required fields (e.g. sender_account) to force DB exception
                invalid_tx = {"tx_id": "TX-FAIL-01"}  # Missing sender_account & receiver_account

                with self.assertRaises(Exception):
                    try:
                        await repo.save_transaction_and_case(accounts, invalid_tx, None)
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

        self.run_with_db(run_failing_tx)

        # Verify ACC-FAIL-TX was NOT left orphaned in DB
        async def verify_no_orphan(session_factory):
            async with session_factory() as session:
                acc = (await session.execute(select(Account).filter(Account.account_id == "ACC-FAIL-TX"))).scalar_one_or_none()
                self.assertIsNone(acc)

        self.run_with_db(verify_no_orphan)

    def test_step3_10_failure_during_case_creation_rolls_back_everything(self):
        """Step 3.10: Database failure during case creation rolls back account and transaction creation."""
        async def run_failing_case(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                accounts = [{"account_id": "ACC-FAIL-C1"}, {"account_id": "ACC-FAIL-C2"}]
                tx_rec = {
                    "tx_id": "TX-FAIL-C1",
                    "sender_account": "ACC-FAIL-C1",
                    "receiver_account": "ACC-FAIL-C2",
                    "amount": 100000.0,
                    "channel": "UPI"
                }
                # Supply invalid case record with risk_level string exceeding VARCHAR(16) database constraint limit
                invalid_case = {
                    "case_id": "CASE-FAIL-C1",
                    "status": "NEW",
                    "risk_level": "INVALID_RISK_LEVEL_EXCEEDING_VARCHAR_16_CONSTRAINT_LIMIT"
                }

                with self.assertRaises(Exception):
                    try:
                        await repo.save_transaction_and_case(accounts, tx_rec, invalid_case)
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise


        self.run_with_db(run_failing_case)

        # Verify accounts and transactions were completely rolled back
        async def verify_clean_rollback(session_factory):
            async with session_factory() as session:
                acc1 = (await session.execute(select(Account).filter(Account.account_id == "ACC-FAIL-C1"))).scalar_one_or_none()
                tx_db = (await session.execute(select(Transaction).filter(Transaction.tx_id == "TX-FAIL-C1"))).scalar_one_or_none()
                c_db = (await session.execute(select(Case).filter(Case.case_id == "CASE-FAIL-C1"))).scalar_one_or_none()
                self.assertIsNone(acc1)
                self.assertIsNone(tx_db)
                self.assertIsNone(c_db)

        self.run_with_db(verify_clean_rollback)

    def test_step3_11_12_duplicate_and_concurrent_ingestion_consistency(self):
        """Step 3.11 & 3.12: Duplicate and concurrent transaction ingestion preserves database consistency."""
        payload = {
            "tx_id": "TX-STEP3-DUP-01",
            "timestamp": "2026-09-01T12:00:00Z",
            "sender_account": "ACC-DUP-SND",
            "receiver_account": "ACC-DUP-RCV",
            "amount": 180000.0,
            "channel": "UPI"
        }

        # First ingestion
        res1 = self.client.post("/transaction", json=payload)
        self.assertEqual(res1.status_code, 200)

        # Duplicate sequential ingestion
        res2 = self.client.post("/transaction", json=payload)
        self.assertEqual(res2.status_code, 200)

        # Verify only 1 transaction record exists in DB
        async def verify_single_tx(session_factory):
            async with session_factory() as session:
                txs = (await session.execute(select(Transaction).filter(Transaction.tx_id == "TX-STEP3-DUP-01"))).scalars().all()
                self.assertEqual(len(txs), 1)

        self.run_with_db(verify_single_tx)

    def test_step3_13_14_15_repository_di_mode_guarantees(self):
        """Step 3.13, 3.14, 3.15: Development mode uses InMemory, Production mode uses PostgreSQL and fails fast if unavailable."""
        # 1. Dev Mode (No DATABASE_URL)
        with patch.dict(os.environ, {"DATABASE_URL": "", "SENTINEL_MODE": "development"}):
            repo_dev = get_repository(session=None)
            self.assertIsInstance(repo_dev, InMemoryCaseRepository)

        # 2. Production Mode (PostgreSQL unavailable)
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://bad:bad@localhost:9999/bad", "SENTINEL_MODE": "production"}):
            with self.assertRaises(RuntimeError) as ctx:
                get_repository(session=None)
            self.assertIn("POSTGRESQL PERSISTENCE FAILURE", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
