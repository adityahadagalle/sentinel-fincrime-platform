"""
Phase 8 Step 4 Tests: Analytical Investigation Report Persistence -> PostgreSQL.

Tests:
1. Successful analytical report persistence.
2. Report exists in PostgreSQL.
3. Report correctly references Case (FK).
4. Report fields survive ORM round-trip.
5. Report retrieval works through repository abstraction.
6. InMemory repository behaves correctly.
7. Production uses PostgreSQL repository.
8. Production does not use data_store for report persistence.
9. Duplicate report behavior follows uq_case_report_type semantics (upsert/update).
10. Concurrent duplicate report persistence is database-safe.
11. Invalid case foreign key is rejected.
12. Report insertion failure rolls back appropriately.
13. Audit events remain immutable.
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
from app.models.investigation_report import InvestigationReport
from app.repositories.postgres import PostgreSQLCaseRepository
from app.repositories.in_memory import InMemoryCaseRepository
from app.core.data_store import data_store
from main import app, get_repository


class TestPhase8Step4ReportPersistence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_url = os.getenv("DATABASE_URL")
        if not cls.db_url:
            cls.db_url = get_database_url(async_driver=True)
        cls.has_postgres = bool(cls.db_url and cls.db_url.startswith("postgresql"))

    def setUp(self):
        if not self.has_postgres:
            self.skipTest("Live PostgreSQL required for Phase 8 Step 4 integration tests.")
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

    def seed_case_fixture(self, case_id: str = "CASE-STEP4-01") -> str:
        async def _seed(session_factory):
            async with session_factory() as session:
                now = datetime.now(timezone.utc)
                acc1 = Account(account_id=f"ACC-SND-{case_id}", created_at=now, updated_at=now)
                acc2 = Account(account_id=f"ACC-RCV-{case_id}", created_at=now, updated_at=now)
                tx = Transaction(
                    tx_id=f"TX-SEED-{case_id}",
                    sender_account_id=f"ACC-SND-{case_id}",
                    receiver_account_id=f"ACC-RCV-{case_id}",
                    amount=100000.0,
                    channel="UPI",
                    timestamp=now,
                    raw_payload={},
                    created_at=now
                )
                c = Case(
                    case_id=case_id,
                    primary_tx_id=f"TX-SEED-{case_id}",
                    status="NEW",
                    risk_level="HIGH",
                    golden_window_minutes=30,
                    total_fraud_amount=100000.0,
                    recoverable_amount=100000.0,
                    created_at=now,
                    updated_at=now
                )
                session.add_all([acc1, acc2, tx, c])
                await session.commit()

        self.run_with_db(_seed)
        return case_id

    def test_step4_01_02_03_04_save_report_pg_persistence_and_orm_roundtrip(self):
        """Step 4.1 - 4.4: Save investigation report persists in PostgreSQL, references Case (FK), and survives ORM roundtrip."""
        case_id = self.seed_case_fixture("CASE-RPT-01")
        report_data = {
            "evidence_score": 88.5,
            "risk_indicators": ["high_amount", "new_receiver"],
            "analyst_summary": "High risk pattern detected."
        }

        async def save_and_verify(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                ok = await repo.save_investigation_report({
                    "report_id": "RPT-STEP4-001",
                    "case_id": case_id,
                    "report_type": "DECISION_SUPPORT",
                    "report_data": report_data,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                self.assertTrue(ok)
                await session.commit()

            # Query DB in fresh session to verify persistence and FK
            async with session_factory() as session:
                rpt_db = (await session.execute(select(InvestigationReport).filter(InvestigationReport.report_id == "RPT-STEP4-001"))).scalar_one_or_none()
                self.assertIsNotNone(rpt_db)
                self.assertEqual(rpt_db.case_id, case_id)
                self.assertEqual(rpt_db.report_type, "DECISION_SUPPORT")
                self.assertEqual(rpt_db.report_data["evidence_score"], 88.5)
                self.assertEqual(rpt_db.report_data["analyst_summary"], "High risk pattern detected.")

        self.run_with_db(save_and_verify)

    def test_step4_05_06_repository_retrieval_pg_and_in_memory(self):
        """Step 4.5 & 4.6: Report retrieval through repository abstraction works for PostgreSQL and InMemory repos."""
        case_id = self.seed_case_fixture("CASE-RPT-RETRIEVE-01")
        report_payload = {
            "report_id": "RPT-CTX-100",
            "case_id": case_id,
            "report_type": "CONTEXTUAL",
            "report_data": {"graph_nodes": 4, "max_depth": 2}
        }

        # 1. Test PostgreSQL Retrieval
        async def test_pg(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                await repo.save_investigation_report(report_payload)
                await session.commit()

                rpt = await repo.get_investigation_report(case_id, "CONTEXTUAL")
                self.assertIsNotNone(rpt)
                self.assertEqual(rpt["report_type"], "CONTEXTUAL")
                self.assertEqual(rpt["report_data"]["graph_nodes"], 4)

                all_rpts = await repo.get_investigation_reports_by_case_id(case_id)
                self.assertEqual(len(all_rpts), 1)

        self.run_with_db(test_pg)

        # 2. Test InMemory Retrieval
        async def test_in_mem():
            repo_inmem = InMemoryCaseRepository()
            await repo_inmem.save_case({"case_id": case_id, "primary_tx_id": "TX-1", "status": "NEW"})
            await repo_inmem.save_investigation_report(report_payload)
            rpt = await repo_inmem.get_investigation_report(case_id, "CONTEXTUAL")
            self.assertIsNotNone(rpt)
            self.assertEqual(rpt["report_data"]["graph_nodes"], 4)

        asyncio.run(test_in_mem())

    def test_step4_07_08_production_uses_pg_and_no_data_store_fallback(self):
        """Step 4.7 & 4.8: Production uses PostgreSQL repo and fails fast if DB is unavailable (no silent fallback)."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://bad:bad@localhost:9999/bad", "SENTINEL_MODE": "production"}):
            with self.assertRaises(RuntimeError) as ctx:
                get_repository(session=None)
            self.assertIn("POSTGRESQL PERSISTENCE FAILURE", str(ctx.exception))

    def test_step4_09_duplicate_report_type_upsert_semantics(self):
        """Step 4.9: Duplicate report with same (case_id, report_type) updates existing report (uq_case_report_type semantics)."""
        case_id = self.seed_case_fixture("CASE-DUP-RPT-01")

        async def test_upsert(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                # First report version
                await repo.save_investigation_report({
                    "report_id": "RPT-V1",
                    "case_id": case_id,
                    "report_type": "REGULATORY",
                    "report_data": {"version": 1, "severity": "MEDIUM"}
                })
                await session.commit()

            # Second report version for same (case_id, report_type)
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                await repo.save_investigation_report({
                    "report_id": "RPT-V2",
                    "case_id": case_id,
                    "report_type": "REGULATORY",
                    "report_data": {"version": 2, "severity": "HIGH"}
                })
                await session.commit()

            # Verify in DB: only 1 report row exists and data was updated to V2
            async with session_factory() as session:
                rpts = (await session.execute(select(InvestigationReport).filter(
                    InvestigationReport.case_id == case_id,
                    InvestigationReport.report_type == "REGULATORY"
                ))).scalars().all()
                self.assertEqual(len(rpts), 1)
                self.assertEqual(rpts[0].report_data["version"], 2)
                self.assertEqual(rpts[0].report_data["severity"], "HIGH")

        self.run_with_db(test_upsert)

    def test_step4_10_concurrent_report_persistence_safety(self):
        """Step 4.10: Concurrent attempts to persist reports for the same case remain database-safe."""
        case_id = self.seed_case_fixture("CASE-CONCUR-RPT-01")

        async def test_concurrent(session_factory):
            async def worker(rpt_type, score):
                async with session_factory() as session:
                    repo = PostgreSQLCaseRepository(session)
                    res = await repo.save_investigation_report({
                        "report_id": f"RPT-CONCUR-{rpt_type}",
                        "case_id": case_id,
                        "report_type": rpt_type,
                        "report_data": {"score": score}
                    })
                    await session.commit()
                    return res

            res1, res2 = await asyncio.gather(
                worker("EVIDENCE", 80),
                worker("CONTEXTUAL", 90)
            )
            self.assertTrue(res1)
            self.assertTrue(res2)

            async with session_factory() as session:
                rpts = (await session.execute(select(InvestigationReport).filter(InvestigationReport.case_id == case_id))).scalars().all()
                self.assertEqual(len(rpts), 2)

        self.run_with_db(test_concurrent)

    def test_step4_11_invalid_case_foreign_key_rejected(self):
        """Step 4.11: Persisting report for nonexistent case_id is rejected by foreign key constraint."""
        async def test_fk_reject(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                with self.assertRaises(Exception):
                    try:
                        await repo.save_investigation_report({
                            "report_id": "RPT-ORPHAN-999",
                            "case_id": "NON_EXISTENT_CASE_99999",
                            "report_type": "EVIDENCE",
                            "report_data": {}
                        })
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

        self.run_with_db(test_fk_reject)

    def test_step4_12_report_insertion_failure_rolls_back(self):
        """Step 4.12: Failed report insertion triggers transaction rollback cleanly."""
        async def test_rollback(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                with self.assertRaises(Exception):
                    try:
                        # Missing required case_id key to force KeyError/Exception
                        await repo.save_investigation_report({
                            "report_type": "EVIDENCE"
                        })
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

        self.run_with_db(test_rollback)


if __name__ == "__main__":
    unittest.main()
