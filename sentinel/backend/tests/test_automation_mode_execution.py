import unittest
import asyncio
from app.core.data_store import data_store
from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
from app.services.simulated_action_executor import execute_simulated_action

class TestAutomationModeExecution(unittest.TestCase):
    def setUp(self):
        data_store["graphs"] = {}
        data_store["cases"] = {}
        data_store["transactions"] = {}
        data_store["accounts"] = {}
        data_store["executed_actions"] = {}

    def test_01_automation_off_mode_does_not_execute_actions(self):
        from app.services.orchestrator import run_pipeline
        data_store["automation_mode"] = False
        tx = {
            "tx_id": "TX-AUTO-OFF-01",
            "sender_account": "ACC-TEST-01",
            "receiver_account": "ACC-TEST-02",
            "amount": 3000.0,
            "risk_score": 45,
            "case_id": "CASE-AUTO-OFF-01"
        }
        res = run_pipeline(tx, data_store)
        exec_rec = res.get("execution_record", {})
        self.assertEqual(exec_rec.get("execution_status"), "NOT_EXECUTED")
        self.assertEqual(exec_rec.get("automation_mode"), "AUTOMATE_OFF")

    def test_02_automation_on_mode_executes_non_freeze_actions_automatically(self):
        from app.services.orchestrator import run_pipeline
        data_store["automation_mode"] = True
        tx = {
            "tx_id": "TX-AUTO-ON-01",
            "sender_account": "ACC-TEST-03",
            "receiver_account": "ACC-TEST-04",
            "amount": 4000.0,
            "risk_score": 50,
            "case_id": "CASE-AUTO-ON-01"
        }
        res = run_pipeline(tx, data_store)
        exec_rec = res.get("execution_record", {})
        self.assertEqual(exec_rec.get("execution_status"), "SUCCESS")
        self.assertEqual(exec_rec.get("actor_type"), "AUTOMATION_ENGINE")
        self.assertEqual(exec_rec.get("automation_mode"), "AUTOMATE_ON")

    def test_03_automation_on_never_executes_freeze_automatically(self):
        from app.services.orchestrator import run_pipeline
        data_store["automation_mode"] = True
        tx = {
            "tx_id": "TX-AUTO-FREEZE-01",
            "sender_account": "ACC-TEST-05",
            "receiver_account": "ACC-TEST-06",
            "amount": 500000.0,
            "risk_score": 98,
            "requested_action": "FREEZE",
            "case_id": "CASE-AUTO-FREEZE-01"
        }
        res = run_pipeline(tx, data_store)
        exec_rec = res.get("execution_record", {})
        self.assertEqual(exec_rec.get("execution_status"), "REQUIRES_OPERATOR_ACTION")
        self.assertNotEqual(data_store.get("accounts", {}).get("ACC-TEST-05", {}).get("status"), "FROZEN")

    def test_04_toggling_automation_on_sweeps_pending_transactions(self):
        from main import set_automation_mode, AutomationModeRequest
        data_store["automation_mode"] = False
        tx = {
            "tx_id": "TX-PENDING-01",
            "sender_account": "ACC-TEST-07",
            "receiver_account": "ACC-TEST-08",
            "amount": 5000.0,
            "risk_score": 55,
            "case_id": "CASE-PENDING-01",
            "execution_record": {"execution_status": "NOT_EXECUTED", "automation_mode": "AUTOMATE_OFF"}
        }
        data_store["transactions"]["TX-PENDING-01"] = tx
        data_store["cases"]["CASE-PENDING-01"] = {"case_id": "CASE-PENDING-01", "status": "NEW"}

        req = AutomationModeRequest(enabled=True, operator_id="OPERATOR_ADMIN")
        res = asyncio.run(set_automation_mode(req, repo=None))
        self.assertEqual(res.get("status"), "success")

        updated_tx = data_store["transactions"]["TX-PENDING-01"]
        exec_rec = updated_tx.get("execution_record", {})
        self.assertEqual(exec_rec.get("execution_status"), "SUCCESS")
        self.assertEqual(exec_rec.get("actor_type"), "AUTOMATION_ENGINE")

if __name__ == "__main__":
    unittest.main()
