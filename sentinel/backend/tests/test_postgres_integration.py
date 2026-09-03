"""
Real PostgreSQL Integration & Migration Test Suite for SENTINEL (Phase 7 Step 5).

This suite tests the real PostgreSQL database layer:
1. Alembic migrations (001_initial_schema -> 002_audit_immutability).
2. Alembic migration rollback (downgrade -> upgrade).
3. ORM round-trip persistence (Account, Transaction, Case, InvestigationReport, Disposition, AuditEvent).
4. Real database-level audit immutability trigger enforcement (UPDATE and DELETE on audit_events rejected with SQLSTATE 55000).
5. Append-only INSERT behavior on audit_events.
6. Transaction atomicity & rollback on failure.
7. SELECT FOR UPDATE pessimistic row locking execution.
8. Idempotency handling & UNIQUE constraint enforcement.
9. Foreign Key RESTRICT integrity.
10. Case status CHECK constraint enforcement.
"""

import os
import unittest
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError, DBAPIError

from app.db.config import get_database_url
from app.db.session import get_async_engine, get_async_session_factory
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.case import Case
from app.models.investigation_report import InvestigationReport
from app.models.disposition import Disposition
from app.models.audit_event import AuditEvent
from app.repositories.postgres import PostgreSQLCaseRepository
from alembic.config import Config
from alembic import command


class TestPostgreSQLRealIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_url = os.getenv("DATABASE_URL")
        if not cls.db_url:
            cls.db_url = get_database_url(async_driver=True)
        cls.has_postgres = bool(cls.db_url and cls.db_url.startswith("postgresql"))

    def setUp(self):
        if not self.has_postgres:
            self.skipTest("POSTGRESQL INTEGRATION UNAVAILABLE (No live PostgreSQL DATABASE_URL configured)")
        self.clean_db()

    def tearDown(self):
        if self.has_postgres:
            self.clean_db()

    def run_async(self, coro):
        return asyncio.run(coro)

    @asynccontextmanager
    async def get_session(self):
        engine = get_async_engine(self.db_url)
        factory = get_async_session_factory(engine)
        async with factory() as session:
            try:
                yield session
            finally:
                pass
        await engine.dispose()

    def clean_db(self):
        async def _clean():
            async with self.get_session() as session:
                await session.execute(text("TRUNCATE audit_events, dispositions, investigation_reports, cases, transactions, accounts CASCADE;"))
                await session.commit()
        self.run_async(_clean())

    def test_pg_01_alembic_migration_upgrade_and_downgrade(self):
        """Step 5.2 & 5.11: Alembic migration upgrade head and downgrade round-trip against real PostgreSQL."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ini_path = os.path.join(backend_dir, "alembic.ini")
        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")

        async def verify_head():
            async with self.get_session() as session:
                res = await session.execute(text("SELECT version_num FROM alembic_version"))
                rev = res.scalar_one_or_none()
                self.assertEqual(rev, "004_active_inv_unique_idx")



        self.run_async(verify_head())


    def test_pg_02_orm_round_trip(self):
        """Step 5.3: Complete ORM entity round-trip persistence (INSERT -> COMMIT -> SELECT)."""
        async def run_test():
            async with self.get_session() as session:
                now = datetime.now(timezone.utc)
                acc1 = Account(account_id="ACC-RT-01", kyc_status="VERIFIED", risk_score=15.0, created_at=now, updated_at=now)
                acc2 = Account(account_id="ACC-RT-02", kyc_status="VERIFIED", risk_score=25.0, created_at=now, updated_at=now)
                session.add_all([acc1, acc2])

                tx = Transaction(
                    tx_id="TX-RT-01",
                    sender_account_id="ACC-RT-01",
                    receiver_account_id="ACC-RT-02",
                    amount=50000.00,
                    currency="INR",
                    channel="UPI",
                    timestamp=now,
                    raw_payload={"test": "payload"},
                    created_at=now
                )
                session.add(tx)

                c = Case(
                    case_id="CASE-RT-01",
                    primary_tx_id="TX-RT-01",
                    status="NEW",
                    risk_level="HIGH",
                    golden_window_minutes=30,
                    total_fraud_amount=50000.00,
                    recoverable_amount=50000.00,
                    created_at=now,
                    updated_at=now
                )
                session.add(c)

                rpt = InvestigationReport(
                    report_id="RPT-RT-01",
                    case_id="CASE-RT-01",
                    report_type="EXECUTIVE_SUMMARY",
                    report_data={"summary": "High risk round trip test"},
                    created_at=now
                )
                session.add(rpt)

                disp = Disposition(
                    disposition_id="DISP-RT-01",
                    case_id="CASE-RT-01",
                    primary_tx_id="TX-RT-01",
                    action_code="ESCALATE_TO_LEGAL",
                    label="Escalate",
                    analyst_notes="ORM round trip test notes",
                    analyst_id="ANALYST-RT",
                    analyst_role="SENIOR_ANALYST",
                    risk_acknowledged=True,
                    previous_case_status="NEW",
                    new_case_status="ESCALATED",
                    idempotency_key="IDEM-RT-01",
                    timestamp=now,
                    created_at=now
                )
                session.add(disp)

                audit = AuditEvent(
                    audit_id="AUD-RT-01",
                    event_type="CASE_DISPOSITION_MUTATION",
                    case_id="CASE-RT-01",
                    primary_tx_id="TX-RT-01",
                    analyst_id="ANALYST-RT",
                    analyst_role="SENIOR_ANALYST",
                    action_code="ESCALATE_TO_LEGAL",
                    previous_case_status="NEW",
                    new_case_status="ESCALATED",
                    analyst_notes="ORM round trip test notes",
                    risk_acknowledged=True,
                    decision_support_summary={"score": 85},
                    traceability_chain={"step": 1},
                    timestamp=now,
                    created_at=now
                )
                session.add(audit)
                await session.commit()

            async with self.get_session() as session:
                c_fetched = (await session.execute(select(Case).filter(Case.case_id == "CASE-RT-01"))).scalar_one_or_none()
                self.assertIsNotNone(c_fetched)
                self.assertEqual(c_fetched.status, "NEW")
                self.assertEqual(c_fetched.risk_level, "HIGH")

                audit_fetched = (await session.execute(select(AuditEvent).filter(AuditEvent.audit_id == "AUD-RT-01"))).scalar_one_or_none()
                self.assertIsNotNone(audit_fetched)
                self.assertEqual(audit_fetched.action_code, "ESCALATE_TO_LEGAL")

        self.run_async(run_test())

    def test_pg_03_audit_events_immutability_trigger_update_rejected(self):
        """Step 5.4: PostgreSQL trigger rejects UPDATE on audit_events with SQLSTATE 55000."""
        async def run_test():
            async with self.get_session() as session:
                now = datetime.now(timezone.utc)
                acc = Account(account_id="ACC-TRIG-01", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-TRIG-01", sender_account_id="ACC-TRIG-01", receiver_account_id="ACC-TRIG-01", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-TRIG-01", primary_tx_id="TX-TRIG-01", created_at=now, updated_at=now)
                audit = AuditEvent(
                    audit_id="AUD-TRIG-01",
                    case_id="CASE-TRIG-01",
                    primary_tx_id="TX-TRIG-01",
                    analyst_id="A1",
                    analyst_role="R1",
                    action_code="CODE",
                    previous_case_status="NEW",
                    new_case_status="UNDER_REVIEW",
                    analyst_notes="Original",
                    decision_support_summary={},
                    traceability_chain={},
                    timestamp=now,
                    created_at=now
                )
                session.add_all([acc, tx, c, audit])
                await session.commit()

            async with self.get_session() as session:
                with self.assertRaises(Exception) as ctx:
                    try:
                        await session.execute(text("UPDATE audit_events SET analyst_notes = 'Tampered' WHERE audit_id = 'AUD-TRIG-01'"))
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
                err_str = str(ctx.exception)
                self.assertTrue("55000" in err_str or "ObjectNotInPrerequisiteStateError" in err_str or "immutability violation" in err_str.lower(), f"Unexpected error: {err_str}")

            async with self.get_session() as session:
                audit_obj = (await session.execute(select(AuditEvent).filter(AuditEvent.audit_id == "AUD-TRIG-01"))).scalar_one()
                self.assertEqual(audit_obj.analyst_notes, "Original")

        self.run_async(run_test())

    def test_pg_04_audit_events_immutability_trigger_delete_rejected(self):
        """Step 5.4: PostgreSQL trigger rejects DELETE on audit_events with SQLSTATE 55000."""
        async def run_test():
            async with self.get_session() as session:
                now = datetime.now(timezone.utc)
                acc = Account(account_id="ACC-TRIG-02", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-TRIG-02", sender_account_id="ACC-TRIG-02", receiver_account_id="ACC-TRIG-02", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-TRIG-02", primary_tx_id="TX-TRIG-02", created_at=now, updated_at=now)
                audit = AuditEvent(
                    audit_id="AUD-TRIG-02",
                    case_id="CASE-TRIG-02",
                    primary_tx_id="TX-TRIG-02",
                    analyst_id="A1",
                    analyst_role="R1",
                    action_code="CODE",
                    previous_case_status="NEW",
                    new_case_status="UNDER_REVIEW",
                    analyst_notes="Untouchable",
                    decision_support_summary={},
                    traceability_chain={},
                    timestamp=now,
                    created_at=now
                )
                session.add_all([acc, tx, c, audit])
                await session.commit()

            async with self.get_session() as session:
                with self.assertRaises(Exception) as ctx:
                    try:
                        await session.execute(text("DELETE FROM audit_events WHERE audit_id = 'AUD-TRIG-02'"))
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
                err_str = str(ctx.exception)
                self.assertTrue("55000" in err_str or "ObjectNotInPrerequisiteStateError" in err_str or "immutability violation" in err_str.lower(), f"Unexpected error: {err_str}")

            async with self.get_session() as session:
                audit_obj = (await session.execute(select(AuditEvent).filter(AuditEvent.audit_id == "AUD-TRIG-02"))).scalar_one_or_none()
                self.assertIsNotNone(audit_obj)
                self.assertEqual(audit_obj.analyst_notes, "Untouchable")

        self.run_async(run_test())

    def test_pg_05_audit_events_append_only_insert(self):
        """Step 5.5: Audit history permits append-only INSERT while blocking UPDATE/DELETE."""
        async def run_test():
            async with self.get_session() as session:
                now = datetime.now(timezone.utc)
                acc = Account(account_id="ACC-APP-01", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-APP-01", sender_account_id="ACC-APP-01", receiver_account_id="ACC-APP-01", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-APP-01", primary_tx_id="TX-APP-01", created_at=now, updated_at=now)
                audit1 = AuditEvent(
                    audit_id="AUD-APP-01",
                    case_id="CASE-APP-01",
                    primary_tx_id="TX-APP-01",
                    analyst_id="A1",
                    analyst_role="R1",
                    action_code="CODE1",
                    previous_case_status="NEW",
                    new_case_status="UNDER_REVIEW",
                    analyst_notes="First Audit",
                    decision_support_summary={},
                    traceability_chain={},
                    timestamp=now,
                    created_at=now
                )
                session.add_all([acc, tx, c, audit1])
                await session.commit()

            async with self.get_session() as session:
                later = datetime.now(timezone.utc) + timedelta(seconds=1)
                audit2 = AuditEvent(
                    audit_id="AUD-APP-02",
                    case_id="CASE-APP-01",
                    primary_tx_id="TX-APP-01",
                    analyst_id="A1",
                    analyst_role="R1",
                    action_code="CODE2",
                    previous_case_status="UNDER_REVIEW",
                    new_case_status="ESCALATED",
                    analyst_notes="Second Audit",
                    decision_support_summary={},
                    traceability_chain={},
                    timestamp=later,
                    created_at=later
                )
                session.add(audit2)
                await session.commit()

            async with self.get_session() as session:
                repo = PostgreSQLCaseRepository(session)
                hist = await repo.get_case_history("CASE-APP-01")
                self.assertEqual(len(hist["audit_history"]), 2)
                self.assertEqual(hist["audit_history"][0]["audit_id"], "AUD-APP-01")
                self.assertEqual(hist["audit_history"][1]["audit_id"], "AUD-APP-02")

        self.run_async(run_test())

    def test_pg_06_transaction_atomicity_and_rollback(self):
        """Step 5.6: Case update + Disposition insert + Audit insert roll back atomically on failure."""
        async def run_test():
            async with self.get_session() as session:
                now = datetime.now(timezone.utc)
                acc = Account(account_id="ACC-ATOM-01", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-ATOM-01", sender_account_id="ACC-ATOM-01", receiver_account_id="ACC-ATOM-01", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-ATOM-01", primary_tx_id="TX-ATOM-01", status="NEW", created_at=now, updated_at=now)
                session.add_all([acc, tx, c])
                await session.commit()

            async with self.get_session() as session:
                repo = PostgreSQLCaseRepository(session)
                disp_rec = {
                    "disposition_id": "DISP-ATOM-01",
                    "primary_tx_id": "TX-ATOM-01",
                    "action_code": "TEST",
                    "label": "Test",
                    "analyst_notes": "Test",
                    "analyst_id": "A1",
                    "analyst_role": "R1",
                    "previous_case_status": "NEW",
                    "idempotency_key": "IDEM-ATOM-01"
                }
                audit_rec = {
                    "audit_id": "AUD-ATOM-01",
                    "primary_tx_id": "TX-ATOM-01",
                    "analyst_id": "A1",
                    "analyst_role": "R1",
                    "action_code": "TEST",
                    "previous_case_status": "NEW",
                    "analyst_notes": "Test"
                }

                with self.assertRaises((IntegrityError, Exception)):
                    await repo.save_disposition_and_audit(
                        case_id="CASE-ATOM-01",
                        new_status="INVALID_STATUS_TRIGGER_FAIL",
                        disposition_record=disp_rec,
                        audit_event_record=audit_rec
                    )

            async with self.get_session() as session:
                repo = PostgreSQLCaseRepository(session)
                c_dict = await repo.get_case_by_id("CASE-ATOM-01")
                self.assertEqual(c_dict["status"], "NEW")
                hist = await repo.get_case_history("CASE-ATOM-01")
                self.assertEqual(len(hist["disposition_history"]), 0)
                self.assertEqual(len(hist["audit_history"]), 0)

        self.run_async(run_test())

    def test_pg_07_select_for_update_row_locking(self):
        """Step 5.7: SELECT FOR UPDATE pessimistic row locking execution across concurrent sessions."""
        async def run_test():
            now = datetime.now(timezone.utc)
            async with self.get_session() as s_setup:
                acc = Account(account_id="ACC-LOCK-01", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-LOCK-01", sender_account_id="ACC-LOCK-01", receiver_account_id="ACC-LOCK-01", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-LOCK-01", primary_tx_id="TX-LOCK-01", status="NEW", created_at=now, updated_at=now)
                s_setup.add_all([acc, tx, c])
                await s_setup.commit()

            lock_acquired_b = False
            lock_released_a = False

            async def session_a_worker():
                nonlocal lock_released_a
                async with self.get_session() as session_a:
                    repo_a = PostgreSQLCaseRepository(session_a)
                    c_locked = await repo_a.get_case_for_update("CASE-LOCK-01")
                    self.assertIsNotNone(c_locked)
                    await asyncio.sleep(0.5)
                    lock_released_a = True
                    await session_a.commit()

            async def session_b_worker():
                nonlocal lock_acquired_b
                await asyncio.sleep(0.1)
                async with self.get_session() as session_b:
                    repo_b = PostgreSQLCaseRepository(session_b)
                    c_locked_b = await repo_b.get_case_for_update("CASE-LOCK-01")
                    self.assertTrue(lock_released_a, "Session B acquired lock before Session A released it!")
                    lock_acquired_b = True
                    await session_b.commit()

            await asyncio.gather(session_a_worker(), session_b_worker())
            self.assertTrue(lock_acquired_b)

        self.run_async(run_test())

    def test_pg_08_idempotency_unique_constraint(self):
        """Step 5.8: Database UNIQUE constraint on idempotency_key prevents duplicate disposition writes."""
        async def run_test():
            now = datetime.now(timezone.utc)
            async with self.get_session() as session:
                acc = Account(account_id="ACC-IDEM-01", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-IDEM-01", sender_account_id="ACC-IDEM-01", receiver_account_id="ACC-IDEM-01", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-IDEM-01", primary_tx_id="TX-IDEM-01", status="NEW", created_at=now, updated_at=now)
                disp1 = Disposition(
                    disposition_id="DISP-IDEM-01",
                    case_id="CASE-IDEM-01",
                    primary_tx_id="TX-IDEM-01",
                    action_code="APPROVE",
                    label="Approve",
                    analyst_notes="Disp 1",
                    analyst_id="A1",
                    analyst_role="R1",
                    previous_case_status="NEW",
                    new_case_status="RESOLVED_APPROVED",
                    idempotency_key="IDEM-UNIQUE-KEY-999",
                    timestamp=now,
                    created_at=now
                )
                session.add_all([acc, tx, c, disp1])
                await session.commit()

            async with self.get_session() as session:
                disp2 = Disposition(
                    disposition_id="DISP-IDEM-02",
                    case_id="CASE-IDEM-01",
                    primary_tx_id="TX-IDEM-01",
                    action_code="APPROVE",
                    label="Approve",
                    analyst_notes="Disp 2 duplicate",
                    analyst_id="A1",
                    analyst_role="R1",
                    previous_case_status="NEW",
                    new_case_status="RESOLVED_APPROVED",
                    idempotency_key="IDEM-UNIQUE-KEY-999",
                    timestamp=now,
                    created_at=now
                )
                session.add(disp2)
                with self.assertRaises(IntegrityError):
                    try:
                        await session.flush()
                    except Exception:
                        await session.rollback()
                        raise

        self.run_async(run_test())

    def test_pg_09_foreign_key_restrict_integrity(self):
        """Step 5.9: Foreign key RESTRICT constraints prevent orphan child records and cascade deletion of compliance logs."""
        async def run_test():
            now = datetime.now(timezone.utc)
            async with self.get_session() as session:
                acc1 = Account(account_id="ACC-FK-01", created_at=now, updated_at=now)
                acc2 = Account(account_id="ACC-FK-02", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-FK-01", sender_account_id="ACC-FK-01", receiver_account_id="ACC-FK-02", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-FK-01", primary_tx_id="TX-FK-01", created_at=now, updated_at=now)
                session.add_all([acc1, acc2, tx, c])
                await session.commit()

            async with self.get_session() as session:
                with self.assertRaises(IntegrityError):
                    try:
                        await session.execute(text("DELETE FROM accounts WHERE account_id = 'ACC-FK-01'"))
                        await session.flush()
                    except Exception:
                        await session.rollback()
                        raise

        self.run_async(run_test())

    def test_pg_10_case_status_check_constraint(self):
        """Step 5.10: PostgreSQL CHECK constraint chk_case_status rejects invalid lifecycle states."""
        async def run_test():
            now = datetime.now(timezone.utc)
            async with self.get_session() as session:
                acc = Account(account_id="ACC-CHK-01", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-CHK-01", sender_account_id="ACC-CHK-01", receiver_account_id="ACC-CHK-01", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c_invalid = Case(case_id="CASE-CHK-01", primary_tx_id="TX-CHK-01", status="FORBIDDEN_STATE", created_at=now, updated_at=now)
                session.add_all([acc, tx, c_invalid])
                with self.assertRaises(IntegrityError) as ctx:
                    try:
                        await session.flush()
                    except Exception:
                        await session.rollback()
                        raise
                self.assertIn("chk_case_status", str(ctx.exception))

        self.run_async(run_test())


if __name__ == "__main__":
    unittest.main()
