import sys
import os
import unittest
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.data_store import data_store
from app.services.orchestrator import run_pipeline
from app.services.evidence_agent import collect_evidence, collect_evidence_for_case, collect_evidence_for_transaction
from app.services.contextual_agent import investigate_context, investigate_case, investigate_transaction


class TestContextualAgent(unittest.TestCase):

    def setUp(self):
        data_store["transactions"].clear()
        data_store["cases"].clear()
        data_store["graphs"].clear()
        data_store["accounts"].clear()
        data_store["actions"].clear()

    def test_1_valid_evidence_package_investigation(self):
        """Test 1: Valid evidence package produces contextual investigation."""
        tx = {
            "tx_id": "TX-CTX-001",
            "timestamp": "2026-09-01T10:00:00Z",
            "sender_account": "ACC-VICTIM-100",
            "receiver_account": "ACC-MULE-200",
            "amount": 350000.0,
            "currency": "INR",
            "channel": "UPI",
            "on_active_call": True
        }
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        evidence_pkg = collect_evidence_for_case(case_id, data_store)
        report = investigate_context(evidence_pkg)

        self.assertTrue(report["found"])
        self.assertEqual(report["status"], "SUCCESS")
        self.assertEqual(report["case_id"], case_id)
        self.assertIn("contextual_severity", report["summary"])
        self.assertIn(report["summary"]["contextual_severity"], ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        self.assertGreater(len(report["patterns"]), 0)
        self.assertGreater(len(report["contextual_findings"]), 0)

    def test_2_baseline_deviation_pattern_detection(self):
        """Test 2: Baseline deviation pattern is detected when supported."""
        # Set account baseline to small amount
        data_store["accounts"]["ACC-USER-DEV"] = {
            "account_id": "ACC-USER-DEV",
            "avg_monthly_tx_amount": 10000.0,
            "current_balance_sim": 500000.0,
            "status": "active"
        }

        tx = {
            "tx_id": "TX-DEV-001",
            "timestamp": "2026-09-01T10:30:00Z",
            "sender_account": "ACC-USER-DEV",
            "receiver_account": "ACC-MERCH-888",
            "amount": 250000.0,  # 25x deviation
            "currency": "INR",
            "channel": "IMPS"
        }
        run_pipeline(tx, data_store)

        report = investigate_transaction("TX-DEV-001", data_store)
        self.assertTrue(report["found"])
        self.assertTrue(report["behavioral_analysis"]["baseline_deviation"]["detected"])
        self.assertGreaterEqual(report["behavioral_analysis"]["baseline_deviation"]["ratio"], 5.0)

        p_ids = [p["pattern_id"] for p in report["patterns"]]
        self.assertIn("BEHAVIORAL_ESCALATION", p_ids)

    def test_3_first_time_high_value_counterparty_detection(self):
        """Test 3: First-time high-value counterparty pattern is detected when supported."""
        tx = {
            "tx_id": "TX-FTC-001",
            "timestamp": "2026-09-01T11:00:00Z",
            "sender_account": "ACC-SENDER-NEW",
            "receiver_account": "ACC-RCVR-NEW",
            "amount": 150000.0,
            "currency": "INR",
            "channel": "NEFT"
        }
        run_pipeline(tx, data_store)

        report = investigate_transaction("TX-FTC-001", data_store)
        self.assertTrue(report["counterparty_analysis"]["first_time_counterparty"])

        p_ids = [p["pattern_id"] for p in report["patterns"]]
        self.assertIn("FIRST_TIME_HIGH_VALUE_COUNTERPARTY", p_ids)

    def test_4_multi_hop_graph_pattern_detection(self):
        """Test 4: Multi-hop graph pattern is detected when supported."""
        tx1 = {
            "tx_id": "TX-HOP-001",
            "timestamp": "2026-09-01T12:00:00Z",
            "sender_account": "ACC-ORIGIN-99",
            "receiver_account": "ACC-MULE-1",
            "amount": 400000.0,
            "currency": "INR",
            "channel": "NEFT"
        }
        res1 = run_pipeline(tx1, data_store)
        case_id = res1["case"]["case_id"]

        tx2 = {
            "tx_id": "TX-HOP-002",
            "timestamp": "2026-09-01T12:05:00Z",
            "sender_account": "ACC-MULE-1",
            "receiver_account": "ACC-MULE-2",
            "amount": 390000.0,
            "currency": "INR",
            "channel": "IMPS",
            "case_id": case_id,
            "hop_number": 1
        }
        run_pipeline(tx2, data_store)

        report = investigate_case(case_id, data_store)
        self.assertGreaterEqual(report["graph_analysis"]["propagation_depth"], 1)

        p_ids = [p["pattern_id"] for p in report["patterns"]]
        self.assertTrue("MULTI_HOP_PROPAGATION" in p_ids or "PASS_THROUGH_ACTIVITY" in p_ids)

    def test_5_insufficient_evidence_handling(self):
        """Test 5: Insufficient evidence does not create fabricated findings."""
        tx = {
            "tx_id": "TX-NORMAL-100",
            "timestamp": "2026-09-01T13:00:00Z",
            "sender_account": "ACC-NORM-1",
            "receiver_account": "ACC-NORM-2",
            "amount": 200.0,
            "currency": "INR",
            "channel": "UPI"
        }
        run_pipeline(tx, data_store)

        report = investigate_transaction("TX-NORMAL-100", data_store)
        self.assertTrue(report["found"])
        self.assertLessEqual(report["summary"]["pattern_count"], 1)

        for finding in report["contextual_findings"]:
            self.assertNotIn("guilty", finding["finding"].lower())
            self.assertNotIn("money laundering", finding["finding"].lower())

    def test_6_missing_evidence_package_handling(self):
        """Test 6: Missing evidence package is handled gracefully with INSUFFICIENT_DATA status."""
        report = investigate_context(None)
        self.assertFalse(report["found"])
        self.assertEqual(report["status"], "INSUFFICIENT_DATA")

        missing_pkg = {"found": False, "target_id": "CASE-MISSING"}
        report_missing = investigate_context(missing_pkg)
        self.assertFalse(report_missing["found"])
        self.assertEqual(report_missing["status"], "INSUFFICIENT_DATA")

    def test_7_finding_evidence_traceability(self):
        """Test 7: Every contextual finding contains valid supporting evidence IDs."""
        tx = {
            "tx_id": "TX-TRACE-001",
            "timestamp": "2026-09-01T14:00:00Z",
            "sender_account": "ACC-VICTIM-999",
            "receiver_account": "ACC-DRAIN-999",
            "amount": 300000.0,
            "currency": "INR",
            "channel": "NEFT",
            "is_cross_border": True
        }
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        report = investigate_case(case_id, data_store)
        self.assertGreater(len(report["contextual_findings"]), 0)

        for f in report["contextual_findings"]:
            self.assertIn("id", f)
            self.assertIn("supporting_evidence_ids", f)
            self.assertTrue(isinstance(f["supporting_evidence_ids"], list))
            if f["id"] != "CTX-000":
                self.assertGreater(len(f["supporting_evidence_ids"]), 0, f"Finding {f['id']} missing evidence IDs")

    def test_8_determinism(self):
        """Test 8: Same input produces deterministic output."""
        tx = {
            "tx_id": "TX-DET-001",
            "timestamp": "2026-09-01T15:00:00Z",
            "sender_account": "ACC-DET-1",
            "receiver_account": "ACC-DET-2",
            "amount": 180000.0,
            "currency": "INR",
            "channel": "IMPS",
            "on_active_call": True
        }
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        pkg = collect_evidence_for_case(case_id, data_store)
        rep1 = investigate_context(pkg)
        rep2 = investigate_context(pkg)

        self.assertEqual(rep1["summary"]["contextual_severity"], rep2["summary"]["contextual_severity"])
        self.assertEqual(rep1["summary"]["confidence"], rep2["summary"]["confidence"])
        self.assertEqual(len(rep1["patterns"]), len(rep2["patterns"]))
        self.assertEqual(len(rep1["contextual_findings"]), len(rep2["contextual_findings"]))

    def test_9_no_fabricated_external_claims(self):
        """Test 9: External KYC/sanctions/criminal claims are never fabricated."""
        tx = {
            "tx_id": "TX-NOFAB-001",
            "timestamp": "2026-09-01T16:00:00Z",
            "sender_account": "ACC-A",
            "receiver_account": "ACC-B",
            "amount": 50000.0,
            "currency": "INR",
            "channel": "UPI"
        }
        run_pipeline(tx, data_store)
        report = investigate_transaction("TX-NOFAB-001", data_store)

        report_str = str(report).lower()
        self.assertNotIn("sanctions", report_str)
        self.assertNotIn("interpol", report_str)
        self.assertNotIn("criminal_record", report_str)
        self.assertNotIn("external_kyc_matched", report_str)

    def test_10_mule_drainage_1hop_no_match(self):
        """Test A: 1-hop transaction with risk >= 60 does NOT trigger mule drainage when no accounts are withdrawn."""
        pkg = {
            "found": True,
            "target_id": "CASE-1HOP-TEST",
            "case_id": "CASE-1HOP-TEST",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "transaction",
                    "category": "Primary Transaction Evidence",
                    "severity": "HIGH",
                    "data": {"risk_score": 65.0, "amount": 100000.0}
                },
                {
                    "id": "EV-002",
                    "type": "graph_network",
                    "category": "Graph Topology",
                    "severity": "MEDIUM",
                    "data": {"chain_depth": 1, "nodes_count": 2, "frozen_accounts": [], "withdrawn_accounts": []}
                }
            ]
        }
        report = investigate_context(pkg)
        p_ids = [p["pattern_id"] for p in report["patterns"]]
        self.assertNotIn("MULE_ACCOUNT_DRAINAGE", p_ids, "1-hop transaction incorrectly triggered MULE_ACCOUNT_DRAINAGE")

    def test_11_mule_drainage_2hop_matches(self):
        """Test B: 2-hop high-risk activity (chain_depth >= 2 and risk_score >= 70) CAN trigger mule drainage."""
        pkg = {
            "found": True,
            "target_id": "CASE-2HOP-TEST",
            "case_id": "CASE-2HOP-TEST",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "transaction",
                    "category": "Primary Transaction Evidence",
                    "severity": "HIGH",
                    "data": {"risk_score": 75.0, "amount": 100000.0}
                },
                {
                    "id": "EV-002",
                    "type": "graph_network",
                    "category": "Graph Topology",
                    "severity": "HIGH",
                    "data": {"chain_depth": 2, "nodes_count": 3, "frozen_accounts": [], "withdrawn_accounts": []}
                }
            ]
        }
        report = investigate_context(pkg)
        p_ids = [p["pattern_id"] for p in report["patterns"]]
        self.assertIn("MULE_ACCOUNT_DRAINAGE", p_ids, "2-hop high-risk activity failed to trigger MULE_ACCOUNT_DRAINAGE")

    def test_12_mule_drainage_withdrawn_account_matches(self):
        """Test C: Presence of withdrawn_accounts CAN trigger mule drainage."""
        pkg = {
            "found": True,
            "target_id": "CASE-WITHDRAWN-TEST",
            "case_id": "CASE-WITHDRAWN-TEST",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "transaction",
                    "category": "Primary Transaction Evidence",
                    "severity": "HIGH",
                    "data": {"risk_score": 50.0, "amount": 50000.0}
                },
                {
                    "id": "EV-002",
                    "type": "graph_network",
                    "category": "Graph Topology",
                    "severity": "HIGH",
                    "data": {"chain_depth": 1, "nodes_count": 2, "frozen_accounts": [], "withdrawn_accounts": ["ACC-DRAINED-99"]}
                }
            ]
        }
        report = investigate_context(pkg)
        p_ids = [p["pattern_id"] for p in report["patterns"]]
        self.assertIn("MULE_ACCOUNT_DRAINAGE", p_ids, "Withdrawn accounts failed to trigger MULE_ACCOUNT_DRAINAGE")

    def test_13_baseline_deviation_alone_not_high_severity(self):
        """Test D: Baseline deviation alone (deviation_ratio >= 5) does NOT create HIGH overall contextual severity."""
        pkg = {
            "found": True,
            "target_id": "CASE-DEV-ALONE",
            "case_id": "CASE-DEV-ALONE",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "transaction",
                    "category": "Primary Transaction Evidence",
                    "severity": "MEDIUM",
                    "data": {"risk_score": 30.0, "amount": 80000.0}
                },
                {
                    "id": "EV-002",
                    "type": "historical_behavior",
                    "category": "Origin Account Baseline",
                    "severity": "MEDIUM",
                    "data": {"deviation_ratio": 8.0, "avg_monthly_tx_amount": 10000.0}
                },
                {
                    "id": "EV-003",
                    "type": "historical_behavior",
                    "category": "Counterparty Relationship",
                    "severity": "LOW",
                    "data": {"is_first_interaction": False, "prior_transactions_count": 15}
                }
            ]
        }
        report = investigate_context(pkg)
        # BEHAVIORAL_ESCALATION pattern matches as MEDIUM
        p_dict = {p["pattern_id"]: p for p in report["patterns"]}
        self.assertIn("BEHAVIORAL_ESCALATION", p_dict)
        self.assertEqual(p_dict["BEHAVIORAL_ESCALATION"]["severity"], "MEDIUM")
        # Overall severity remains MEDIUM, not HIGH
        self.assertNotEqual(report["summary"]["contextual_severity"], "HIGH")
        self.assertEqual(report["summary"]["contextual_severity"], "MEDIUM")

    def test_14_multi_signal_behavioral_escalation_becomes_high(self):
        """Test E: Baseline deviation combined with additional contextual risk signals DOES create HIGH overall severity."""
        pkg = {
            "found": True,
            "target_id": "CASE-DEV-MULTI",
            "case_id": "CASE-DEV-MULTI",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "transaction",
                    "category": "Primary Transaction Evidence",
                    "severity": "HIGH",
                    "data": {"risk_score": 60.0, "amount": 60000.0}
                },
                {
                    "id": "EV-002",
                    "type": "historical_behavior",
                    "category": "Origin Account Baseline",
                    "severity": "HIGH",
                    "data": {"deviation_ratio": 8.0, "avg_monthly_tx_amount": 7500.0}
                },
                {
                    "id": "EV-003",
                    "type": "historical_behavior",
                    "category": "Counterparty Relationship",
                    "severity": "HIGH",
                    "data": {"is_first_interaction": True, "prior_transactions_count": 0}
                }
            ]
        }
        report = investigate_context(pkg)
        self.assertEqual(report["summary"]["contextual_severity"], "HIGH")


if __name__ == "__main__":
    unittest.main()
