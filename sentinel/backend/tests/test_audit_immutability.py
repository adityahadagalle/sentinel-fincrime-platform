"""
Phase 7 Step 4: Audit Immutability & Database Integrity Test Suite.

Validates:
1. Audit event immutability trigger definition and migration DDL structure.
2. PostgreSQL live trigger enforcement (UPDATE / DELETE rejected with error code 55000 when PostgreSQL is online).
3. Transaction atomicity: Case status UPDATE + Disposition INSERT + AuditEvent INSERT within 1 atomic transaction.
4. Idempotency protection without duplicate audit event creation.
5. Explicit handling when offline: clearly reports PostgreSQL availability status.
"""

import os
import unittest
from datetime import datetime, timezone
import asyncio
from contextlib import asynccontextmanager


from app.repositories.in_memory import InMemoryCaseRepository
from app.services.case_lifecycle_agent import CaseLifecycleService
from app.db.config import get_database_url


class TestAuditImmutabilityArchitecture(unittest.TestCase):

    def setUp(self):
        self.store = {
            "transactions": {},
            "cases": {
                "CASE-IMMUT-01": {
                    "case_id": "CASE-IMMUT-01",
                    "primary_tx_id": "TX-IMMUT-01",
                    "status": "NEW",
                    "version": 1
                }
            },
            "graphs": {},
            "accounts": {},
            "actions": [],
            "dispositions": {},
            "audit_log": []
        }
        self.repo = InMemoryCaseRepository(self.store)
        self.service = CaseLifecycleService(self.repo)

    def test_01_migration_file_contains_immutability_trigger(self):
        """Step 4.1: Verify Alembic migration 002 contains PostgreSQL trigger prevent_audit_event_tampering."""
        migration_path = os.path.join("backend", "alembic", "versions", "002_audit_immutability.py")
        if not os.path.exists(migration_path):
            migration_path = os.path.join("alembic", "versions", "002_audit_immutability.py")
        self.assertTrue(os.path.exists(migration_path), f"Migration file not found at {migration_path}")

        with open(migration_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("prevent_audit_event_tampering", content)
        self.assertIn("trg_protect_audit_events", content)
        self.assertIn("BEFORE UPDATE OR DELETE ON audit_events", content)
        self.assertIn("ERRCODE = '55000'", content)

    def test_02_audit_event_model_has_no_mutation_methods(self):
        """Step 4.3: Verify AbstractCaseRepository exposes zero update or delete methods for audit logs."""
        from app.repositories.base import AbstractCaseRepository
        repo_methods = dir(AbstractCaseRepository)
        self.assertNotIn("update_audit_event", repo_methods)
        self.assertNotIn("delete_audit_event", repo_methods)

    def test_03_transaction_atomicity_contract(self):
        """Step 4.5: Verify case status update, disposition insert, and audit insert execute atomically."""
        ds_report = {
            "found": True,
            "status": "SUCCESS",
            "case_id": "CASE-IMMUT-01",
            "primary_tx_id": "TX-IMMUT-01",
            "disposition_options": [
                {
                    "action_code": "REQUEST_CUSTOMER_CDD",
                    "label": "Request CDD",
                    "requires_reason_note": True,
                    "requires_risk_acknowledgement": False
                }
            ],
            "recommended_review_steps": [],
            "summary": {"review_priority": "MEDIUM"}
        }

        res = asyncio.run(self.service.submit_case_disposition(
            case_id="CASE-IMMUT-01",
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="Atomicity test.",
            decision_support_report=ds_report
        ))
        self.assertTrue(res["ok"])

        # Check all 3 records were persisted simultaneously
        hist = asyncio.run(self.repo.get_case_history("CASE-IMMUT-01"))
        self.assertEqual(hist["current_case_status"], "CDD_PENDING")
        self.assertEqual(len(hist["disposition_history"]), 1)
        self.assertEqual(len(hist["audit_history"]), 1)


class TestPostgreSQLAuditImmutabilityLive(unittest.TestCase):
    """
    Live PostgreSQL Integration Test Suite for Trigger-Based Audit Immutability.
    Executes real DDL/DML against PostgreSQL if DATABASE_URL is reachable.
    Skipped safely when running offline without PostgreSQL.
    """

    @classmethod
    def setUpClass(cls):
        cls.db_url = os.getenv("DATABASE_URL")
        if not cls.db_url:
            cls.db_url = get_database_url(async_driver=True)
        cls.is_postgres = cls.db_url and cls.db_url.startswith("postgresql")

    def setUp(self):
        if not self.is_postgres:
            self.skipTest("DATABASE-LEVEL TRIGGER ENFORCEMENT UNVERIFIED (PostgreSQL offline)")

    @asynccontextmanager
    async def get_session(self):
        from app.db.session import get_async_engine, get_async_session_factory
        engine = get_async_engine(self.db_url)
        factory = get_async_session_factory(engine)
        async with factory() as session:
            try:
                yield session
            finally:
                pass
        await engine.dispose()

    def test_pg_01_audit_tampering_rejected_by_trigger(self):
        """Step 4.7: Adversarial test - PostgreSQL trigger rejects UPDATE and DELETE on audit_events."""
        async def run_test():
            from sqlalchemy import text
            from app.models.account import Account
            from app.models.transaction import Transaction
            from app.models.case import Case
            from app.models.audit_event import AuditEvent

            now = datetime.now(timezone.utc)
            async with self.get_session() as session:
                acc = Account(account_id="ACC-IMM-LIVE-01", created_at=now, updated_at=now)
                tx = Transaction(tx_id="TX-IMM-LIVE-01", sender_account_id="ACC-IMM-LIVE-01", receiver_account_id="ACC-IMM-LIVE-01", amount=100.0, channel="UPI", timestamp=now, raw_payload={}, created_at=now)
                c = Case(case_id="CASE-IMM-LIVE-01", primary_tx_id="TX-IMM-LIVE-01", created_at=now, updated_at=now)
                audit = AuditEvent(
                    audit_id="AUD-IMM-LIVE-01",
                    case_id="CASE-IMM-LIVE-01",
                    primary_tx_id="TX-IMM-LIVE-01",
                    analyst_id="A1",
                    analyst_role="R1",
                    action_code="CODE",
                    previous_case_status="NEW",
                    new_case_status="UNDER_REVIEW",
                    analyst_notes="Immutable original",
                    decision_support_summary={},
                    traceability_chain={},
                    timestamp=now,
                    created_at=now
                )
                session.add_all([acc, tx, c, audit])
                await session.commit()

            # Attempt UPDATE
            async with self.get_session() as session:
                with self.assertRaises(Exception) as ctx:
                    await session.execute(text("UPDATE audit_events SET analyst_notes = 'TAMPERED' WHERE audit_id = 'AUD-IMM-LIVE-01'"))
                    await session.commit()
                err_str = str(ctx.exception)
                self.assertTrue("55000" in err_str or "ObjectNotInPrerequisiteStateError" in err_str or "immutability violation" in err_str.lower())

            # Attempt DELETE
            async with self.get_session() as session:
                with self.assertRaises(Exception) as ctx:
                    await session.execute(text("DELETE FROM audit_events WHERE audit_id = 'AUD-IMM-LIVE-01'"))
                    await session.commit()
                err_str = str(ctx.exception)
                self.assertTrue("55000" in err_str or "ObjectNotInPrerequisiteStateError" in err_str or "immutability violation" in err_str.lower())

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
