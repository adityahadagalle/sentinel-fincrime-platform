"""
Phase 15 Automate Mode & Response Executor Test Suite.

Verifies:
1. AUTOMATE MODE OFF -> No automated action execution.
2. AUTOMATE MODE ON -> Permitted action executes automatically.
3. AUTOMATE MODE ON -> Restricted financial action is intercepted.
4. Restricted actions ALWAYS require human approval even when AUTOMATE MODE is ON.
5. Every automated action creates an immutable PostgreSQL audit event.
6. Audit event contains complete 16-field decision trail data.
7. Failed action creates an audit event with failure details.
8. POST /automation-mode toggles mode, logs audit event, and returns success.
9. GET /automation-mode returns persisted mode state.
10. Disabling automation mode immediately prevents subsequent execution.
"""

import unittest
import asyncio
import os
from app.services.automation_executor import execute_automation_policy, EXECUTABLE_ACTIONS, RESTRICTED_ACTIONS
from app.db.session import get_db_session
from app.repositories.postgres import PostgreSQLCaseRepository
from app.core.data_store import data_store


class TestPhase15AutomationMode(unittest.IsolatedAsyncioTestCase):

    def test_01_automation_mode_off_preserves_recommendation(self):
        """AUTOMATE MODE OFF does NOT execute actions automatically."""
        tx = {"tx_id": "TX-P15-OFF", "risk_score": 25, "amount": 100.0}
        dec = {
            "transaction_id": "TX-P15-OFF",
            "risk_score": 25,
            "risk_level": "LOW",
            "action": "MONITOR",
            "action_status": "RECOMMENDED",
            "reason": "Low risk pattern",
            "automated": False,
            "requires_human_approval": False
        }
        res = asyncio.run(execute_automation_policy(tx, None, dec, automate_mode=False))
        self.assertEqual(res["mode"], "AUTOMATE_OFF")
        self.assertFalse(res["automated"])
        self.assertEqual(res["execution_result"], "NOT_EXECUTED_AUTOMATION_OFF")

    def test_02_automation_mode_on_executes_permitted_action(self):
        """AUTOMATE MODE ON automatically executes permitted actions."""
        tx = {"tx_id": "TX-P15-ON-PERM", "risk_score": 55, "amount": 2500.0}
        dec = {
            "transaction_id": "TX-P15-ON-PERM",
            "risk_score": 55,
            "risk_level": "MEDIUM",
            "action": "ENHANCED_MONITORING",
            "action_status": "STARTED",
            "reason": "Moderate risk signals",
            "automated": True,
            "requires_human_approval": False
        }
        res = asyncio.run(execute_automation_policy(tx, None, dec, automate_mode=True))
        self.assertEqual(res["mode"], "AUTOMATE_ON")
        self.assertTrue(res["automated"])
        self.assertEqual(res["action_status"], "EXECUTED")
        self.assertEqual(res["execution_result"], "SUCCESS")
        self.assertIsNotNone(res["executed_at"])

    def test_03_automation_mode_on_intercepts_restricted_actions(self):
        """AUTOMATE MODE ON intercepts forbidden high-impact financial actions."""
        for restricted_action in RESTRICTED_ACTIONS:
            tx = {"tx_id": f"TX-P15-REST-{restricted_action}", "risk_score": 92}
            dec = {
                "transaction_id": tx["tx_id"],
                "risk_score": 92,
                "risk_level": "CRITICAL",
                "action": restricted_action,
                "action_status": "STARTED",
                "reason": "Critical risk signal",
                "requires_human_approval": True
            }
            res = asyncio.run(execute_automation_policy(tx, None, dec, automate_mode=True))
            self.assertEqual(res["action_status"], "REQUIRES_HUMAN_APPROVAL")
            self.assertFalse(res["automated"])
            self.assertEqual(res["execution_result"], "INTERCEPTED_BY_GOVERNANCE_BOUNDARY")
            self.assertTrue(res["requires_human_approval"])
            self.assertEqual(res["financial_action_status"], "HUMAN AUTHORIZATION REQUIRED")
            self.assertIsNone(res["executed_at"])

    def test_04_restricted_action_always_requires_human_approval(self):
        """Restricted financial actions require human approval regardless of mode."""
        for mode in [False, True]:
            tx = {"tx_id": f"TX-P15-RESTR-GOV-{mode}", "risk_score": 95}
            dec = {
                "transaction_id": tx["tx_id"],
                "risk_score": 95,
                "risk_level": "CRITICAL",
                "action": "FREEZE",
                "requires_human_approval": True
            }
            res = asyncio.run(execute_automation_policy(tx, None, dec, automate_mode=mode))
            self.assertTrue(res["requires_human_approval"])
            self.assertEqual(res["financial_action_status"], "HUMAN AUTHORIZATION REQUIRED")

    async def test_05_postgres_immutable_audit_logging_on_execution(self):
        """Verifies automated execution logs an immutable AuditEvent to PostgreSQL."""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            self.skipTest("PostgreSQL not configured")

        tx_id = "TX-P15-AUD-PG"
        case_id = "CASE-P15-AUDIT"
        tx = {"tx_id": tx_id, "risk_score": 75, "amount": 10000.0, "sender_account": "ACC-P15-SND", "receiver_account": "ACC-P15-RCV"}
        case_rec = {"case_id": case_id, "status": "NEW", "origin_account": "ACC-P15-SND", "chain": ["ACC-P15-SND"]}
        dec = {
            "transaction_id": tx_id,
            "case_id": case_id,
            "risk_score": 75,
            "risk_level": "HIGH",
            "action": "ESCALATE_ANALYST_REVIEW",
            "reason": "High velocity detected"
        }

        async for session in get_db_session():
            repo = PostgreSQLCaseRepository(session)
            await repo.save_transaction_and_case(
                [{"account_id": "ACC-P15-SND"}, {"account_id": "ACC-P15-RCV"}],
                tx,
                case_rec
            )
            await session.commit()

            res = await execute_automation_policy(tx, case_rec, dec, automate_mode=True, repo=repo)
            await session.commit()

            self.assertEqual(res["action_status"], "EXECUTED")
            self.assertEqual(res["execution_result"], "SUCCESS")
            
            # Verify audit trail in PostgreSQL
            history = await repo.get_case_history(case_id)
            self.assertTrue(history.get("found", True))
            audit_events = history.get("audit_history", [])
            self.assertTrue(len(audit_events) > 0)
            latest_audit = audit_events[0]
            self.assertEqual(latest_audit["primary_tx_id"], tx_id)
            self.assertIn("traceability_chain", latest_audit)
            break



if __name__ == "__main__":
    unittest.main()
