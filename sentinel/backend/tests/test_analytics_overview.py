import unittest
import asyncio
from app.core.data_store import data_store

class TestAnalyticsOverview(unittest.TestCase):
    def setUp(self):
        data_store["graphs"] = {}
        data_store["cases"] = {}
        data_store["transactions"] = {}
        data_store["accounts"] = {}
        data_store["executed_actions"] = {}
        data_store["automation_mode"] = True

        # Populate sample transactions
        data_store["transactions"]["TX-101"] = {
            "tx_id": "TX-101",
            "risk_score": 85,
            "amount": 250000.0,
            "channel": "UPI",
            "case_id": "CASE-101",
            "execution_record": {"execution_status": "SUCCESS", "actor_type": "AUTOMATION_ENGINE"},
            "timestamp": "2026-09-02T10:00:00Z"
        }
        data_store["transactions"]["TX-102"] = {
            "tx_id": "TX-102",
            "risk_score": 45,
            "amount": 50000.0,
            "channel": "IMPS",
            "case_id": "CASE-102",
            "execution_record": {"execution_status": "SUCCESS", "actor_type": "HUMAN_OPERATOR"},
            "timestamp": "2026-09-02T10:05:00Z"
        }
        data_store["transactions"]["TX-103"] = {
            "tx_id": "TX-103",
            "risk_score": 25,
            "amount": 1200.0,
            "channel": "NEFT",
            "case_id": None,
            "execution_record": {"execution_status": "SUCCESS", "actor_type": "AUTOMATION_ENGINE"},
            "timestamp": "2026-09-02T10:10:00Z"
        }

        # Populate executed actions
        data_store["executed_actions"]["AUTO-ACTION:CASE-101:TX-101:POL-01"] = {
            "action_code": "MONITOR",
            "actor_type": "AUTOMATION_ENGINE"
        }
        data_store["executed_actions"]["AUTO-ACTION:CASE-102:TX-102:POL-02"] = {
            "action_code": "ENHANCED_MONITORING",
            "actor_type": "HUMAN_OPERATOR"
        }

        # Populate sample case
        data_store["cases"]["CASE-101"] = {
            "case_id": "CASE-101",
            "status": "ACTIONED",
            "total_fraud_amount": 250000.0,
            "recoverable_amount": 200000.0,
            "chain": ["ACC-01", "ACC-02", "ACC-03"],
            "max_nodes": 5
        }


    def test_01_analytics_overview_structure(self):
        from main import get_analytics_overview
        data = asyncio.run(get_analytics_overview(timeframe="30d"))
        
        self.assertIn("kpis", data)
        self.assertIn("risk_trend", data)
        self.assertIn("alerts_by_risk_level", data)
        self.assertIn("investigation_performance", data)
        self.assertIn("action_outcomes", data)
        self.assertIn("automation_intelligence", data)
        self.assertIn("risk_distribution", data)
        self.assertIn("channel_performance", data)
        self.assertIn("detected_patterns", data)
        self.assertIn("network_intelligence", data)
        self.assertIn("financial_impact", data)
        self.assertIn("system_health", data)

        kpis = data["kpis"]
        self.assertEqual(kpis["total_transactions"], 3)
        self.assertEqual(kpis["risk_alerts"], 2) # score >= 40

        auto = data["automation_intelligence"]
        self.assertTrue(auto["automation_mode"])
        self.assertGreaterEqual(auto["automated_actions_count"], 1)

if __name__ == "__main__":
    unittest.main()
