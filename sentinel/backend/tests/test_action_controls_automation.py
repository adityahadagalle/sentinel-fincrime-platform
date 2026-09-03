import unittest
import asyncio
from app.core.data_store import data_store
from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
from app.services.simulated_action_executor import execute_simulated_action

class TestActionControlsAutomation(unittest.TestCase):
    def setUp(self):
        data_store["graphs"] = {}
        data_store["cases"] = {}
        data_store["transactions"] = {}
        data_store["accounts"] = {}
        data_store["executed_actions"] = {}

    def test_01_automation_off_prevents_autonomous_execution(self):
        from app.services.orchestrator import run_pipeline
        tx = {
            "tx_id": "TX-ACT-01",
            "sender_account": "ACC-USR-01",
            "receiver_account": "ACC-MERCH-01",
            "amount": 4000.0,
            "risk_score": 45,
            "case_id": "CASE-ACT-01"
        }
        data_store["automation_mode"] = False
        res = run_pipeline(tx, data_store)
        exec_rec = res.get("execution_record", {})
        self.assertEqual(exec_rec.get("execution_status"), "NOT_EXECUTED")

    def test_02_manual_action_executes_with_human_operator(self):
        from main import _handle_action, ActionRequest
        tx = {
            "tx_id": "TX-ACT-02",
            "case_id": "CASE-ACT-02",
            "sender_account": "ACC-USR-02",
            "receiver_account": "ACC-MERCH-02",
            "amount": 5000.0,
            "risk_score": 50
        }
        data_store["transactions"]["TX-ACT-02"] = tx
        data_store["cases"]["CASE-ACT-02"] = {"case_id": "CASE-ACT-02", "status": "NEW", "nodes": []}

        req = ActionRequest(case_id="CASE-ACT-02", target_id="TX-ACT-02", account_id="ACC-USR-02")
        res = asyncio.run(_handle_action("monitor", req))
        self.assertTrue(res.get("ok"))
        exec_rec = res.get("execution_record", {})
        self.assertEqual(exec_rec.get("actor_type"), "HUMAN_OPERATOR")
        self.assertEqual(exec_rec.get("execution_status"), "SUCCESS")

    def test_03_manual_escalate_and_block_execution(self):
        from main import _handle_action, ActionRequest
        tx = {
            "tx_id": "TX-ACT-03",
            "case_id": "CASE-ACT-03",
            "sender_account": "ACC-USR-03",
            "receiver_account": "ACC-MERCH-03",
            "amount": 15000.0,
            "risk_score": 75
        }
        data_store["transactions"]["TX-ACT-03"] = tx
        data_store["cases"]["CASE-ACT-03"] = {"case_id": "CASE-ACT-03", "status": "NEW", "nodes": []}

        req = ActionRequest(case_id="CASE-ACT-03", target_id="TX-ACT-03", account_id="ACC-USR-03")
        res_esc = asyncio.run(_handle_action("escalate", req))
        self.assertTrue(res_esc.get("ok"))
        self.assertEqual(res_esc.get("execution_record", {}).get("actor_type"), "HUMAN_OPERATOR")

        res_blk = asyncio.run(_handle_action("block", req))
        self.assertTrue(res_blk.get("ok"))
        self.assertEqual(res_blk.get("execution_record", {}).get("actor_type"), "HUMAN_OPERATOR")

    def test_04_automation_on_executes_non_freeze_actions_with_automation_engine(self):
        from app.services.orchestrator import run_pipeline
        tx = {
            "tx_id": "TX-ACT-04",
            "sender_account": "ACC-USR-04",
            "receiver_account": "ACC-MERCH-04",
            "amount": 4000.0,
            "risk_score": 50,
            "case_id": "CASE-ACT-04"
        }
        data_store["automation_mode"] = True
        res = run_pipeline(tx, data_store)
        exec_rec = res.get("execution_record", {})
        self.assertEqual(exec_rec.get("execution_status"), "SUCCESS")
        self.assertEqual(exec_rec.get("actor_type"), "AUTOMATION_ENGINE")

    def test_05_automation_on_never_executes_freeze_automatically(self):
        from app.services.orchestrator import run_pipeline
        tx = {
            "tx_id": "TX-ACT-05",
            "sender_account": "ACC-USR-05",
            "receiver_account": "ACC-MERCH-05",
            "amount": 500000.0,
            "risk_score": 98,
            "requested_action": "FREEZE",
            "case_id": "CASE-ACT-05"
        }
        data_store["automation_mode"] = True
        res = run_pipeline(tx, data_store)
        exec_rec = res.get("execution_record", {})
        self.assertEqual(exec_rec.get("execution_status"), "REQUIRES_OPERATOR_ACTION")
        self.assertNotEqual(data_store.get("accounts", {}).get("ACC-USR-05", {}).get("status"), "FROZEN")

    def test_06_freeze_operator_execution_changes_account_state_to_frozen(self):
        from main import execute_operator_freeze, FreezeRequestPayload
        tx = {
            "tx_id": "TX-ACT-06",
            "sender_account": "ACC-USR-06",
            "receiver_account": "ACC-MERCH-06",
            "amount": 500000.0,
            "risk_score": 95,
            "case_id": "CASE-ACT-06"
        }
        data_store["transactions"]["TX-ACT-06"] = tx
        data_store["cases"]["CASE-ACT-06"] = {"case_id": "CASE-ACT-06", "status": "NEW", "nodes": []}
        data_store["accounts"]["ACC-USR-06"] = {"account_id": "ACC-USR-06", "status": "ACTIVE"}

        payload = FreezeRequestPayload(operator_id="OP-TEST-01", reason="Operator test freeze")
        res = asyncio.run(execute_operator_freeze(transaction_id="TX-ACT-06", case_id="CASE-ACT-06", payload=payload, repo=None))
        
        self.assertEqual(res.get("execution_status"), "SUCCESS")
        self.assertEqual(res.get("actor_type"), "HUMAN_OPERATOR")
        self.assertEqual(data_store["accounts"]["ACC-USR-06"]["status"], "FROZEN")

    def test_07_idempotency_prevents_duplicate_execution(self):
        pol = {"policy_rule_id": "POL-TEST-07", "decision": "EXECUTE", "risk_score": 50, "risk_level": "MEDIUM"}
        res1 = asyncio.run(execute_simulated_action("CASE-IDEM", "TX-IDEM-01", "MONITOR", pol, actor_type="HUMAN_OPERATOR"))
        res2 = asyncio.run(execute_simulated_action("CASE-IDEM", "TX-IDEM-01", "MONITOR", pol, actor_type="HUMAN_OPERATOR"))
        self.assertEqual(res1["execution_id"], res2["execution_id"])

if __name__ == "__main__":
    unittest.main()
