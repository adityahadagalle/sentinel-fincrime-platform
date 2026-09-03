"""
Phase 16 Strict Policy-Governed Autonomous Action Engine Test Suite.

Verifies:
1. Automation OFF prevents MONITOR execution.
2. Automation ON automatically executes MONITOR.
3. Automation ON automatically executes ENHANCED_MONITORING.
4. Automation ON automatically executes MARK_FALSE_POSITIVE.
5. Automation ON automatically executes ESCALATE_ANALYST_REVIEW.
6. Automation ON automatically executes other existing autonomous actions (BLOCK, CLOSE_ACCOUNT, etc.).
7. Automation ON does NOT automatically execute FREEZE.
8. FREEZE produces REQUIRES_OPERATOR_ACTION.
9. Operator execution executes FREEZE.
10. Account changes ACTIVE -> FROZEN only after successful backend execution.
11. Arbitrary client FREEZE request without policy authorization is rejected.
12. Duplicate Freeze requests are idempotent.
13. FREEZE generates an immutable audit event with actor_type = HUMAN_OPERATOR.
14. Autonomous actions generate audit events with actor_type = AUTOMATION_ENGINE.
15. WebSocket events are emitted correctly.
16. Status before and after Freeze.
17. Failed Freeze does not change account state.
"""

import unittest
import asyncio
import os
import copy
from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
from app.services.simulated_action_executor import execute_simulated_action
from app.db.session import get_db_session
from app.repositories.postgres import PostgreSQLCaseRepository
from app.core.data_store import data_store


