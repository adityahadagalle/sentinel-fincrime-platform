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
from app.services.audit_explanation_agent import (
    generate_audit_explanation,
    generate_case_audit_explanation,
    generate_transaction_audit_explanation
)


class TestAuditExplanationAgent(unittest.TestCase):

    def setUp(self):
        data_store["transactions"].clear()
        data_store["cases"].clear()
        data_store["graphs"].clear()
        data_store["accounts"].clear()
        data_store["actions"].clear()

    def test_1_complete_valid_pipeline(self):
        """Test 1: Complete valid pipeline produces structured audit explanation."""
        tx = {
            "tx_id": "TX-AUD-001",
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
        audit_rpt = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertTrue(audit_rpt["found"])
        self.assertEqual(audit_rpt["status"], "SUCCESS")
        self.assertEqual(audit_rpt["case_id"], case_id)
        self.assertIn("executive_summary", audit_rpt)
        self.assertGreater(len(audit_rpt["investigation_narrative"]), 0)
        self.assertGreater(len(audit_rpt["key_findings"]), 0)
        self.assertIn("audit_trail", audit_rpt)

    def test_2_missing_evidence_returns_insufficient_data(self):
        """Test 2: Missing evidence package returns INSUFFICIENT_DATA."""
        ctx_rpt = {"found": True, "target_id": "CASE-100"}
        reg_rpt = {"found": True, "target_id": "CASE-100"}
        audit = generate_audit_explanation(None, ctx_rpt, reg_rpt)

        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INSUFFICIENT_DATA")

    def test_3_missing_contextual_report_returns_insufficient_data(self):
        """Test 3: Missing contextual report returns INSUFFICIENT_DATA."""
        ev_pkg = {"found": True, "target_id": "CASE-100", "evidence": []}
        reg_rpt = {"found": True, "target_id": "CASE-100"}
        audit = generate_audit_explanation(ev_pkg, None, reg_rpt)

        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INSUFFICIENT_DATA")

    def test_4_missing_regulatory_assessment_returns_insufficient_data(self):
        """Test 4: Missing regulatory assessment returns INSUFFICIENT_DATA."""
        ev_pkg = {"found": True, "target_id": "CASE-100", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-100"}
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, None)

        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INSUFFICIENT_DATA")

    def test_5_valid_case_zero_regulatory_indicators(self):
        """Test 5: Valid case with zero regulatory indicators returns SUCCESS with explanation stating no indicators detected."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-ZERO",
            "case_id": "CASE-ZERO",
            "primary_tx_id": "TX-ZERO",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 50.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-ZERO",
            "case_id": "CASE-ZERO",
            "primary_tx_id": "TX-ZERO",
            "summary": {"contextual_severity": "LOW", "confidence": 0.5},
            "patterns": [],
            "contextual_findings": []
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-ZERO",
            "case_id": "CASE-ZERO",
            "primary_tx_id": "TX-ZERO",
            "summary": {"regulatory_severity": "LOW", "assessment_heuristic_index": 0.4, "indicator_count": 0},
            "jurisdiction_data_status": {"external_sanctions_database": "UNAVAILABLE", "external_kyc_verification": "NOT_CHECKED"},
            "regulatory_indicators": [],
            "compliance_considerations": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertIn("NO regulatory indicators were detected", audit["executive_summary"])

    def test_6_evidence_ids_preserved(self):
        """Test 6: Evidence IDs are correctly preserved in narrative steps and key findings."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-EV-PRESERVE",
            "case_id": "CASE-EV-PRESERVE",
            "primary_tx_id": "TX-PRESERVE",
            "evidence": [{"id": "EV-999", "type": "transaction", "data": {"amount": 1000.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-EV-PRESERVE",
            "case_id": "CASE-EV-PRESERVE",
            "primary_tx_id": "TX-PRESERVE",
            "patterns": [],
            "contextual_findings": [{"id": "CTX-001", "type": "behavioral", "finding": "Test finding", "supporting_evidence_ids": ["EV-999"]}]
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-EV-PRESERVE",
            "case_id": "CASE-EV-PRESERVE",
            "primary_tx_id": "TX-PRESERVE",
            "summary": {"regulatory_severity": "LOW", "assessment_heuristic_index": 0.4},
            "regulatory_indicators": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        narrative_ev_ids = [eid for step in audit["investigation_narrative"] for eid in step["evidence_ids"]]
        self.assertIn("EV-999", narrative_ev_ids)

    def test_7_context_finding_ids_preserved(self):
        """Test 7: Context finding IDs (CTX-XXX) are correctly preserved in context_finding_ids."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-CTX-PRESERVE",
            "case_id": "CASE-CTX-PRESERVE",
            "primary_tx_id": "TX-CTX-PRESERVE",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-CTX-PRESERVE",
            "case_id": "CASE-CTX-PRESERVE",
            "primary_tx_id": "TX-CTX-PRESERVE",
            "patterns": [],
            "contextual_findings": [{"id": "CTX-777", "type": "behavioral", "finding": "Baseline anomaly", "supporting_evidence_ids": ["EV-001"]}]
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-CTX-PRESERVE",
            "case_id": "CASE-CTX-PRESERVE",
            "primary_tx_id": "TX-CTX-PRESERVE",
            "summary": {"regulatory_severity": "LOW"},
            "regulatory_indicators": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        narrative_ctx_finding_ids = [cid for step in audit["investigation_narrative"] for cid in step["context_finding_ids"]]
        self.assertIn("CTX-777", narrative_ctx_finding_ids)

    def test_8_regulatory_ids_preserved(self):
        """Test 8: Regulatory IDs are correctly preserved in narrative steps and key findings."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-REG-PRESERVE",
            "case_id": "CASE-REG-PRESERVE",
            "primary_tx_id": "TX-REG-PRESERVE",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-REG-PRESERVE",
            "case_id": "CASE-REG-PRESERVE",
            "primary_tx_id": "TX-REG-PRESERVE",
            "patterns": [{"pattern_id": "BEHAVIORAL_ESCALATION", "matched": True}],
            "contextual_findings": []
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-REG-PRESERVE",
            "case_id": "CASE-REG-PRESERVE",
            "primary_tx_id": "TX-REG-PRESERVE",
            "summary": {"regulatory_severity": "MEDIUM", "assessment_heuristic_index": 0.6},
            "regulatory_indicators": [{
                "id": "REG-555",
                "indicator_code": "ABNORMAL_BASELINE_BEHAVIORAL_ESCALATION",
                "severity": "MEDIUM",
                "indicator": "Behavioral escalation",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["BEHAVIORAL_ESCALATION"]
            }]
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        narrative_reg_ids = [rid for step in audit["investigation_narrative"] for rid in step["regulatory_ids"]]
        self.assertIn("REG-555", narrative_reg_ids)

    def test_9_no_fabricated_ids(self):
        """Test 9: No fabricated IDs exist in audit explanation output."""
        tx = {
            "tx_id": "TX-NOFAB-AUD",
            "timestamp": "2026-09-01T11:00:00Z",
            "sender_account": "ACC-1",
            "receiver_account": "ACC-2",
            "amount": 50000.0
        }
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        audit = generate_case_audit_explanation(case_id, data_store)
        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertEqual(len(audit["unresolved_references"]), 0)

    def test_10_broken_evidence_reference_returns_incomplete_traceability(self):
        """Test 10: Context finding referencing non-existent Evidence ID returns INCOMPLETE_TRACEABILITY."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-BROKEN-EV",
            "case_id": "CASE-BROKEN-EV",
            "primary_tx_id": "TX-BROKEN-EV",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-BROKEN-EV",
            "case_id": "CASE-BROKEN-EV",
            "primary_tx_id": "TX-BROKEN-EV",
            "patterns": [],
            "contextual_findings": [{"id": "CTX-001", "type": "behavioral", "finding": "Test", "supporting_evidence_ids": ["EV-NONEXISTENT"]}]
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-BROKEN-EV",
            "case_id": "CASE-BROKEN-EV",
            "primary_tx_id": "TX-BROKEN-EV",
            "summary": {"regulatory_severity": "LOW"},
            "regulatory_indicators": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertEqual(audit["status"], "INCOMPLETE_TRACEABILITY")
        self.assertGreater(len(audit["unresolved_references"]), 0)

    def test_11_broken_context_reference_returns_incomplete_traceability(self):
        """Test 11: Regulatory indicator referencing non-existent Context ID returns INCOMPLETE_TRACEABILITY."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-BROKEN-CTX",
            "case_id": "CASE-BROKEN-CTX",
            "primary_tx_id": "TX-BROKEN-CTX",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-BROKEN-CTX",
            "case_id": "CASE-BROKEN-CTX",
            "primary_tx_id": "TX-BROKEN-CTX",
            "patterns": [],
            "contextual_findings": []
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-BROKEN-CTX",
            "case_id": "CASE-BROKEN-CTX",
            "primary_tx_id": "TX-BROKEN-CTX",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "TEST_IND",
                "severity": "HIGH",
                "indicator": "Test",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["CTX-NONEXISTENT"]
            }]
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertEqual(audit["status"], "INCOMPLETE_TRACEABILITY")
        self.assertIn("CTX-NONEXISTENT", audit["unresolved_references"][0])

    def test_12_broken_regulatory_reference(self):
        """Test 12: Broken reference in indicator returns INCOMPLETE_TRACEABILITY."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-BROKEN-REG",
            "case_id": "CASE-BROKEN-REG",
            "primary_tx_id": "TX-BROKEN-REG",
            "evidence": []
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-BROKEN-REG",
            "case_id": "CASE-BROKEN-REG",
            "primary_tx_id": "TX-BROKEN-REG",
            "patterns": [],
            "contextual_findings": []
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-BROKEN-REG",
            "case_id": "CASE-BROKEN-REG",
            "primary_tx_id": "TX-BROKEN-REG",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "TEST",
                "severity": "HIGH",
                "indicator": "Test",
                "supporting_evidence_ids": ["EV-GHOST"],
                "supporting_context_ids": []
            }]
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertEqual(audit["status"], "INCOMPLETE_TRACEABILITY")

    def test_13_case_id_mismatch_returns_invalid_input(self):
        """Test 13: Mismatched case IDs across pipeline stages returns INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "CASE-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}
        ctx_rpt = {"found": True, "target_id": "CASE-002", "case_id": "CASE-002", "primary_tx_id": "TX-001"}
        reg_rpt = {"found": True, "target_id": "CASE-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INVALID_INPUT")

    def test_14_transaction_id_mismatch_returns_invalid_input(self):
        """Test 14: Mismatched primary transaction IDs returns INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "TX-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}
        ctx_rpt = {"found": True, "target_id": "TX-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}
        reg_rpt = {"found": True, "target_id": "TX-002", "case_id": "CASE-001", "primary_tx_id": "TX-002"}
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INVALID_INPUT")

    def test_15_severity_preserved_exactly(self):
        """Test 15: Regulatory severity is preserved exactly from Phase 3 without recalculation."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-SEV",
            "case_id": "CASE-SEV",
            "primary_tx_id": "TX-SEV",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-SEV",
            "case_id": "CASE-SEV",
            "primary_tx_id": "TX-SEV",
            "patterns": [],
            "contextual_findings": []
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-SEV",
            "case_id": "CASE-SEV",
            "primary_tx_id": "TX-SEV",
            "summary": {"regulatory_severity": "HIGH", "assessment_heuristic_index": 0.8},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "TEST",
                "severity": "HIGH",
                "indicator": "Test indicator",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": []
            }]
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertEqual(audit["summary"]["regulatory_severity"], "HIGH")
        kf = next(k for k in audit["key_findings"] if k["finding_id"] == "KF-001")
        self.assertEqual(kf["severity"], "HIGH")

    def test_16_heuristic_index_preserved_exactly(self):
        """Test 16: Heuristic Index is preserved exactly from Phase 3."""
        ev_pkg = {"found": True, "target_id": "CASE-HEUR", "case_id": "CASE-HEUR", "primary_tx_id": "TX-HEUR", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-HEUR", "case_id": "CASE-HEUR", "primary_tx_id": "TX-HEUR", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-HEUR",
            "case_id": "CASE-HEUR",
            "primary_tx_id": "TX-HEUR",
            "summary": {"regulatory_severity": "HIGH", "assessment_heuristic_index": 0.83},
            "regulatory_indicators": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        self.assertEqual(audit["summary"]["assessment_heuristic_index"], 0.83)

    def test_17_unavailable_sanctions_data_disclosed(self):
        """Test 17: Unavailable sanctions database status is explicitly disclosed."""
        ev_pkg = {"found": True, "target_id": "CASE-SANC", "case_id": "CASE-SANC", "primary_tx_id": "TX-SANC", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-SANC", "case_id": "CASE-SANC", "primary_tx_id": "TX-SANC", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-SANC",
            "case_id": "CASE-SANC",
            "primary_tx_id": "TX-SANC",
            "summary": {"regulatory_severity": "LOW"},
            "jurisdiction_data_status": {"external_sanctions_database": "UNAVAILABLE"},
            "regulatory_indicators": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        audit_str = str(audit)
        self.assertIn("UNAVAILABLE", audit_str)
        self.assertIn("sanctions", audit_str.lower())

    def test_18_kyc_not_checked_disclosed(self):
        """Test 18: KYC NOT_CHECKED status is explicitly disclosed."""
        ev_pkg = {"found": True, "target_id": "CASE-KYC", "case_id": "CASE-KYC", "primary_tx_id": "TX-KYC", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-KYC", "case_id": "CASE-KYC", "primary_tx_id": "TX-KYC", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-KYC",
            "case_id": "CASE-KYC",
            "primary_tx_id": "TX-KYC",
            "summary": {"regulatory_severity": "LOW"},
            "jurisdiction_data_status": {"external_kyc_verification": "NOT_CHECKED"},
            "regulatory_indicators": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        audit_str = str(audit)
        self.assertIn("NOT_CHECKED", audit_str)

    def test_19_no_unsupported_legal_claims(self):
        """Test 19: Output contains zero unsupported legal certainty claims."""
        tx = {"tx_id": "TX-LEGAL-CLAIMS", "timestamp": "2026-09-01T12:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 90000.0}
        run_pipeline(tx, data_store)
        audit = generate_transaction_audit_explanation("TX-LEGAL-CLAIMS", data_store)

        output_str = str(audit).lower()
        self.assertNotIn("violates aml regulations", output_str)
        self.assertNotIn("this is money laundering", output_str)
        self.assertNotIn("an str must be filed", output_str)
        self.assertNotIn("the entity is sanctioned", output_str)

    def test_20_no_intent_inference(self):
        """Test 20: Output contains zero intent inference claims."""
        tx = {"tx_id": "TX-INTENT-CHECK", "timestamp": "2026-09-01T13:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 95000.0}
        run_pipeline(tx, data_store)
        audit = generate_transaction_audit_explanation("TX-INTENT-CHECK", data_store)

        output_str = str(audit).lower()
        self.assertNotIn("intentionally structured", output_str)
        self.assertNotIn("attempted to launder", output_str)
        self.assertNotIn("deliberately bypassed", output_str)

    def test_21_deterministic_output(self):
        """Test 21: Output is completely deterministic across multiple runs on identical input."""
        ev_pkg = {"found": True, "target_id": "CASE-DETERM", "case_id": "CASE-DETERM", "primary_tx_id": "TX-DETERM", "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]}
        ctx_rpt = {"found": True, "target_id": "CASE-DETERM", "case_id": "CASE-DETERM", "primary_tx_id": "TX-DETERM", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "CASE-DETERM", "case_id": "CASE-DETERM", "primary_tx_id": "TX-DETERM", "summary": {"regulatory_severity": "LOW", "assessment_heuristic_index": 0.4}, "regulatory_indicators": []}

        rep1 = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        rep2 = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

        # Ignore generated_at timestamp
        rep1.pop("generated_at")
        rep2.pop("generated_at")
        self.assertEqual(rep1, rep2)

    def test_22_no_action_recommendation_generation(self):
        """Test 22: Phase 4 does NOT generate autonomous action recommendations (no BLOCK, FREEZE, CLOSE, FILE STR)."""
        ev_pkg = {"found": True, "target_id": "CASE-NOACTION", "case_id": "CASE-NOACTION", "primary_tx_id": "TX-NOACTION", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-NOACTION", "case_id": "CASE-NOACTION", "primary_tx_id": "TX-NOACTION", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "CASE-NOACTION", "case_id": "CASE-NOACTION", "primary_tx_id": "TX-NOACTION", "summary": {"regulatory_severity": "HIGH"}, "regulatory_indicators": []}

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        for kf in audit["key_findings"]:
            self.assertNotIn(kf.get("statement", ""), ["BLOCK", "FREEZE", "CLOSE", "FILE STR"])

    def test_23_case_boundary_preservation(self):
        """Test 23: Case boundary is strictly preserved."""
        tx = {"tx_id": "TX-BOUND-01", "timestamp": "2026-09-01T14:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 50000.0}
        res = run_pipeline(tx, data_store)
        case_id = res["case"]["case_id"]

        audit = generate_case_audit_explanation(case_id, data_store)
        self.assertEqual(audit["case_id"], case_id)

    def test_24_empty_contextual_findings_handled(self):
        """Test 24: Empty contextual findings handled cleanly."""
        ev_pkg = {"found": True, "target_id": "CASE-EMPTY-CTX", "case_id": "CASE-EMPTY-CTX", "primary_tx_id": "TX-EMPTY-CTX", "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]}
        ctx_rpt = {"found": True, "target_id": "CASE-EMPTY-CTX", "case_id": "CASE-EMPTY-CTX", "primary_tx_id": "TX-EMPTY-CTX", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "CASE-EMPTY-CTX", "case_id": "CASE-EMPTY-CTX", "primary_tx_id": "TX-EMPTY-CTX", "summary": {"regulatory_severity": "LOW"}, "regulatory_indicators": []}

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")

    def test_25_empty_regulatory_indicators_handled(self):
        """Test 25: Empty regulatory indicators handled cleanly."""
        ev_pkg = {"found": True, "target_id": "CASE-EMPTY-REG", "case_id": "CASE-EMPTY-REG", "primary_tx_id": "TX-EMPTY-REG", "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]}
        ctx_rpt = {"found": True, "target_id": "CASE-EMPTY-REG", "case_id": "CASE-EMPTY-REG", "primary_tx_id": "TX-EMPTY-REG", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "CASE-EMPTY-REG", "case_id": "CASE-EMPTY-REG", "primary_tx_id": "TX-EMPTY-REG", "summary": {"regulatory_severity": "LOW"}, "regulatory_indicators": []}

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")

    def test_26_multiple_regulatory_indicators_maintain_separate_traceability(self):
        """Test 26: Multiple regulatory indicators maintain separate category-specific traceability."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-MULTI-REG",
            "case_id": "CASE-MULTI-REG",
            "primary_tx_id": "TX-MULTI-REG",
            "evidence": [
                {"id": "EV-001", "type": "transaction", "data": {"amount": 200000.0}},
                {"id": "EV-002", "type": "historical_behavior", "category": "Baseline", "data": {"deviation_ratio": 5.0}}
            ]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-MULTI-REG",
            "case_id": "CASE-MULTI-REG",
            "primary_tx_id": "TX-MULTI-REG",
            "patterns": [
                {"pattern_id": "RAPID_STRUCTURING", "matched": True},
                {"pattern_id": "BEHAVIORAL_ESCALATION", "matched": True}
            ],
            "contextual_findings": [
                {"id": "CTX-001", "type": "velocity", "finding": "Rapid velocity", "supporting_evidence_ids": ["EV-001"]},
                {"id": "CTX-002", "type": "behavioral", "finding": "High baseline deviation", "supporting_evidence_ids": ["EV-002"]}
            ]
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-MULTI-REG",
            "case_id": "CASE-MULTI-REG",
            "primary_tx_id": "TX-MULTI-REG",
            "summary": {"regulatory_severity": "CRITICAL", "assessment_heuristic_index": 0.95},
            "regulatory_indicators": [
                {
                    "id": "REG-001",
                    "indicator_code": "POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING",
                    "severity": "HIGH",
                    "indicator": "Structuring pattern detected.",
                    "supporting_evidence_ids": ["EV-001"],
                    "supporting_context_ids": ["RAPID_STRUCTURING", "CTX-001"]
                },
                {
                    "id": "REG-002",
                    "indicator_code": "ABNORMAL_BASELINE_BEHAVIORAL_ESCALATION",
                    "severity": "MEDIUM",
                    "indicator": "Behavioral escalation detected.",
                    "supporting_evidence_ids": ["EV-002"],
                    "supporting_context_ids": ["BEHAVIORAL_ESCALATION", "CTX-002"]
                }
            ]
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertEqual(len(audit["key_findings"]), 5)  # 2 REG + 2 CTX + 1 LIMITATION

    # --- HARDENING TESTS A THROUGH G ---

    def test_a_none_heuristic_index_handling(self):
        """Test A: None heuristic index does not raise TypeError and defaults safely to 0.0."""
        ev_pkg = {"found": True, "target_id": "CASE-NONE-HEUR", "case_id": "CASE-NONE-HEUR", "primary_tx_id": "TX-NONE-HEUR", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-NONE-HEUR", "case_id": "CASE-NONE-HEUR", "primary_tx_id": "TX-NONE-HEUR", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-NONE-HEUR",
            "case_id": "CASE-NONE-HEUR",
            "primary_tx_id": "TX-NONE-HEUR",
            "summary": {"regulatory_severity": "LOW", "assessment_heuristic_index": None},
            "regulatory_indicators": []
        }
        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertEqual(audit["summary"]["assessment_heuristic_index"], 0.0)

    def test_b_partial_none_case_id_boundary_rejection(self):
        """Test B: Partial None case_id across packages MUST return INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "CASE-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}
        ctx_rpt = {"found": True, "target_id": "CASE-001", "case_id": None, "primary_tx_id": "TX-001"}
        reg_rpt = {"found": True, "target_id": "CASE-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INVALID_INPUT")

    def test_c_context_finding_vs_pattern_namespace_isolation(self):
        """Test C: Context finding IDs (CTX-XXX) and Context pattern IDs are strictly separated into context_finding_ids and context_pattern_ids."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-NS-ISO",
            "case_id": "CASE-NS-ISO",
            "primary_tx_id": "TX-NS-ISO",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100000.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-NS-ISO",
            "case_id": "CASE-NS-ISO",
            "primary_tx_id": "TX-NS-ISO",
            "patterns": [{"pattern_id": "CROSS_BORDER_HIGH_RISK_ACTIVITY", "pattern_name": "Telemetry Risk", "matched": True, "description": "High risk signal"}],
            "contextual_findings": [{"id": "CTX-002", "type": "telemetry", "finding": "Signal detected", "supporting_evidence_ids": ["EV-001"]}]
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-NS-ISO",
            "case_id": "CASE-NS-ISO",
            "primary_tx_id": "TX-NS-ISO",
            "summary": {"regulatory_severity": "HIGH", "assessment_heuristic_index": 0.8},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "SUSPICIOUS_CROSS_BORDER_TELEMETRY",
                "severity": "HIGH",
                "indicator": "Cross border threat",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["CROSS_BORDER_HIGH_RISK_ACTIVITY", "CTX-002"]
            }]
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")

        reg_step = next(s for s in audit["investigation_narrative"] if s["stage"] == "REGULATORY")
        self.assertEqual(reg_step["context_finding_ids"], ["CTX-002"])
        self.assertEqual(reg_step["context_pattern_ids"], ["CROSS_BORDER_HIGH_RISK_ACTIVITY"])
        self.assertNotIn("CROSS_BORDER_HIGH_RISK_ACTIVITY", reg_step["context_finding_ids"])

    def test_d_pattern_only_context(self):
        """Test D: Regulatory indicator referencing a pattern only does not fabricate a CTX finding."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-PAT-ONLY",
            "case_id": "CASE-PAT-ONLY",
            "primary_tx_id": "TX-PAT-ONLY",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-PAT-ONLY",
            "case_id": "CASE-PAT-ONLY",
            "primary_tx_id": "TX-PAT-ONLY",
            "patterns": [{"pattern_id": "RAPID_STRUCTURING", "pattern_name": "Structuring", "matched": True}],
            "contextual_findings": []
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-PAT-ONLY",
            "case_id": "CASE-PAT-ONLY",
            "primary_tx_id": "TX-PAT-ONLY",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING",
                "severity": "HIGH",
                "indicator": "Structuring",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["RAPID_STRUCTURING"]
            }]
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertEqual(audit["status"], "SUCCESS")
        reg_step = next(s for s in audit["investigation_narrative"] if s["stage"] == "REGULATORY")
        self.assertEqual(reg_step["context_finding_ids"], [])
        self.assertEqual(reg_step["context_pattern_ids"], ["RAPID_STRUCTURING"])

    def test_e_multiple_context_findings_and_patterns(self):
        """Test E: Multiple context findings and pattern IDs remain distinctly separated."""
        ev_pkg = {
            "found": True,
            "target_id": "CASE-MULTI-SEP",
            "case_id": "CASE-MULTI-SEP",
            "primary_tx_id": "TX-MULTI-SEP",
            "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]
        }
        ctx_rpt = {
            "found": True,
            "target_id": "CASE-MULTI-SEP",
            "case_id": "CASE-MULTI-SEP",
            "primary_tx_id": "TX-MULTI-SEP",
            "patterns": [
                {"pattern_id": "BEHAVIORAL_ESCALATION", "matched": True},
                {"pattern_id": "RAPID_STRUCTURING", "matched": True}
            ],
            "contextual_findings": [
                {"id": "CTX-001", "type": "behavioral", "finding": "Finding 1", "supporting_evidence_ids": ["EV-001"]},
                {"id": "CTX-002", "type": "velocity", "finding": "Finding 2", "supporting_evidence_ids": ["EV-001"]}
            ]
        }
        reg_rpt = {
            "found": True,
            "target_id": "CASE-MULTI-SEP",
            "case_id": "CASE-MULTI-SEP",
            "primary_tx_id": "TX-MULTI-SEP",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "MULTI_IND",
                "severity": "HIGH",
                "indicator": "Multi indicator",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["CTX-001", "CTX-002", "BEHAVIORAL_ESCALATION", "RAPID_STRUCTURING"]
            }]
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertEqual(audit["status"], "SUCCESS")
        kf = next(k for k in audit["key_findings"] if k["finding_id"] == "KF-001")
        self.assertEqual(set(kf["supporting_context_finding_ids"]), {"CTX-001", "CTX-002"})
        self.assertEqual(set(kf["supporting_context_pattern_ids"]), {"BEHAVIORAL_ESCALATION", "RAPID_STRUCTURING"})

    def test_f_frontend_api_contract_consistency(self):
        """Test F: API response uses context_finding_ids and context_pattern_ids as expected by frontend."""
        tx = {"tx_id": "TX-FE-CONTRACT", "timestamp": "2026-09-01T15:00:00Z", "sender_account": "A1", "receiver_account": "A2", "amount": 100000.0}
        run_pipeline(tx, data_store)
        audit = generate_transaction_audit_explanation("TX-FE-CONTRACT", data_store)

        self.assertTrue(audit["found"])
        self.assertEqual(audit["status"], "SUCCESS")
        for step in audit["investigation_narrative"]:
            self.assertIn("context_finding_ids", step)
            self.assertIn("context_pattern_ids", step)
            self.assertNotIn("context_ids", step)

    def test_g_none_transaction_boundary(self):
        """Test G: Missing primary_tx_id in one package returns INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "TX-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}
        ctx_rpt = {"found": True, "target_id": "TX-001", "case_id": "CASE-001", "primary_tx_id": None}
        reg_rpt = {"found": True, "target_id": "TX-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INVALID_INPUT")

    # --- ADVERSARIAL FIXTURES A THROUGH G ---

    def test_adversarial_fixture_a_false_fact(self):
        """Adversarial Fixture A: Upstream amount=179218 must NEVER generate 'customer earned 179218'."""
        ev_pkg = {"found": True, "target_id": "CASE-ADV-A", "case_id": "CASE-ADV-A", "primary_tx_id": "TX-ADV-A", "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 179218.0}}]}
        ctx_rpt = {"found": True, "target_id": "CASE-ADV-A", "case_id": "CASE-ADV-A", "primary_tx_id": "TX-ADV-A", "patterns": [], "contextual_findings": []}
        reg_rpt = {"found": True, "target_id": "CASE-ADV-A", "case_id": "CASE-ADV-A", "primary_tx_id": "TX-ADV-A", "summary": {"regulatory_severity": "LOW"}, "regulatory_indicators": []}

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        output_str = str(audit).lower()
        self.assertNotIn("earned 179218", output_str)
        self.assertNotIn("customer earned", output_str)

    def test_adversarial_fixture_b_false_intent(self):
        """Adversarial Fixture B: BEHAVIORAL_ESCALATION must NEVER generate 'customer intentionally escalated activity'."""
        ev_pkg = {"found": True, "target_id": "CASE-ADV-B", "case_id": "CASE-ADV-B", "primary_tx_id": "TX-ADV-B", "evidence": [{"id": "EV-001", "type": "historical_behavior", "category": "Baseline", "data": {"deviation_ratio": 4.0}}]}
        ctx_rpt = {"found": True, "target_id": "CASE-ADV-B", "case_id": "CASE-ADV-B", "primary_tx_id": "TX-ADV-B", "patterns": [{"pattern_id": "BEHAVIORAL_ESCALATION", "matched": True}], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-ADV-B",
            "case_id": "CASE-ADV-B",
            "primary_tx_id": "TX-ADV-B",
            "summary": {"regulatory_severity": "MEDIUM"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "ABNORMAL_BASELINE_BEHAVIORAL_ESCALATION",
                "severity": "MEDIUM",
                "indicator": "Transaction value severely deviates from spending baseline.",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["BEHAVIORAL_ESCALATION"]
            }]
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        output_str = str(audit).lower()
        self.assertNotIn("intentionally escalated", output_str)
        self.assertNotIn("deliberately escalated", output_str)

    def test_adversarial_fixture_c_false_legal_certainty(self):
        """Adversarial Fixture C: POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING must NEVER generate 'AML violation confirmed'."""
        ev_pkg = {"found": True, "target_id": "CASE-ADV-C", "case_id": "CASE-ADV-C", "primary_tx_id": "TX-ADV-C", "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 200000.0}}]}
        ctx_rpt = {"found": True, "target_id": "CASE-ADV-C", "case_id": "CASE-ADV-C", "primary_tx_id": "TX-ADV-C", "patterns": [{"pattern_id": "RAPID_STRUCTURING", "matched": True}], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-ADV-C",
            "case_id": "CASE-ADV-C",
            "primary_tx_id": "TX-ADV-C",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING",
                "severity": "HIGH",
                "indicator": "Transaction activity exhibits structuring patterns.",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["RAPID_STRUCTURING"]
            }]
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        output_str = str(audit).lower()
        self.assertNotIn("aml violation confirmed", output_str)
        self.assertNotIn("confirmed money laundering", output_str)

    def test_adversarial_fixture_d_missing_sanctions(self):
        """Adversarial Fixture D: external_sanctions_database = UNAVAILABLE must say unavailable, NOT 'no sanctions match found'."""
        ev_pkg = {"found": True, "target_id": "CASE-ADV-D", "case_id": "CASE-ADV-D", "primary_tx_id": "TX-ADV-D", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-ADV-D", "case_id": "CASE-ADV-D", "primary_tx_id": "TX-ADV-D", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-ADV-D",
            "case_id": "CASE-ADV-D",
            "primary_tx_id": "TX-ADV-D",
            "summary": {"regulatory_severity": "LOW"},
            "jurisdiction_data_status": {"external_sanctions_database": "UNAVAILABLE"},
            "regulatory_indicators": []
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        output_str = str(audit).lower()
        self.assertIn("unavailable", output_str)
        self.assertNotIn("no sanctions match found", output_str)

    def test_adversarial_fixture_e_missing_kyc(self):
        """Adversarial Fixture E: external_kyc_verification = NOT_CHECKED must say KYC was not checked."""
        ev_pkg = {"found": True, "target_id": "CASE-ADV-E", "case_id": "CASE-ADV-E", "primary_tx_id": "TX-ADV-E", "evidence": []}
        ctx_rpt = {"found": True, "target_id": "CASE-ADV-E", "case_id": "CASE-ADV-E", "primary_tx_id": "TX-ADV-E", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-ADV-E",
            "case_id": "CASE-ADV-E",
            "primary_tx_id": "TX-ADV-E",
            "summary": {"regulatory_severity": "LOW"},
            "jurisdiction_data_status": {"external_kyc_verification": "NOT_CHECKED"},
            "regulatory_indicators": []
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        output_str = str(audit).lower()
        self.assertIn("not_checked", output_str)

    def test_adversarial_fixture_f_broken_traceability(self):
        """Adversarial Fixture F: Indicator referencing CTX-999 (non-existent) MUST return INCOMPLETE_TRACEABILITY."""
        ev_pkg = {"found": True, "target_id": "CASE-ADV-F", "case_id": "CASE-ADV-F", "primary_tx_id": "TX-ADV-F", "evidence": [{"id": "EV-001", "type": "transaction", "data": {"amount": 100.0}}]}
        ctx_rpt = {"found": True, "target_id": "CASE-ADV-F", "case_id": "CASE-ADV-F", "primary_tx_id": "TX-ADV-F", "patterns": [], "contextual_findings": []}
        reg_rpt = {
            "found": True,
            "target_id": "CASE-ADV-F",
            "case_id": "CASE-ADV-F",
            "primary_tx_id": "TX-ADV-F",
            "summary": {"regulatory_severity": "HIGH"},
            "regulatory_indicators": [{
                "id": "REG-001",
                "indicator_code": "TEST",
                "severity": "HIGH",
                "indicator": "Test",
                "supporting_evidence_ids": ["EV-001"],
                "supporting_context_ids": ["CTX-999"]
            }]
        }

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertEqual(audit["status"], "INCOMPLETE_TRACEABILITY")
        self.assertIn("CTX-999", audit["unresolved_references"][0])

    def test_adversarial_fixture_g_conflicting_cases(self):
        """Adversarial Fixture G: Evidence CASE-001 vs Context CASE-002 MUST return INVALID_INPUT."""
        ev_pkg = {"found": True, "target_id": "CASE-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}
        ctx_rpt = {"found": True, "target_id": "CASE-002", "case_id": "CASE-002", "primary_tx_id": "TX-001"}
        reg_rpt = {"found": True, "target_id": "CASE-001", "case_id": "CASE-001", "primary_tx_id": "TX-001"}

        audit = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
        self.assertFalse(audit["found"])
        self.assertEqual(audit["status"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
