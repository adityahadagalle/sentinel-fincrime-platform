"""
Phase 8 Step 2 Tests: Asynchronous Case Lifecycle & Disposition API Endpoint Integration.

Tests:
1. Successful disposition through HTTP API.
2. Case status transition persisted in PostgreSQL.
3. Disposition persisted in PostgreSQL.
4. Audit event persisted in PostgreSQL.
5. Idempotent repeated request returns cached response.
6. Repeated idempotency request does not create duplicate audit events.
7. Invalid transition rejected and leaves database unchanged.
8. Unauthorized analyst/role rejected.
9. Forbidden autonomous action codes remain rejected.
10. Transaction rollback leaves case/disposition/audit unchanged.
11. GET history returns persisted PostgreSQL history.
12. History ordering is deterministic.
13. Concurrent disposition attempts respect SELECT FOR UPDATE.
"""

import os
import unittest
import asyncio
from datetime import datetime, timezone
from sqlalchemy import text, select
from fastapi.testclient import TestClient

from app.db.config import get_database_url
from app.db.session import get_async_engine, get_async_session_factory
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.case import Case
from app.models.disposition import Disposition
from app.models.audit_event import AuditEvent
from app.repositories.postgres import PostgreSQLCaseRepository
from app.services.case_lifecycle_agent import CaseLifecycleService
from app.services.analyst_agent import generate_case_analyst_decision_support
from app.core.data_store import data_store
from main import app