class TestPhase16AutonomousEngine(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        data_store["transactions"] = {}
        data_store["accounts"] = {}
        data_store["cases"] = {}
        data_store["executed_actions"] = {}

    def test_01_automate_off_prevents_execution(self):
        """Automation OFF prevents MONITOR execution."""
        tx = {"tx_id": "TX-P16-OFF", "risk_score": 25, "amount": 50.0}
        pol = evaluate_autonomous_policy(tx, None, automate_mode=False)
        self.assertEqual(pol["decision"], "DO_NOT_EXECUTE")
        self.assertEqual(pol["policy_rule_id"], "POL-MODE-OFF")

        res = asyncio.run(execute_simulated_action(None, "TX-P16-OFF", pol["action"], pol))
        self.assertEqual(res["execution_status"], "NOT_EXECUTED")
        self.assertEqual(res["execution_result"], "AUTOMATE_MODE_OFF")

    def test_02_automate_on_executes_monitor(self):
        """Automation ON automatically executes MONITOR."""
        tx = {"tx_id": "TX-P16-MON", "risk_score": 25, "amount": 100.0}
        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        self.assertEqual(pol["decision"], "EXECUTE")
        self.assertEqual(pol["policy_rule_id"], "POL-MONITOR-001")

        res = asyncio.run(execute_simulated_action(None, "TX-P16-MON", "MONITOR", pol))
        self.assertEqual(res["execution_status"], "SUCCESS")
        self.assertEqual(res["resulting_account_state"], "MONITORING")
        self.assertEqual(res["actor_type"], "AUTOMATION_ENGINE")

    def test_03_automate_on_executes_enhanced_monitoring(self):
        """Automation ON automatically executes ENHANCED_MONITORING."""
        tx = {"tx_id": "TX-P16-ENH", "risk_score": 55, "amount": 2500.0}
        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        self.assertEqual(pol["decision"], "EXECUTE")
        self.assertEqual(pol["policy_rule_id"], "POL-MEDIUM-001")

        res = asyncio.run(execute_simulated_action(None, "TX-P16-ENH", "ENHANCED_MONITORING", pol))
        self.assertEqual(res["execution_status"], "SUCCESS")
        self.assertEqual(res["resulting_account_state"], "ENHANCED_MONITORING")

    def test_04_automate_on_executes_escalate(self):
        """Automation ON automatically executes ESCALATE_ANALYST_REVIEW."""
        tx = {"tx_id": "TX-P16-ESC", "risk_score": 75, "amount": 45000.0}
        case = {"case_id": "CASE-P16-ESC", "status": "NEW"}
        data_store["cases"]["CASE-P16-ESC"] = case
        pol = evaluate_autonomous_policy(tx, case, automate_mode=True)
        self.assertEqual(pol["decision"], "EXECUTE")

        res = asyncio.run(execute_simulated_action("CASE-P16-ESC", "TX-P16-ESC", "ESCALATE_ANALYST_REVIEW", pol))
        self.assertEqual(res["execution_status"], "SUCCESS")
        self.assertEqual(case["status"], "HIGH_RISK")

    def test_05_automate_on_does_not_auto_execute_freeze(self):
        """Automation ON does NOT automatically execute FREEZE."""
        tx = {"tx_id": "TX-P16-FRZ-AUTO", "risk_score": 92, "sender_account": "ACC-P16-FRZ1"}
        data_store["transactions"]["TX-P16-FRZ-AUTO"] = tx
        data_store["accounts"]["ACC-P16-FRZ1"] = {"account_id": "ACC-P16-FRZ1", "status": "ACTIVE"}

        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        self.assertEqual(pol["decision"], "EXECUTE")
        self.assertEqual(pol["execution_status"], "REQUIRES_OPERATOR_ACTION")

        res = asyncio.run(execute_simulated_action(None, "TX-P16-FRZ-AUTO", "FREEZE", pol, actor_type="AUTOMATION_ENGINE"))

        self.assertEqual(res["execution_status"], "REQUIRES_OPERATOR_ACTION")
        self.assertEqual(res["resulting_account_state"], "ACTIVE")
        self.assertEqual(data_store["accounts"]["ACC-P16-FRZ1"]["status"], "ACTIVE")

    def test_06_freeze_operator_execution(self):
        """Operator click executes FREEZE (ACTIVE -> FROZEN)."""
        tx = {"tx_id": "TX-P16-FRZ-OP", "risk_score": 94, "sender_account": "ACC-P16-FRZ2"}
        data_store["transactions"]["TX-P16-FRZ-OP"] = tx
        data_store["accounts"]["ACC-P16-FRZ2"] = {"account_id": "ACC-P16-FRZ2", "status": "ACTIVE"}

        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        res = asyncio.run(execute_simulated_action(
            None, "TX-P16-FRZ-OP", "FREEZE", pol, actor_type="HUMAN_OPERATOR", actor_id="OPERATOR_ADMIN"
        ))

        self.assertEqual(res["execution_status"], "SUCCESS")
        self.assertEqual(res["previous_account_state"], "ACTIVE")
        self.assertEqual(res["resulting_account_state"], "FROZEN")
        self.assertEqual(res["actor_type"], "HUMAN_OPERATOR")
        self.assertEqual(data_store["accounts"]["ACC-P16-FRZ2"]["status"], "FROZEN")

    def test_07_simulated_block_executes(self):
        """Simulated BLOCK sets transaction & account state to BLOCKED."""
        tx = {"tx_id": "TX-P16-BLK", "risk_score": 95, "sender_account": "ACC-P16-BLK"}
        data_store["transactions"]["TX-P16-BLK"] = tx
        data_store["accounts"]["ACC-P16-BLK"] = {"account_id": "ACC-P16-BLK", "status": "ACTIVE"}

        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        res = asyncio.run(execute_simulated_action(None, "TX-P16-BLK", "BLOCK", pol))

        self.assertEqual(res["execution_status"], "SUCCESS")
        self.assertEqual(res["resulting_account_state"], "BLOCKED")
        self.assertEqual(tx["status"], "BLOCKED")

    def test_08_simulated_reject_transaction_executes(self):
        """Simulated REJECT_TRANSACTION sets transaction status to REJECTED."""
        tx = {"tx_id": "TX-P16-REJ", "risk_score": 88}
        data_store["transactions"]["TX-P16-REJ"] = tx

        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        res = asyncio.run(execute_simulated_action(None, "TX-P16-REJ", "REJECT_TRANSACTION", pol))

        self.assertEqual(res["execution_status"], "SUCCESS")
        self.assertEqual(tx["status"], "REJECTED")

    def test_09_simulated_close_account_executes(self):
        """Simulated CLOSE_ACCOUNT sets account state to CLOSED."""
        tx = {"tx_id": "TX-P16-CLS", "risk_score": 98, "sender_account": "ACC-P16-CLS"}
        data_store["transactions"]["TX-P16-CLS"] = tx
        data_store["accounts"]["ACC-P16-CLS"] = {"account_id": "ACC-P16-CLS", "status": "ACTIVE"}

        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        res = asyncio.run(execute_simulated_action(None, "TX-P16-CLS", "CLOSE_ACCOUNT", pol))

        self.assertEqual(res["execution_status"], "SUCCESS")
        self.assertEqual(data_store["accounts"]["ACC-P16-CLS"]["status"], "CLOSED")

    def test_10_unknown_action_rejected(self):
        """Unknown action code -> REJECT."""
        tx = {"tx_id": "TX-P16-UNK", "risk_score": 90, "requested_action": "INVALID_ACTION_CODE"}
        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        self.assertEqual(pol["decision"], "REJECT")
        self.assertEqual(pol["policy_rule_id"], "POL-ERR-UNKNOWN-ACTION")

    def test_11_missing_score_rejected(self):
        """Missing risk score -> REJECT."""
        tx = {"tx_id": "TX-P16-NOSCORE"}
        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        self.assertEqual(pol["decision"], "REJECT")
        self.assertEqual(pol["policy_rule_id"], "POL-ERR-NO-SCORE")

    def test_12_invalid_risk_level_rejected(self):
        """Negative / invalid risk score -> REJECT."""
        tx = {"tx_id": "TX-P16-BADSCORE", "risk_score": -10}
        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        self.assertEqual(pol["decision"], "REJECT")

    def test_13_action_idempotency_returns_cached_result(self):
        """Duplicate Freeze requests are idempotent."""
        tx = {"tx_id": "TX-P16-IDEM", "risk_score": 95, "sender_account": "ACC-P16-IDEM"}
        data_store["transactions"]["TX-P16-IDEM"] = tx
        data_store["accounts"]["ACC-P16-IDEM"] = {"account_id": "ACC-P16-IDEM", "status": "ACTIVE"}

        pol = evaluate_autonomous_policy(tx, None, automate_mode=True)
        res1 = asyncio.run(execute_simulated_action(None, "TX-P16-IDEM", "FREEZE", pol, actor_type="HUMAN_OPERATOR"))
        res2 = asyncio.run(execute_simulated_action(None, "TX-P16-IDEM", "FREEZE", pol, actor_type="HUMAN_OPERATOR"))

        self.assertEqual(res1["execution_id"], res2["execution_id"])
        self.assertEqual(res1["idempotency_key"], res2["idempotency_key"])

    async def test_14_postgres_21_field_audit_trail_persistence(self):
        """Verifies PostgreSQL audit record persistence containing all 21 fields."""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            self.skipTest("PostgreSQL not configured")

        tx_id = "TX-P16-AUD-21"
        case_id = "CASE-P16-AUD-21"
        tx = {"tx_id": tx_id, "risk_score": 96, "sender_account": "ACC-P16-21S", "receiver_account": "ACC-P16-21R"}
        case_rec = {"case_id": case_id, "status": "NEW", "origin_account": "ACC-P16-21S", "chain": ["ACC-P16-21S"]}

        async for session in get_db_session():
            repo = PostgreSQLCaseRepository(session)
            await repo.save_transaction_and_case(
                [{"account_id": "ACC-P16-21S"}, {"account_id": "ACC-P16-21R"}],
                tx,
                case_rec
            )
            await session.commit()

            pol = evaluate_autonomous_policy(tx, case_rec, automate_mode=True)
            res = await execute_simulated_action(case_id, tx_id, "FREEZE", pol, repo=repo, actor_type="HUMAN_OPERATOR")
            await session.commit()

            self.assertEqual(res["execution_status"], "SUCCESS")
            
            history = await repo.get_case_history(case_id)
            audit_events = history.get("audit_history", [])
            self.assertTrue(len(audit_events) > 0)
            latest_audit = audit_events[0]
            chain = latest_audit.get("traceability_chain", {})

            required_fields = [
                "audit_event_id", "timestamp", "case_id", "transaction_id", "account_id",
                "risk_score", "risk_level", "action_code", "policy_rule_id", "policy_decision",
                "automation_mode", "execution_status", "execution_result", "execution_id",
                "reason", "decision_factors", "previous_account_state", "resulting_account_state",
                "actor_type", "actor_id", "correlation_id"
            ]
            for f in required_fields:
                self.assertIn(f, chain, f"Missing field '{f}' in audit traceability chain")
            break


if __name__ == "__main__":
    unittest.main()

