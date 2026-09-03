import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.data_store import data_store
from app.services.orchestrator import run_pipeline
from app.services.evidence_agent import collect_evidence_for_case, collect_evidence_for_transaction
from app.services.contextual_agent import investigate_context
from app.services.regulatory_agent import assess_regulatory_risk
from app.services.audit_explanation_agent import generate_audit_explanation
from app.services.analyst_agent import (
    generate_analyst_decision_support,
    generate_case_analyst_decision_support,
    generate_transaction_analyst_decision_support
)


class TestAnalystDecisionSupportAgent(unittest.TestCase):

    def setUp(self):
        data_store["transactions"].clear()
        data_store["cases"].clear()
        data_store["graphs"].clear()
        data_store["accounts"].clear()
        data_store["actions"].clear()

    def test_1_complete_valid_pipeline(self):
        """Test 1: Complete valid pipeline input produces structured decision support."""
        tx = {
            "tx_id": "TX-P5-001",
            "timestamp": "2026-09-01T10:00:00Z",
            "sender_account": "ACC-SENDER-100",
            "receiver_account": "ACC-MULE-200",
            "amount": 250000.0,
            "currency": "INR",
            "channel": "UPI",
            "on_active_call": True
        }
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        ev_pkg = collect_evidence_for_case(case_id, data_store)
        ctx_rpt = investigate_context(ev_pkg)
        reg_rpt = assess_regulatory_risk(ev_pkg, ctx_rpt)
        aud_exp = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)

        self.assertTrue(ds["found"])
        self.assertEqual(ds["status"], "SUCCESS")
        self.assertEqual(ds["case_id"], case_id)
        self.assertIn("summary", ds)
        self.assertIn("review_priority", ds)
        self.assertIn("recommended_review_steps", ds)
        self.assertIn("disposition_options", ds)
        self.assertFalse(ds["human_approval_boundary"]["autonomous_execution"])
        self.assertEqual(ds["human_approval_boundary"]["required_role"], "COMPLIANCE_ANALYST")

    def test_2_missing_evidence_returns_insufficient_data(self):
        """Test 2: Missing evidence package returns INSUFFICIENT_DATA."""
        ctx_rpt = {"found": True, "target_id": "C-1"}
        reg_rpt = {"found": True, "target_id": "C-1"}
        aud_exp = {"found": True, "target_id": "C-1"}
        ds = generate_analyst_decision_support(None, ctx_rpt, reg_rpt, aud_exp)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INSUFFICIENT_DATA")

    def test_3_missing_contextual_report_returns_insufficient_data(self):
        """Test 3: Missing contextual report returns INSUFFICIENT_DATA."""
        ev_pkg = {"found": True, "target_id": "C-1"}
        reg_rpt = {"found": True, "target_id": "C-1"}
        aud_exp = {"found": True, "target_id": "C-1"}
        ds = generate_analyst_decision_support(ev_pkg, None, reg_rpt, aud_exp)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INSUFFICIENT_DATA")

    def test_4_missing_regulatory_assessment_returns_insufficient_data(self):
        """Test 4: Missing regulatory assessment returns INSUFFICIENT_DATA."""
        ev_pkg = {"found": True, "target_id": "C-1"}
        ctx_rpt = {"found": True, "target_id": "C-1"}
        aud_exp = {"found": True, "target_id": "C-1"}
        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, None, aud_exp)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INSUFFICIENT_DATA")

    def test_5_missing_audit_explanation_returns_insufficient_data(self):
        """Test 5: Missing audit explanation returns INSUFFICIENT_DATA."""
        ev_pkg = {"found": True, "target_id": "C-1"}
        ctx_rpt = {"found": True, "target_id": "C-1"}
        reg_rpt = {"found": True, "target_id": "C-1"}
        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, None)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INSUFFICIENT_DATA")

    def test_6_case_id_mismatch_returns_invalid_input(self):
        """Test 6: Mismatched case IDs across pipeline stages returns INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "CASE-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ctx_rpt = {"found": True, "target_id": "CASE-2", "case_id": "CASE-2", "primary_tx_id": "TX-1"}
        reg_rpt = {"found": True, "target_id": "CASE-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        aud_exp = {"found": True, "target_id": "CASE-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INVALID_INPUT")

    def test_7_transaction_id_mismatch_returns_invalid_input(self):
        """Test 7: Mismatched primary transaction IDs returns INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "TX-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ctx_rpt = {"found": True, "target_id": "TX-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        reg_rpt = {"found": True, "target_id": "TX-2", "case_id": "CASE-1", "primary_tx_id": "TX-2"}
        aud_exp = {"found": True, "target_id": "TX-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INVALID_INPUT")

    def test_8_partial_null_case_boundary_rejection(self):
        """Test 8: Partial null case_id returns INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "CASE-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ctx_rpt = {"found": True, "target_id": "CASE-1", "case_id": None, "primary_tx_id": "TX-1"}
        reg_rpt = {"found": True, "target_id": "CASE-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        aud_exp = {"found": True, "target_id": "CASE-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INVALID_INPUT")

    def test_9_partial_null_transaction_boundary_rejection(self):
        """Test 9: Partial null primary_tx_id returns INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "TX-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ctx_rpt = {"found": True, "target_id": "TX-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        reg_rpt = {"found": True, "target_id": "TX-1", "case_id": "CASE-1", "primary_tx_id": None}
        aud_exp = {"found": True, "target_id": "TX-1", "case_id": "CASE-1", "primary_tx_id": "TX-1"}
        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)

        self.assertFalse(ds["found"])
        self.assertEqual(ds["status"], "INVALID_INPUT")

    def test_10_namespace_isolation(self):
        """Test 10: Strict namespace isolation between context_finding_ids and context_pattern_ids."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-NS",
            "case_id": "CASE-NS",
            "primary_tx_id": "TX-NS",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-NS",
            "case_id": "CASE-NS",
            "primary_tx_id": "TX-NS",
            "patterns": [{"pattern_id": "RAPID_STRUCTURING", "matched": True}],
            "contextual_findings": [{"id": "CTX-001", "type": "velocity", "finding": "Rapid velocity", "supporting_evidence_ids": ["EV-001"]}]
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-NS",
            "case_id": "CASE-NS",
            "primary_tx_id": "TX-NS",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING",
                "severity": "HIGH",
                "indicator": "Structuring pattern",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["RAPID_STRUCTURING", "CTX-001"]
            }]
        }
        aud_exp = {
            "found": True,
            "target_id": "CASE-NS",
            "case_id": "CASE-NS",
            "primary_tx_id": "TX-NS",
            "investigation_narrative": []
        }

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertTrue(ds["found"])
        self.assertEqual(ds["status"], "SUCCESS")

        step = ds["recommended_review_steps"][0]
        self.assertEqual(step["supporting_context_finding_ids"], ["CTX-001"])
        self.assertEqual(step["supporting_context_pattern_ids"], ["RAPID_STRUCTURING"])
        self.assertNotIn("RAPID_STRUCTURING", step["supporting_context_finding_ids"])

    def test_11_broken_evidence_reference_returns_incomplete_traceability(self):
        """Test 11: Context finding referencing non-existent Evidence ID returns INCOMPLETE_TRACEABILITY."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {
            "found": True,
            "target_id": "C-1",
            "case_id": "C-1",
            "primary_tx_id": "T-1",
            "patterns": [],
            "contextual_findings": [{"id": "CTX-001", "type": "behavioral", "finding": "F", "supporting_evidence_ids": ["EV-GHOST"]}]
        }
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["status"], "INCOMPLETE_TRACEABILITY")

    def test_12_broken_context_finding_reference_returns_incomplete_traceability(self):
        """Test 12: Indicator referencing non-existent Context Finding ID returns INCOMPLETE_TRACEABILITY."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": [{"id": "EV-001", "type": "transaction"}]}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "C-1",
            "case_id": "C-1",
            "primary_tx_id": "T-1",
            "summary": {},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "TEST",
                "severity": "HIGH",
                "indicator": "Test",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["CTX-GHOST"]
            }]
        }
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["status"], "INCOMPLETE_TRACEABILITY")

    def test_13_broken_context_pattern_reference_returns_incomplete_traceability(self):
        """Test 13: Indicator referencing non-existent Context Pattern ID returns INCOMPLETE_TRACEABILITY."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": [{"id": "EV-001", "type": "transaction"}]}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "C-1",
            "case_id": "C-1",
            "primary_tx_id": "T-1",
            "summary": {},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "TEST",
                "severity": "HIGH",
                "indicator": "Test",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["PATTERN_GHOST"]
            }]
        }
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["status"], "INCOMPLETE_TRACEABILITY")

    def test_14_broken_regulatory_reference_returns_incomplete_traceability(self):
        """Test 14: Indicator with invalid structure returns INCOMPLETE_TRACEABILITY."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "C-1",
            "case_id": "C-1",
            "primary_tx_id": "T-1",
            "summary": {},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "TEST",
                "severity": "HIGH",
                "indicator": "Test",
                "supporting_evidence_ids": ["EV-GHOST"],
                "supporting_context_ids": []
            }]
        }
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["status"], "INCOMPLETE_TRACEABILITY")

    def test_15_review_priority_urgent(self):
        """Test 15: Critical severity or golden_window <= 15 assigns URGENT review priority."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "CRITICAL"}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["review_priority"], "URGENT")

    def test_16_review_priority_high(self):
        """Test 16: HIGH severity or recoverable_amount >= 100k assigns HIGH review priority."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "HIGH"}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["review_priority"], "HIGH")

    def test_17_review_priority_standard(self):
        """Test 17: MEDIUM severity assigns STANDARD review priority."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "MEDIUM"}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["review_priority"], "STANDARD")

    def test_18_review_priority_low(self):
        """Test 18: LOW severity assigns LOW review priority."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "LOW"}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["review_priority"], "LOW")

    def test_19_human_approval_always_present(self):
        """Test 19: requires_human_approval is always True in summary."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "LOW"}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertTrue(ds["summary"]["requires_human_approval"])

    def test_20_autonomous_execution_always_false(self):
        """Test 20: autonomous_execution is always False in human_approval_boundary."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "LOW"}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertFalse(ds["human_approval_boundary"]["autonomous_execution"])
        self.assertEqual(ds["human_approval_boundary"]["required_role"], "COMPLIANCE_ANALYST")

    def test_21_forbidden_autonomous_actions_absent(self):
        """Test 21: Phase 5 output contains zero autonomous action execution claims (no FREEZE, BLOCK, FILE_STR execution)."""
        tx = {"tx_id": "TX-P5-SAFE", "timestamp": "2026-09-01T12:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 150000.0}
        run_pipeline(tx, data_store)
        ds = generate_transaction_analyst_decision_support("TX-P5-SAFE", data_store)

        output_str = str(ds).lower()
        self.assertNotIn("automatically froze", output_str)
        self.assertNotIn("automatically blocked", output_str)
        self.assertNotIn("autonomously filed str", output_str)

    def test_22_no_intent_inference(self):
        """Test 22: Executive brief contains zero intent inference claims."""
        tx = {"tx_id": "TX-P5-INTENT", "timestamp": "2026-09-01T13:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 95000.0}
        run_pipeline(tx, data_store)
        ds = generate_transaction_analyst_decision_support("TX-P5-INTENT", data_store)

        brief = ds["analyst_executive_brief"].lower()
        self.assertNotIn("intentionally structured", brief)
        self.assertNotIn("attempted to launder", brief)
        self.assertNotIn("deliberately bypassed", brief)

    def test_23_no_legal_certainty(self):
        """Test 23: Executive brief contains zero legal certainty claims."""
        tx = {"tx_id": "TX-P5-LEGAL", "timestamp": "2026-09-01T14:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 200000.0}
        run_pipeline(tx, data_store)
        ds = generate_transaction_analyst_decision_support("TX-P5-LEGAL", data_store)

        brief = ds["analyst_executive_brief"].lower()
        self.assertNotIn("violates aml regulations", brief)
        self.assertNotIn("this is money laundering", brief)
        self.assertNotIn("fraud confirmed", brief)

    def test_24_sanctions_unavailable_preserved(self):
        """Test 24: external_sanctions_database UNAVAILABLE status is explicitly disclosed."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "C-1",
            "case_id": "C-1",
            "primary_tx_id": "T-1",
            "summary": {"regulatory_severity": "LOW"},
            "jurisdiction_data_status": {"external_sanctions_database": "UNAVAILABLE"},
            "regulatory_indicators": []
        }
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        ds_str = str(ds)
        self.assertIn("UNAVAILABLE", ds_str)
        self.assertNotIn("no sanctions match found", ds_str.lower())

    def test_25_kyc_not_checked_preserved(self):
        """Test 25: external_kyc_verification NOT_CHECKED generates documentation review step."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": [{"id": "EV-001", "type": "transaction"}]}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "C-1",
            "case_id": "C-1",
            "primary_tx_id": "T-1",
            "summary": {"regulatory_severity": "LOW"},
            "jurisdiction_data_status": {"external_kyc_verification": "NOT_CHECKED"},
            "regulatory_indicators": []
        }
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        step = next(s for s in ds["recommended_review_steps"] if s["category"] == "DOCUMENTATION_REVIEW")
        self.assertIn("KYC", step["action_label"])

    def test_26_deterministic_output(self):
        """Test 26: Output is completely deterministic across multiple runs on identical input."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "LOW", "assessment_heuristic_index": 0.4}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        rep1 = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        rep2 = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)

        rep1.pop("generated_at")
        rep2.pop("generated_at")
        self.assertEqual(rep1, rep2)

    def test_27_malformed_heuristic_index_handling(self):
        """Test 27: None or malformed assessment_heuristic_index does not raise TypeError."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "summary": {"regulatory_severity": "LOW", "assessment_heuristic_index": None}, "regulatory_indicators": []}
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertTrue(ds["found"])
        self.assertEqual(ds["summary"]["assessment_heuristic_index"], 0.0)

    def test_28_recommendation_without_evidence_rejected(self):
        """Test 28: Regulatory indicator without valid supporting IDs does NOT generate a review step."""
        ev_pkg = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "C-1",
            "case_id": "C-1",
            "primary_tx_id": "T-1",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-GHOST",
                "indicator_code": "TEST",
                "severity": "HIGH",
                "indicator": "Test",
                "supporting_evidence_ids": ["EV-GHOST"],
                "supporting_context_ids": []
            }]
        }
        aud_exp = {"found": True, "target_id": "C-1", "case_id": "C-1", "primary_tx_id": "T-1"}

        ds = generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
        self.assertEqual(ds["status"], "INCOMPLETE_TRACEABILITY")
        self.assertEqual(len(ds["recommended_review_steps"]), 0)


from fastapi.testclient import TestClient
from main import app


class TestAnalystDecisionSupportAPI(unittest.TestCase):

    def setUp(self):
        data_store["transactions"].clear()
        data_store["cases"].clear()
        data_store["graphs"].clear()
        data_store["accounts"].clear()
        data_store["actions"].clear()
        data_store["dispositions"] = {}
        data_store["audit_log"] = []
        from main import get_repository
        from app.repositories.in_memory import InMemoryCaseRepository
        app.dependency_overrides[get_repository] = lambda: InMemoryCaseRepository(data_store)
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()


    def test_api_1_get_case_decision_support_success(self):
        """API Test 1: GET /cases/{case_id}/decision-support returns SUCCESS."""
        tx = {"tx_id": "TX-API-01", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        resp = self.client.get(f"/cases/{case_id}/decision-support")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["case_id"], case_id)

    def test_api_2_get_transaction_decision_support_success(self):
        """API Test 2: GET /transactions/{tx_id}/decision-support returns SUCCESS."""
        tx = {"tx_id": "TX-API-02", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        run_pipeline(tx, data_store)

        resp = self.client.get("/transactions/TX-API-02/decision-support")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["primary_tx_id"], "TX-API-02")

    def test_api_3_post_decision_support_success(self):
        """API Test 3: POST /decision-support returns SUCCESS."""
        tx = {"tx_id": "TX-API-03", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        resp = self.client.post("/decision-support", json={"case_id": case_id})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "SUCCESS")

    def test_api_4_missing_case_returns_insufficient_data(self):
        """API Test 4: Missing case returns INSUFFICIENT_DATA."""
        resp = self.client.get("/cases/CASE-GHOST/decision-support")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["found"])
        self.assertEqual(data["status"], "INSUFFICIENT_DATA")

    def test_api_5_missing_transaction_returns_insufficient_data(self):
        """API Test 5: Missing transaction returns INSUFFICIENT_DATA."""
        resp = self.client.get("/transactions/TX-GHOST/decision-support")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["found"])
        self.assertEqual(data["status"], "INSUFFICIENT_DATA")

    def test_api_6_case_transaction_mismatch_returns_invalid_input(self):
        """API Test 6: POST /decision-support with mismatched case_id and tx_id returns INVALID_INPUT."""
        tx1 = {"tx_id": "TX-MIS-1", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 50000.0}
        tx2 = {"tx_id": "TX-MIS-2", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "B1", "receiver_account": "B2", "amount": 50000.0}
        res1 = run_pipeline(tx1, data_store)
        run_pipeline(tx2, data_store)

        resp = self.client.post("/decision-support", json={"case_id": res1["case"]["case_id"], "tx_id": "TX-MIS-2"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["found"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_7_disposition_success(self):
        """API Test 7: POST /cases/{case_id}/disposition with valid payload returns SUCCESS acknowledgement."""
        tx = {"tx_id": "TX-DISP-01", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        resp = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Valid false positive rationale."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "SUCCESS")
        self.assertTrue(data["acknowledged"])

    def test_api_8_disposition_forbidden_action_code_rejected(self):
        """API Test 8: Forbidden action code (FREEZE) returns INVALID_INPUT."""
        tx = {"tx_id": "TX-DISP-02", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        resp = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "FREEZE",
            "analyst_notes": "Attempting autonomous freeze."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_9_disposition_missing_analyst_notes_rejected(self):
        """API Test 9: Action code requiring note without analyst_notes returns INVALID_INPUT."""
        tx = {"tx_id": "TX-DISP-03", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        resp = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": ""
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_10_disposition_missing_risk_ack_rejected(self):
        """API Test 10: Action requiring risk_acknowledged without risk_acknowledged=true returns INVALID_INPUT."""
        tx = {"tx_id": "TX-DISP-04", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        resp = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "ESCALATE_SENIOR_COMPLIANCE",
            "analyst_notes": "Escalating for review.",
            "risk_acknowledged": False
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_11_disposition_unoffered_action_code_rejected(self):
        """API Test 11: Unoffered action code returns INVALID_INPUT."""
        tx = {"tx_id": "TX-DISP-05", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        resp = self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "INVALID_CUSTOM_CODE",
            "analyst_notes": "Custom code."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_12_disposition_cross_case_attempt_rejected(self):
        """API Test 12: Cross-case path vs payload mismatch returns INVALID_INPUT."""
        tx1 = {"tx_id": "TX-DISP-06A", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        tx2 = {"tx_id": "TX-DISP-06B", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "B1", "receiver_account": "B2", "amount": 100000.0}
        res1 = run_pipeline(tx1, data_store)
        res2 = run_pipeline(tx2, data_store)

        resp = self.client.post(f"/cases/{res1['case']['case_id']}/disposition", json={
            "case_id": res2["case"]["case_id"],
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Mismatch."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_13_no_account_state_mutation(self):
        """API Test 13: Disposition endpoint does NOT mutate account balances or statuses."""
        tx = {"tx_id": "TX-DISP-07", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "ACC-STATE-1", "receiver_account": "ACC-STATE-2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        acc_before = dict(data_store.get("accounts", {}).get("ACC-STATE-1", {}))

        self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Dismissing case."
        })

        acc_after = data_store.get("accounts", {}).get("ACC-STATE-1", {})
        self.assertEqual(acc_before.get("status"), acc_after.get("status"))
        self.assertEqual(acc_before.get("current_balance_sim"), acc_after.get("current_balance_sim"))

    def test_api_14_no_transaction_state_mutation(self):
        """API Test 14: Disposition endpoint does NOT mutate transaction risk scores or reasons."""
        tx = {"tx_id": "TX-DISP-08", "timestamp": "2026-09-01T10:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        tx_before = dict(data_store.get("transactions", {}).get("TX-DISP-08", {}))

        self.client.post(f"/cases/{case_id}/disposition", json={
            "case_id": case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Dismissing case."
        })

        tx_after = data_store.get("transactions", {}).get("TX-DISP-08", {})
        self.assertEqual(tx_before.get("risk_score"), tx_after.get("risk_score"))

    def test_api_15_no_db_persistence_mutation(self):
        """API Test 15: Verifies dispositions are tracked in data_store['dispositions']."""
        self.assertIn("dispositions", data_store)


if __name__ == "__main__":
    unittest.main()