class TestPhase8Step2AsyncEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_url = os.getenv("DATABASE_URL")
        if not cls.db_url:
            cls.db_url = get_database_url(async_driver=True)
        cls.has_postgres = bool(cls.db_url and cls.db_url.startswith("postgresql"))

    def setUp(self):
        if not self.has_postgres:
            self.skipTest("Live PostgreSQL required for Phase 8 Step 2 integration tests.")
        self.client = TestClient(app)
        self.clean_db()

    def tearDown(self):
        if self.has_postgres:
            self.clean_db()

    def run_with_db(self, async_fn):
        """Helper executing an async function with a single-loop engine & session factory."""
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

    def seed_case_fixture(self, case_id: str = "CASE-STEP2-01", status: str = "NEW") -> str:
        async def _seed(session_factory):
            async with session_factory() as session:
                now = datetime.now(timezone.utc)
                acc1 = Account(account_id=f"ACC-SND-{case_id}", created_at=now, updated_at=now)
                acc2 = Account(account_id=f"ACC-RCV-{case_id}", created_at=now, updated_at=now)
                tx = Transaction(
                    tx_id=f"TX-SEED-{case_id}",
                    sender_account_id=f"ACC-SND-{case_id}",
                    receiver_account_id=f"ACC-RCV-{case_id}",
                    amount=150000.0,
                    channel="UPI",
                    timestamp=now,
                    raw_payload={},
                    created_at=now
                )
                c = Case(
                    case_id=case_id,
                    primary_tx_id=f"TX-SEED-{case_id}",
                    status=status,
                    risk_level="HIGH",
                    golden_window_minutes=30,
                    total_fraud_amount=150000.0,
                    recoverable_amount=150000.0,
                    created_at=now,
                    updated_at=now
                )
                session.add_all([acc1, acc2, tx, c])
                await session.commit()

        self.run_with_db(_seed)

        # Also seed in data_store for decision support lookups
        data_store["cases"][case_id] = {
            "case_id": case_id,
            "primary_tx_id": f"TX-SEED-{case_id}",
            "status": status,
            "risk_level": 85.0,
            "golden_window_minutes": 30,
            "total_fraud_amount": 150000.0,
            "recoverable_amount": 150000.0,
            "transactions": [f"TX-SEED-{case_id}"]
        }
        data_store["transactions"][f"TX-SEED-{case_id}"] = {
            "tx_id": f"TX-SEED-{case_id}",
            "case_id": case_id,
            "sender_account": f"ACC-SND-{case_id}",
            "receiver_account": f"ACC-RCV-{case_id}",
            "amount": 150000.0,
            "risk_score": 85.0,
            "channel": "UPI"
        }
        return case_id

    def test_step2_01_successful_disposition_http_api(self):
        """Step 2.1: POST /cases/{case_id}/disposition returns HTTP 200, status SUCCESS, and new_case_status."""
        case_id = self.seed_case_fixture("CASE-HTTP-01", "NEW")

        res = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "ESCALATE_SENIOR_COMPLIANCE",
            "analyst_notes": "HTTP API step 2 test notes.",
            "analyst_id": "ANALYST-HTTP-1",
            "analyst_role": "SENIOR_COMPLIANCE_OFFICER",
            "risk_acknowledged": True
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["previous_case_status"], "NEW")
        self.assertEqual(data["new_case_status"], "ESCALATED")

    def test_step2_02_03_04_persisted_in_postgresql(self):
        """Step 2.2, 2.3, 2.4: Case status transition, Disposition, and Audit event are persisted in PostgreSQL."""
        case_id = self.seed_case_fixture("CASE-PG-PERSIST-01", "NEW")

        self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "analyst_notes": "CDD request rationale.",
            "analyst_id": "ANALYST-CDD",
            "analyst_role": "COMPLIANCE_ANALYST"
        })

        async def verify_pg(session_factory):
            async with session_factory() as session:
                # 1. Verify case status in DB
                c_db = (await session.execute(select(Case).filter(Case.case_id == case_id))).scalar_one()
                self.assertEqual(c_db.status, "CDD_PENDING")

                # 2. Verify disposition in DB
                disp_db = (await session.execute(select(Disposition).filter(Disposition.case_id == case_id))).scalar_one()
                self.assertEqual(disp_db.action_code, "REQUEST_CUSTOMER_CDD")
                self.assertEqual(disp_db.analyst_id, "ANALYST-CDD")

                # 3. Verify audit event in DB
                audit_db = (await session.execute(select(AuditEvent).filter(AuditEvent.case_id == case_id))).scalar_one()
                self.assertEqual(audit_db.action_code, "REQUEST_CUSTOMER_CDD")
                self.assertEqual(audit_db.new_case_status, "CDD_PENDING")

        self.run_with_db(verify_pg)

    def test_step2_05_06_idempotent_repeated_request(self):
        """Step 2.5 & 2.6: Repeated request with idempotency_key returns cached response without duplicate audit events."""
        case_id = self.seed_case_fixture("CASE-IDEM-01", "NEW")
        idem_key = "IDEM-STEP2-KEY-100"

        payload = {
            "case_id": case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "First attempt",
            "idempotency_key": idem_key
        }

        # First POST
        res1 = self.client.post(f"/cases/{case_id}/disposition", json=payload)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1["ok"])

        # Second POST with same idempotency_key
        res2 = self.client.post(f"/cases/{case_id}/disposition", json=payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2["ok"])
        self.assertTrue(data2.get("idempotent_cached_response", False))

        # Verify only 1 disposition and 1 audit event exist in PostgreSQL
        async def verify_single_event(session_factory):
            async with session_factory() as session:
                disps = (await session.execute(select(Disposition).filter(Disposition.case_id == case_id))).scalars().all()
                audits = (await session.execute(select(AuditEvent).filter(AuditEvent.case_id == case_id))).scalars().all()
                self.assertEqual(len(disps), 1)
                self.assertEqual(len(audits), 1)

        self.run_with_db(verify_single_event)

    def test_step2_07_invalid_transition_rejected(self):
        """Step 2.7: Invalid lifecycle transition is rejected and leaves database unchanged."""
        # RESOLVED_APPROVED is a terminal state
        case_id = self.seed_case_fixture("CASE-TERM-01", "RESOLVED_APPROVED")

        res = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "analyst_notes": "Attempt transition from terminal state"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

        # Verify PostgreSQL database remains unchanged
        async def verify_unchanged(session_factory):
            async with session_factory() as session:
                c_db = (await session.execute(select(Case).filter(Case.case_id == case_id))).scalar_one()
                self.assertEqual(c_db.status, "RESOLVED_APPROVED")
                disps = (await session.execute(select(Disposition).filter(Disposition.case_id == case_id))).scalars().all()
                self.assertEqual(len(disps), 0)

        self.run_with_db(verify_unchanged)

    def test_step2_08_unauthorized_analyst_role_rejected(self):
        """Step 2.8: Unauthorized analyst_role is rejected and leaves database unchanged."""
        case_id = self.seed_case_fixture("CASE-UNAUTH-01", "NEW")

        res = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Unauthorized attempt",
            "analyst_role": "UNAUTHORIZED_INTERN"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_step2_09_forbidden_autonomous_actions_rejected(self):
        """Step 2.9: Forbidden autonomous action codes (FREEZE, BLOCK, FILE_STR, CLOSE_ACCOUNT, REJECT_TRANSACTION) are rejected."""
        case_id = self.seed_case_fixture("CASE-FORBIDDEN-01", "NEW")

        for code in ["FREEZE", "BLOCK", "FILE_STR", "CLOSE_ACCOUNT", "REJECT_TRANSACTION"]:
            res = self.client.post(f"/cases/{case_id}/disposition", json={
                "case_id": case_id,
                "action_code": code,
                "analyst_notes": f"Attempt forbidden action {code}"
            })
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertFalse(data["ok"])
            self.assertEqual(data["status"], "INVALID_INPUT")
            self.assertIn("Forbidden action code", data["error"])

    def test_step2_10_transaction_rollback_integrity(self):
        """Step 2.10: Transaction failure triggers rollback, leaving case, dispositions, and audit events unchanged."""
        case_id = self.seed_case_fixture("CASE-ROLLBACK-01", "NEW")

        async def run_failing_disposition(session_factory):
            async with session_factory() as session:
                repo = PostgreSQLCaseRepository(session)
                with self.assertRaises(Exception):
                    try:
                        await repo.save_disposition_and_audit(
                            case_id=case_id,
                            new_status="INVALID_STATUS_FAIL",
                            disposition_record={"disposition_id": "D1", "action_code": "TEST"},
                            audit_event_record={"audit_id": "A1", "action_code": "TEST"}
                        )
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

        self.run_with_db(run_failing_disposition)

        # Verify DB remained untouched
        async def verify_clean(session_factory):
            async with session_factory() as session:
                c_db = (await session.execute(select(Case).filter(Case.case_id == case_id))).scalar_one()
                self.assertEqual(c_db.status, "NEW")
                disps = (await session.execute(select(Disposition).filter(Disposition.case_id == case_id))).scalars().all()
                audits = (await session.execute(select(AuditEvent).filter(AuditEvent.case_id == case_id))).scalars().all()
                self.assertEqual(len(disps), 0)
                self.assertEqual(len(audits), 0)

        self.run_with_db(verify_clean)

    def test_step2_11_12_get_history_returns_persisted_ordered_history(self):
        """Step 2.11 & 2.12: GET /cases/{case_id}/history returns persisted history with deterministic ordering."""
        case_id = self.seed_case_fixture("CASE-HIST-01", "NEW")

        # Submit first disposition
        self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "analyst_notes": "CDD first step"
        })

        # Submit second disposition
        self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "ESCALATE_SENIOR_COMPLIANCE",
            "analyst_notes": "Escalation second step",
            "risk_acknowledged": True
        })

        # Fetch history via HTTP GET
        res = self.client.get(f"/cases/{case_id}/history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["disposition_count"], 2)
        self.assertEqual(data["audit_count"], 2)

        disps = data["disposition_history"]
        audits = data["audit_history"]

        # Deterministic ordering checks
        self.assertEqual(disps[0]["action_code"], "REQUEST_CUSTOMER_CDD")
        self.assertEqual(disps[1]["action_code"], "ESCALATE_SENIOR_COMPLIANCE")
        self.assertEqual(audits[0]["action_code"], "REQUEST_CUSTOMER_CDD")
        self.assertEqual(audits[1]["action_code"], "ESCALATE_SENIOR_COMPLIANCE")

    def test_step2_13_concurrent_dispositions_select_for_update(self):
        """Step 2.13: Concurrent disposition attempts against the same case respect SELECT FOR UPDATE row locking."""
        case_id = self.seed_case_fixture("CASE-CONCUR-01", "NEW")

        async def run_concurrent(session_factory):
            async def worker(action_code, notes, risk_ack=False):
                async with session_factory() as session:
                    repo = PostgreSQLCaseRepository(session)
                    service = CaseLifecycleService(repo)
                    ds_report = generate_case_analyst_decision_support(case_id, data_store)
                    res = await service.submit_case_disposition(
                        case_id=case_id,
                        action_code=action_code,
                        analyst_notes=notes,
                        decision_support_report=ds_report,
                        risk_acknowledged=risk_ack
                    )
                    if res.get("ok"):
                        await session.commit()
                    return res

            res1, res2 = await asyncio.gather(
                worker("DISMISS_CASE", "Dismiss concurrent"),
                worker("APPROVE_TRANSACTION", "Approve concurrent")
            )
            success_count = sum(1 for r in [res1, res2] if r.get("ok"))
            self.assertEqual(success_count, 1)

        self.run_with_db(run_concurrent)


if __name__ == "__main__":
    unittest.main()
