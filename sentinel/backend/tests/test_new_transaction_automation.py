import unittest
import asyncio
from app.core.data_store import data_store
from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
from app.services.simulated_action_executor import execute_simulated_action

class TestNewTransactionAutomation(unittest.TestCase):
    def setUp(self):
        data_store["graphs"] = {}
        data_store["cases"] = {}
        data_store["transactions"] = {}
        data_store["accounts"] = {}
        data_store["executed_actions"] = {}

    def test_01_new_transaction_automation_off_requires_action(self):
        from main import _process_policy_and_action
        data_store["automation_mode"] = False
        tx = {
            "tx_id": "TX-NEW-OFF-01",
            "sender_account": "ACC-USR-01",
            "receiver_account": "ACC-USR-02",
            "amount": 3000.0,
            "risk_score": 45,
            "case_id": "CASE-NEW-OFF-01"
        }
        case = {"case_id": "CASE-NEW-OFF-01", "status": "NEW"}
        pol, exec_rec = asyncio.run(_process_policy_and_action(tx, case, repo=None))
        self.assertEqual(exec_rec.get("execution_status"), "NOT_EXECUTED")
        self.assertEqual(exec_rec.get("automation_mode"), "AUTOMATE_OFF")

    def test_02_new_transaction_automation_on_executes_automatically(self):
        from main import _process_policy_and_action
        data_store["automation_mode"] = True
        tx = {
            "tx_id": "TX-NEW-ON-01",
            "sender_account": "ACC-USR-03",
            "receiver_account": "ACC-USR-04",
            "amount": 4000.0,
            "risk_score": 50,
            "case_id": "CASE-NEW-ON-01"
        }
        case = {"case_id": "CASE-NEW-ON-01", "status": "NEW"}
        pol, exec_rec = asyncio.run(_process_policy_and_action(tx, case, repo=None))
        self.assertEqual(exec_rec.get("execution_status"), "SUCCESS")
        self.assertEqual(exec_rec.get("actor_type"), "AUTOMATION_ENGINE")
        self.assertEqual(exec_rec.get("automation_mode"), "AUTOMATE_ON")

    def test_03_new_freeze_transaction_automation_on_requires_operator_action(self):
        from main import _process_policy_and_action
        data_store["automation_mode"] = True
        tx = {
            "tx_id": "TX-NEW-FREEZE-01",
            "sender_account": "ACC-USR-05",
            "receiver_account": "ACC-USR-06",
            "amount": 500000.0,
            "risk_score": 98,
            "requested_action": "FREEZE",
            "case_id": "CASE-NEW-FREEZE-01"
        }
        case = {"case_id": "CASE-NEW-FREEZE-01", "status": "NEW"}
        pol, exec_rec = asyncio.run(_process_policy_and_action(tx, case, repo=None))
        self.assertEqual(exec_rec.get("execution_status"), "REQUIRES_OPERATOR_ACTION")
        self.assertNotEqual(data_store.get("accounts", {}).get("ACC-USR-05", {}).get("status"), "FROZEN")


if __name__ == "__main__":
    unittest.main()
