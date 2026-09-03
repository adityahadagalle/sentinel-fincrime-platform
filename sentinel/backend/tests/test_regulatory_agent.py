import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.data_store import data_store
from app.services.orchestrator import run_pipeline
from app.services.evidence_agent import collect_evidence_for_case, collect_evidence_for_transaction
from app.services.contextual_agent import investigate_context, investigate_case, investigate_transaction
from app.services.regulatory_agent import (
    assess_regulatory_risk,
    assess_case_regulatory_risk,
    assess_transaction_regulatory_risk
)


class TestRegulatoryAgent(unittest.TestCase):

    def setUp(self):
        data_store["transactions"].clear()
        data_store["cases"].clear()
        data_store["graphs"].clear()
        data_store["accounts"].clear()
        data_store["actions"].clear()

    def test_1_valid_input_produces_structured_report(self):
        """Test 1: Valid Phase 1 + Phase 2 input produces a structured regulatory report."""
        tx = {
            "tx_id": "TX-REG-001",
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

        ev_pkg = collect_evidence_for_case(case_id, data_store)
        ctx_rpt = investigate_context(ev_pkg)
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)

        self.assertTrue(report["found"])
        self.assertEqual(report["status"], "SUCCESS")
        self.assertEqual(report["case_id"], case_id)
        self.assertIn("regulatory_severity", report["summary"])
        self.assertIn("assessment_heuristic_index", report["summary"])
        self.assertIn("jurisdiction_data_status", report)
        self.assertEqual(report["jurisdiction_data_status"]["external_sanctions_database"], "UNAVAILABLE")
        self.assertEqual(report["jurisdiction_data_status"]["external_kyc_verification"], "NOT_CHECKED")
        self.assertGreater(len(report["regulatory_indicators"]), 0)
        self.assertGreater(len(report["compliance_considerations"]), 0)

    def test_2_missing_evidence_returns_insufficient_data(self):
        """Test 2: Missing evidence package returns INSUFFICIENT_DATA."""
        ctx_rpt = {"found": True, "target_id": "CASE-100"}
        report = assess_regulatory_risk(None, ctx_rpt)

        self.assertFalse(report["found"])
        self.assertEqual(report["status"], "INSUFFICIENT_DATA")
        self.assertEqual(report["summary"]["regulatory_severity"], "UNKNOWN")

    def test_3_missing_contextual_report_returns_insufficient_data(self):
        """Test 3: Missing contextual report returns INSUFFICIENT_DATA."""
        ev_pkg = {"found": True, "target_id": "CASE-100", "evidence": []}
        report = assess_regulatory_risk(ev_pkg, None)

        self.assertFalse(report["found"])
        self.assertEqual(report["status"], "INSUFFICIENT_DATA")

    def test_4_no_matching_indicators_returns_no_indicators_detected(self):
        """Test 4: Clean transaction with no matching regulatory thresholds returns NO_INDICATORS_DETECTED."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-CLEAN",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "transaction",
                    "category": "Primary Transaction Evidence",
                    "severity": "LOW",
                    "data": {"risk_score": 10.0, "amount": 100.0}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-CLEAN",
            "summary": {"contextual_severity": "LOW", "confidence": 0.5},
            "patterns": [],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)

        self.assertTrue(report["found"])
        self.assertEqual(report["status"], "NO_INDICATORS_DETECTED")
        self.assertEqual(len(report["regulatory_indicators"]), 0)
        self.assertEqual(report["summary"]["regulatory_severity"], "LOW")

    def test_5_cross_border_alone_not_high_severity(self):
        """Test 5: Cross-border flag alone without suspicious telemetry or high context does NOT produce a high indicator."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-XBORDER-SOLO",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "behavioral_telemetry",
                    "category": "System Telemetry Signals",
                    "severity": "LOW",
                    "data": {"active_flags": [{"flag": "is_cross_border"}]}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-XBORDER-SOLO",
            "summary": {"contextual_severity": "LOW", "confidence": 0.5},
            "patterns": [],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertNotIn("SUSPICIOUS_CROSS_BORDER_TELEMETRY", reg_codes)

    def test_6_cross_border_with_contextual_support_produces_indicator(self):
        """Test 6: Cross-border flag WITH active telemetry threat CAN produce a high indicator."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-XBORDER-THREAT",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "behavioral_telemetry",
                    "category": "System Telemetry Signals",
                    "severity": "HIGH",
                    "data": {"active_flags": [{"flag": "is_cross_border"}, {"flag": "on_active_call"}]}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-XBORDER-THREAT",
            "summary": {"contextual_severity": "HIGH", "confidence": 0.9},
            "patterns": [
                {
                    "pattern_id": "CROSS_BORDER_HIGH_RISK_ACTIVITY",
                    "matched": True,
                    "severity": "HIGH",
                    "supporting_evidence_ids": ["EV-001"]
                }
            ],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("SUSPICIOUS_CROSS_BORDER_TELEMETRY", reg_codes)

    def test_7_mule_indicator_requires_matched_pattern(self):
        """Test 7: Mule indicator is only produced when Phase 2 mule pattern is matched or withdrawn accounts exist."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-NOMULE",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "graph_network",
                    "category": "Graph Topology",
                    "severity": "LOW",
                    "data": {"chain_depth": 1, "withdrawn_accounts": []}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-NOMULE",
            "summary": {"contextual_severity": "MEDIUM"},
            "patterns": [],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertNotIn("MULE_LAYERED_DRAINAGE_INDICATOR", reg_codes)

    def test_8_first_time_high_value_payee_conditions(self):
        """Test 8: First-time payee indicator requires relevant high value conditions."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-FTC-HIGH",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "transaction",
                    "category": "Primary Transaction Evidence",
                    "severity": "HIGH",
                    "data": {"amount": 150000.0}
                },
                {
                    "id": "EV-002",
                    "type": "historical_behavior",
                    "category": "Counterparty Relationship",
                    "severity": "HIGH",
                    "data": {"is_first_interaction": True}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-FTC-HIGH",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [
                {
                    "pattern_id": "FIRST_TIME_HIGH_VALUE_COUNTERPARTY",
                    "matched": True,
                    "severity": "HIGH",
                    "supporting_evidence_ids": ["EV-001", "EV-002"]
                }
            ],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("UNUSUAL_HIGH_VALUE_FIRST_TIME_PAYEE", reg_codes)

    def test_9_behavioral_escalation_consumed_from_phase_2(self):
        """Test 9: Behavioral escalation indicator consumes Phase 2 pattern directly."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-ESCALATE",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "historical_behavior",
                    "category": "Origin Account Baseline",
                    "severity": "MEDIUM",
                    "data": {"deviation_ratio": 4.5}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-ESCALATE",
            "summary": {"contextual_severity": "MEDIUM"},
            "patterns": [
                {
                    "pattern_id": "BEHAVIORAL_ESCALATION",
                    "matched": True,
                    "severity": "MEDIUM",
                    "supporting_evidence_ids": ["EV-001"]
                }
            ],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("ABNORMAL_BASELINE_BEHAVIORAL_ESCALATION", reg_codes)

    def test_10_multi_hop_indicator_references_phase_2(self):
        """Test 10: Multi-hop indicator references Phase 2 pattern context."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-MULTIHOP",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "graph_network",
                    "category": "Graph Topology",
                    "severity": "HIGH",
                    "data": {"chain_depth": 2}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-MULTIHOP",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [
                {
                    "pattern_id": "MULTI_HOP_PROPAGATION",
                    "matched": True,
                    "severity": "HIGH",
                    "supporting_evidence_ids": ["EV-001"]
                }
            ],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("MULTI_HOP_ENTITY_PROPAGATION_INDICATOR", reg_codes)

    def test_11_indicator_evidence_and_context_traceability(self):
        """Test 11: Every indicator contains non-empty supporting evidence IDs and supporting context IDs."""
        tx = {
            "tx_id": "TX-TRACE-REG",
            "timestamp": "2026-09-01T14:00:00Z",
            "sender_account": "ACC-TRACE-SENDER",
            "receiver_account": "ACC-TRACE-RCVR",
            "amount": 300000.0,
            "currency": "INR",
            "channel": "NEFT",
            "is_cross_border": True
        }
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        report = assess_case_regulatory_risk(case_id, data_store)
        self.assertTrue(report["found"])
        self.assertGreater(len(report["regulatory_indicators"]), 0)

        for reg in report["regulatory_indicators"]:
            self.assertIn("id", reg)
            self.assertIn("supporting_evidence_ids", reg)
            self.assertIn("supporting_context_ids", reg)
            self.assertTrue(isinstance(reg["supporting_evidence_ids"], list))
            self.assertTrue(isinstance(reg["supporting_context_ids"], list))
            self.assertGreater(len(reg["supporting_evidence_ids"]), 0, f"Regulatory Indicator {reg['id']} missing evidence IDs")

    def test_12_no_fabricated_sanctions_or_kyc_claims(self):
        """Test 12: External sanctions/KYC claims are never fabricated (UNAVAILABLE / NOT_CHECKED)."""
        tx = {
            "tx_id": "TX-NOFAB-REG",
            "timestamp": "2026-09-01T16:00:00Z",
            "sender_account": "ACC-NOFAB-1",
            "receiver_account": "ACC-NOFAB-2",
            "amount": 100000.0,
            "currency": "INR",
            "channel": "UPI"
        }
        run_pipeline(tx, data_store)
        report = assess_transaction_regulatory_risk("TX-NOFAB-REG", data_store)

        self.assertEqual(report["jurisdiction_data_status"]["external_sanctions_database"], "UNAVAILABLE")
        self.assertEqual(report["jurisdiction_data_status"]["external_kyc_verification"], "NOT_CHECKED")

        report_str = str(report).lower()
        self.assertNotIn("interpol_matched", report_str)
        self.assertNotIn("ofac_confirmed", report_str)
        self.assertNotIn("criminal_conviction_found", report_str)

    def test_13_heuristic_index_determinism(self):
        """Test 13: Assessment heuristic index is deterministic and bounded."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-HEUR-TEST",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 200000.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-HEUR-TEST",
            "summary": {"contextual_severity": "HIGH", "confidence": 0.88},
            "patterns": [{"pattern_id": "RAPID_STRUCTURING", "matched": True}],
            "contextual_findings": []
        }
        rep1 = assess_regulatory_risk(ev_pkg, ctx_rpt)
        rep2 = assess_regulatory_risk(ev_pkg, ctx_rpt)

        self.assertEqual(rep1["summary"]["assessment_heuristic_index"], rep2["summary"]["assessment_heuristic_index"])
        self.assertGreaterEqual(rep1["summary"]["assessment_heuristic_index"], 0.0)
        self.assertLessEqual(rep1["summary"]["assessment_heuristic_index"], 1.0)

    def test_14_same_input_produces_identical_report(self):
        """Test 14: Same Phase 1 + Phase 2 input produces identical regulatory report."""
        tx = {
            "tx_id": "TX-SAME-REG",
            "timestamp": "2026-09-01T17:00:00Z",
            "sender_account": "ACC-SAME-1",
            "receiver_account": "ACC-SAME-2",
            "amount": 220000.0,
            "currency": "INR",
            "channel": "IMPS",
            "on_active_call": True
        }
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        ev_pkg = collect_evidence_for_case(case_id, data_store)
        ctx_rpt = investigate_context(ev_pkg)

        rep1 = assess_regulatory_risk(ev_pkg, ctx_rpt)
        rep2 = assess_regulatory_risk(ev_pkg, ctx_rpt)

        self.assertEqual(rep1["summary"]["regulatory_severity"], rep2["summary"]["regulatory_severity"])
        self.assertEqual(rep1["summary"]["indicator_count"], rep2["summary"]["indicator_count"])
        self.assertEqual(len(rep1["regulatory_indicators"]), len(rep2["regulatory_indicators"]))

    def test_15_regulatory_severity_explainability(self):
        """Test 15: Regulatory severity is deterministic and explainable from indicators."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-SEV-EXPLAIN",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 250000.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-SEV-EXPLAIN",
            "summary": {"contextual_severity": "HIGH", "confidence": 0.90},
            "patterns": [
                {"pattern_id": "RAPID_STRUCTURING", "matched": True},
                {"pattern_id": "MULE_ACCOUNT_DRAINAGE", "matched": True}
            ],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)

        self.assertEqual(report["summary"]["regulatory_severity"], "CRITICAL")
        self.assertGreaterEqual(report["summary"]["indicator_count"], 2)

    def test_16_context_ids_are_category_specific(self):
        """Test 16 (Hardening): Context IDs are category-specific and do not bleed across unrelated indicators."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-SPECIFIC-CTX",
            "evidence": [
                {"id": "EV-001", "type": "historical_behavior", "category": "Baseline", "data": {"deviation_ratio": 5.0}}
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-SPECIFIC-CTX",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [
                {"pattern_id": "BEHAVIORAL_ESCALATION", "matched": True}
            ],
            "contextual_findings": [
                {"id": "CTX-BEHAVIORAL", "type": "behavioral", "finding": "High baseline deviation."},
                {"id": "CTX-XBORDER", "type": "cross_border", "finding": "Unrelated cross border finding."},
                {"id": "CTX-MULE", "type": "mule", "finding": "Unrelated mule finding."}
            ]
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        behavioral_ind = next((r for r in report["regulatory_indicators"] if r["indicator_code"] == "ABNORMAL_BASELINE_BEHAVIORAL_ESCALATION"), None)
        self.assertIsNotNone(behavioral_ind)
        self.assertIn("BEHAVIORAL_ESCALATION", behavioral_ind["supporting_context_ids"])
        self.assertIn("CTX-BEHAVIORAL", behavioral_ind["supporting_context_ids"])
        self.assertNotIn("CTX-XBORDER", behavioral_ind["supporting_context_ids"])
        self.assertNotIn("CTX-MULE", behavioral_ind["supporting_context_ids"])

    def test_17_cross_border_unrelated_high_severity_does_not_trigger(self):
        """Test 17 (Hardening): Cross-border flag with unrelated HIGH severity does NOT trigger cross-border indicator."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-XBORDER-UNRELATED",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "behavioral_telemetry",
                    "data": {"active_flags": [{"flag": "is_cross_border"}]}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-XBORDER-UNRELATED",
            "summary": {"contextual_severity": "HIGH"},  # Unrelated HIGH severity
            "patterns": [],  # CROSS_BORDER_HIGH_RISK_ACTIVITY is NOT matched
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertNotIn("SUSPICIOUS_CROSS_BORDER_TELEMETRY", reg_codes)

    def test_18_cross_border_active_threat_does_trigger(self):
        """Test 18 (Hardening): Cross-border flag WITH active telemetry threat DOES trigger cross-border indicator."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-XBORDER-THREAT",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "behavioral_telemetry",
                    "data": {"active_flags": [{"flag": "is_cross_border"}, {"flag": "on_active_call"}]}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-XBORDER-THREAT",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [],
            "contextual_findings": [{"id": "CTX-TEL", "type": "telemetry", "finding": "Active call during cross-border payment."}]
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("SUSPICIOUS_CROSS_BORDER_TELEMETRY", reg_codes)

    def test_19_cross_border_pattern_does_trigger(self):
        """Test 19 (Hardening): Cross-border flag WITH CROSS_BORDER_HIGH_RISK_ACTIVITY pattern DOES trigger."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-XBORDER-PAT",
            "evidence": [
                {
                    "id": "EV-001",
                    "type": "behavioral_telemetry",
                    "data": {"active_flags": [{"flag": "is_cross_border"}]}
                }
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-XBORDER-PAT",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [{"pattern_id": "CROSS_BORDER_HIGH_RISK_ACTIVITY", "matched": True}],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("SUSPICIOUS_CROSS_BORDER_TELEMETRY", reg_codes)

    def test_20_three_txs_50k_without_high_deviation_no_structuring(self):
        """Test 20 (Hardening): 3 transactions + 50k without high deviation or pattern match does NOT trigger structuring."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-NO-STRUCT",
            "evidence": [
                {"id": "EV-001", "type": "transaction", "data": {"amount": 50000.0}},
                {"id": "EV-002", "type": "related_activity", "data": {"total_transactions": 3}},
                {"id": "EV-003", "type": "historical_behavior", "category": "Baseline", "data": {"deviation_ratio": 1.2}}
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-NO-STRUCT",
            "summary": {"contextual_severity": "LOW"},
            "patterns": [],  # RAPID_STRUCTURING not matched
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertNotIn("POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING", reg_codes)

    def test_21_three_txs_high_deviation_triggers_structuring(self):
        """Test 21 (Hardening): 3 transactions WITH deviation_ratio >= 2.0 DOES trigger structuring indicator."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-STRUCT-DEV",
            "evidence": [
                {"id": "EV-001", "type": "transaction", "data": {"amount": 50000.0}},
                {"id": "EV-002", "type": "related_activity", "data": {"total_transactions": 3}},
                {"id": "EV-003", "type": "historical_behavior", "category": "Baseline", "data": {"deviation_ratio": 3.5}}
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-STRUCT-DEV",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING", reg_codes)

    def test_22_rapid_structuring_pattern_triggers(self):
        """Test 22 (Hardening): RAPID_STRUCTURING pattern match triggers structuring regardless of amount."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-STRUCT-PAT",
            "evidence": [
                {"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-STRUCT-PAT",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [{"pattern_id": "RAPID_STRUCTURING", "matched": True}],
            "contextual_findings": []
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        reg_codes = [r["indicator_code"] for r in report["regulatory_indicators"]]
        self.assertIn("POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING", reg_codes)

    def test_23_traceability_ids_strictly_exist_in_input(self):
        """Test 23 (Hardening): Every supporting evidence ID and supporting context ID strictly exists in input."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-TRACE-VALID",
            "evidence": [
                {"id": "EV-001", "type": "historical_behavior", "category": "Baseline", "data": {"deviation_ratio": 4.0}}
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-TRACE-VALID",
            "summary": {"contextual_severity": "HIGH"},
            "patterns": [{"pattern_id": "BEHAVIORAL_ESCALATION", "matched": True}],
            "contextual_findings": [{"id": "CTX-BEH-100", "type": "behavioral", "finding": "Severe baseline deviation."}]
        }
        report = assess_regulatory_risk(ev_pkg, ctx_rpt)
        valid_ev_ids = {"EV-001"}
        valid_ctx_ids = {"BEHAVIORAL_ESCALATION", "CTX-BEH-100"}

        for reg in report["regulatory_indicators"]:
            for ev_id in reg["supporting_evidence_ids"]:
                self.assertIn(ev_id, valid_ev_ids, f"Fabricated evidence ID {ev_id} found in {reg['id']}")
            for ctx_id in reg["supporting_context_ids"]:
                self.assertIn(ctx_id, valid_ctx_ids, f"Fabricated context ID {ctx_id} found in {reg['id']}")


if __name__ == "__main__":
    unittest.main()
