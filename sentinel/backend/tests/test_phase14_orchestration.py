"""
Phase 14 Automated Response Orchestration & Governance Unit Tests.

Verifies:
1. LOW score transaction maps to MONITOR decision.
2. MEDIUM score transaction maps to ENHANCED_MONITORING decision.
3. HIGH score transaction maps to ESCALATE_ANALYST_REVIEW decision.
4. CRITICAL score transaction maps to URGENT_ANALYST_REVIEW decision.
5. Autonomous forbidden financial actions are intercepted and flagged as REQUIRES_HUMAN_APPROVAL.
6. Response decisions are persisted to PostgreSQL raw_payload.
7. Idempotency on repeated transaction processing.
"""

import unittest
import asyncio
import os
from app.engines.response_policy_engine import evaluate_response_policy, FORBIDDEN_AUTONOMOUS_ACTIONS
from app.services.orchestrator import run_pipeline
from app.db.session import get_db_session
from app.repositories.postgres import PostgreSQLCaseRepository
from app.core.data_store import data_store


class TestPhase14Orchestration(unittest.IsolatedAsyncioTestCase):

    def test_01_low_risk_response_policy(self):
        """LOW score transaction maps to MONITOR decision."""
        tx = {"tx_id": "TX-P14-LOW", "risk_score": 25, "amount": 100.0}
        dec = evaluate_response_policy(tx)
        self.assertEqual(dec["risk_level"], "LOW")
        self.assertEqual(dec["action"], "MONITOR")
        self.assertEqual(dec["action_status"], "COMPLETED")
        self.assertFalse(dec["requires_human_approval"])
        self.assertEqual(dec["financial_action_status"], "NOT_APPLICABLE")

    def test_02_medium_risk_response_policy(self):
        """MEDIUM score transaction maps to ENHANCED_MONITORING decision."""
        tx = {"tx_id": "TX-P14-MED", "risk_score": 55, "amount": 2500.0}
        dec = evaluate_response_policy(tx)
        self.assertEqual(dec["risk_level"], "MEDIUM")
        self.assertEqual(dec["action"], "ENHANCED_MONITORING")
        self.assertFalse(dec["requires_human_approval"])

    def test_03_high_risk_response_policy(self):
        """HIGH score transaction maps to ESCALATE_ANALYST_REVIEW decision."""
        tx = {"tx_id": "TX-P14-HIGH", "risk_score": 75, "amount": 45000.0}
        dec = evaluate_response_policy(tx)
        self.assertEqual(dec["risk_level"], "HIGH")
        self.assertEqual(dec["action"], "ESCALATE_ANALYST_REVIEW")
        self.assertTrue(dec["requires_human_approval"])

    def test_04_critical_risk_response_policy(self):
        """CRITICAL score transaction maps to URGENT_ANALYST_REVIEW decision."""
        tx = {"tx_id": "TX-P14-CRIT", "risk_score": 92, "amount": 150000.0}
        dec = evaluate_response_policy(tx)
        self.assertEqual(dec["risk_level"], "CRITICAL")
        self.assertEqual(dec["action"], "URGENT_ANALYST_REVIEW")
        self.assertTrue(dec["requires_human_approval"])
        self.assertEqual(dec["financial_action_status"], "HUMAN AUTHORIZATION REQUIRED")

    def test_05_forbidden_financial_action_governance_intercept(self):
        """Forbidden financial actions are intercepted and flagged as REQUIRES_HUMAN_APPROVAL."""
        for forbidden in FORBIDDEN_AUTONOMOUS_ACTIONS:
            tx = {"tx_id": f"TX-FORBIDDEN-{forbidden}", "risk_score": 90, "requested_action": forbidden}
            dec = evaluate_response_policy(tx)
            self.assertEqual(dec["action"], forbidden)
            self.assertEqual(dec["action_status"], "REQUIRES_HUMAN_APPROVAL")
            self.assertTrue(dec["requires_human_approval"])
            self.assertEqual(dec["financial_action_status"], "HUMAN AUTHORIZATION REQUIRED")

    def test_06_idempotent_response_decision(self):
        """Repeated policy evaluation reuses existing decision."""
        tx = {"tx_id": "TX-P14-IDEM", "risk_score": 88}
        dec1 = evaluate_response_policy(tx)
        dec2 = evaluate_response_policy(tx)
        self.assertIs(dec1, dec2)

    async def test_07_postgres_persistence_of_response_decision(self):
        """Verifies response decision is persisted in PostgreSQL raw_payload."""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            self.skipTest("PostgreSQL not configured")

        tx_id = "TX-P14-PG"
        acc_s = {"account_id": "ACC-P14-SND", "status": "active"}
        acc_r = {"account_id": "ACC-P14-RCV", "status": "active"}
        tx_dict = {
            "tx_id": tx_id,
            "sender_account": "ACC-P14-SND",
            "receiver_account": "ACC-P14-RCV",
            "amount": 99000.0,
            "channel": "UPI",
            "cross_border_risk": True,
            "risk_score": 95,
            "timestamp": "2026-09-01T12:00:00Z"
        }


        result = run_pipeline(tx_dict, data_store)
        saved_tx = result["transaction"]

        async for session in get_db_session():
            repo = PostgreSQLCaseRepository(session)
            await repo.save_transaction_and_case([acc_s, acc_r], saved_tx, result.get("case"))
            await session.commit()

            fetched_tx = await repo.get_transaction(tx_id)
            self.assertIsNotNone(fetched_tx)
            raw = fetched_tx.get("raw_payload", {})
            self.assertIn("response_decision", raw)
            dec = raw["response_decision"]
            self.assertEqual(dec["transaction_id"], tx_id)
            self.assertIn("action", dec)
            self.assertIn("action_status", dec)
            self.assertTrue(dec["automated"])
            break



if __name__ == "__main__":
    unittest.main()
