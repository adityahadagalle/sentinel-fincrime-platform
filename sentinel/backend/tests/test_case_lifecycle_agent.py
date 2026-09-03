"""
Unit tests for Case Lifecycle & Audit Persistence Agent (Phase 6 Steps 1–3).

Tests state machine transitions, stateful disposition submission, identity validation,
forbidden action rejections, atomicity guarantees (zero mutation on error), multi-tier
traceability preservation, and immutable audit logging.
"""

import unittest
from typing import Dict, Any

from app.core.data_store import data_store
from app.services.evidence_agent import collect_evidence
from app.services.contextual_agent import investigate_context
from app.services.regulatory_agent import assess_regulatory_risk
from app.services.audit_explanation_agent import generate_audit_explanation
from app.services.analyst_agent import generate_analyst_decision_support
from app.services.case_lifecycle_agent import (
    submit_case_disposition,
    validate_state_transition,
    get_case_disposition_history,
    get_case_audit_history,
    STATE_NEW,
    STATE_UNDER_REVIEW,
    STATE_CDD_PENDING,
    STATE_ESCALATED,
    STATE_RESOLVED_DISMISSED,
    STATE_RESOLVED_APPROVED,
)
from app.repositories.in_memory import InMemoryCaseRepository
from main import app, get_repository




def _run_full_pipeline(tx: Dict[str, Any], store: Dict[str, Any]) -> Dict[str, Any]:
    tx_id = tx["tx_id"]
    case_id = f"CASE-{tx_id}"
    store["transactions"][tx_id] = tx

    ev = collect_evidence(tx_id, store)
    ev["case_id"] = case_id

    ctx = investigate_context(ev)
    ctx["case_id"] = case_id

    reg = assess_regulatory_risk(ev, ctx)
    reg["case_id"] = case_id

    aud = generate_audit_explanation(ev, ctx, reg)
    aud["case_id"] = case_id

    ds = generate_analyst_decision_support(ev, ctx, reg, aud)
    ds["case_id"] = case_id

    heur = reg.get("summary", {}).get("assessment_heuristic_index", 0.75)
    store["cases"][case_id] = {
        "case_id": case_id,
        "primary_tx_id": tx_id,
        "status": "NEW",
        "risk_score": float(heur) * 100,
        "chain": [tx_id]
    }
    return {
        "ev": ev,
        "ctx": ctx,
        "reg": reg,
        "aud": aud,
        "ds": ds,
        "case_id": case_id,
        "tx_id": tx_id
    }


class TestCaseLifecycleAgent(unittest.TestCase):

    def setUp(self):
        data_store["transactions"].clear()
        data_store["cases"].clear()
        data_store["graphs"].clear()
        data_store["accounts"].clear()
        data_store["actions"].clear()
        data_store["dispositions"] = {}
        data_store["audit_log"] = []

        self.tx = {
            "tx_id": "TX-P6-001",
            "timestamp": "2026-09-01T10:00:00Z",
            "sender_account": "ACC-SENDER-01",
            "receiver_account": "ACC-REC-01",
            "amount": 125000.0,
            "currency": "USD"
        }
        self.pipe = _run_full_pipeline(self.tx, data_store)
        self.case_id = self.pipe["case_id"]
        self.ds = self.pipe["ds"]

    def test_1_state_transition_validation_rules(self):
        """Test 1: Verifies state machine transition logic directly."""
        self.assertTrue(validate_state_transition(STATE_NEW, STATE_UNDER_REVIEW))
        self.assertTrue(validate_state_transition(STATE_NEW, STATE_ESCALATED))
        self.assertTrue(validate_state_transition(STATE_NEW, STATE_RESOLVED_DISMISSED))
        self.assertTrue(validate_state_transition(STATE_UNDER_REVIEW, STATE_CDD_PENDING))
        self.assertTrue(validate_state_transition(STATE_CDD_PENDING, STATE_RESOLVED_APPROVED))

        # Terminal state transitions must be rejected
        self.assertFalse(validate_state_transition(STATE_RESOLVED_DISMISSED, STATE_ESCALATED))
        self.assertFalse(validate_state_transition(STATE_RESOLVED_APPROVED, STATE_CDD_PENDING))
        self.assertFalse(validate_state_transition("INVALID_STATE", STATE_NEW))

    def test_2_valid_dismiss_case_transition(self):
        """Test 2: Valid DISMISS_CASE transitions status from NEW to RESOLVED_DISMISSED."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Valid false positive rationale.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-101",
            analyst_role="COMPLIANCE_ANALYST",
            store=data_store
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["previous_case_status"], STATE_NEW)
        self.assertEqual(res["new_case_status"], STATE_RESOLVED_DISMISSED)
        self.assertEqual(data_store["cases"][self.case_id]["status"], STATE_RESOLVED_DISMISSED)

    def test_3_valid_approve_transaction_transition(self):
        """Test 3: Valid APPROVE_TRANSACTION transitions status to RESOLVED_APPROVED."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="APPROVE_TRANSACTION",
            analyst_notes="Legitimate business invoice verified.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-102",
            analyst_role="COMPLIANCE_ANALYST",
            store=data_store
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["new_case_status"], STATE_RESOLVED_APPROVED)
        self.assertEqual(data_store["cases"][self.case_id]["status"], STATE_RESOLVED_APPROVED)

    def test_4_valid_request_cdd_transition(self):
        """Test 4: Valid REQUEST_CUSTOMER_CDD transitions status to CDD_PENDING."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="Requesting source of funds documentation.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-103",
            analyst_role="COMPLIANCE_ANALYST",
            store=data_store
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["new_case_status"], STATE_CDD_PENDING)
        self.assertEqual(data_store["cases"][self.case_id]["status"], STATE_CDD_PENDING)

    def test_5_valid_escalate_compliance_transition(self):
        """Test 5: Valid ESCALATE_SENIOR_COMPLIANCE transitions status to ESCALATED with risk ack."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="ESCALATE_SENIOR_COMPLIANCE",
            analyst_notes="Escalating due to high risk cross-border activity.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-104",
            analyst_role="COMPLIANCE_ANALYST",
            risk_acknowledged=True,
            store=data_store
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["new_case_status"], STATE_ESCALATED)
        self.assertEqual(data_store["cases"][self.case_id]["status"], STATE_ESCALATED)

    def test_6_invalid_transition_from_closed_case(self):
        """Test 6: Closed case (RESOLVED_DISMISSED) cannot be transitioned to ESCALATED."""
        data_store["cases"][self.case_id]["status"] = STATE_RESOLVED_DISMISSED

        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="ESCALATE_SENIOR_COMPLIANCE",
            analyst_notes="Attempting invalid transition from closed case.",
            decision_support_report=self.ds,
            risk_acknowledged=True,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")
        self.assertIn("Invalid state transition", res["error"])
        # Ensure status was not mutated
        self.assertEqual(data_store["cases"][self.case_id]["status"], STATE_RESOLVED_DISMISSED)

    def test_7_missing_case_id_rejected(self):
        """Test 7: Missing case_id returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id="",
            action_code="DISMISS_CASE",
            analyst_notes="Missing case id.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_8_missing_analyst_id_rejected(self):
        """Test 8: Missing analyst_id returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Missing analyst id.",
            decision_support_report=self.ds,
            analyst_id="",
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_9_missing_analyst_role_rejected(self):
        """Test 9: Missing analyst_role returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Missing analyst role.",
            decision_support_report=self.ds,
            analyst_role="",
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_10_unauthorized_analyst_role_rejected(self):
        """Test 10: Unauthorized role returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Unauthorized role test.",
            decision_support_report=self.ds,
            analyst_role="GUEST_USER",
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_11_missing_required_notes_rejected(self):
        """Test 11: Action requiring notes with empty analyst_notes returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="   ",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_12_missing_risk_ack_rejected(self):
        """Test 12: Action requiring risk_acknowledged=True with risk_acknowledged=False returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="ESCALATE_SENIOR_COMPLIANCE",
            analyst_notes="Escalating without risk ack.",
            decision_support_report=self.ds,
            risk_acknowledged=False,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_13_forbidden_freeze_action_rejected(self):
        """Test 13: Forbidden action FREEZE is strictly rejected."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="FREEZE",
            analyst_notes="Attempting autonomous freeze.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")
        self.assertIn("Forbidden action code", res["error"])

    def test_14_forbidden_block_action_rejected(self):
        """Test 14: Forbidden action BLOCK is strictly rejected."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="BLOCK",
            analyst_notes="Attempting autonomous block.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_15_forbidden_file_str_action_rejected(self):
        """Test 15: Forbidden action FILE_STR is strictly rejected."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="FILE_STR",
            analyst_notes="Attempting autonomous STR filing.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_16_forbidden_close_account_action_rejected(self):
        """Test 16: Forbidden action CLOSE_ACCOUNT is strictly rejected."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="CLOSE_ACCOUNT",
            analyst_notes="Attempting autonomous account closure.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_17_forbidden_reject_tx_action_rejected(self):
        """Test 17: Forbidden action REJECT_TRANSACTION is strictly rejected."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="REJECT_TRANSACTION",
            analyst_notes="Attempting autonomous transaction rejection.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_18_unknown_action_code_rejected(self):
        """Test 18: Unknown action code returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="INVALID_CUSTOM_ACTION",
            analyst_notes="Custom action.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_19_cross_case_submission_rejected(self):
        """Test 19: Payload case_id vs Decision support case_id mismatch returns INVALID_INPUT."""
        res = submit_case_disposition(
            case_id="CASE-FORGED-999",
            action_code="DISMISS_CASE",
            analyst_notes="Cross-case attempt.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")
        self.assertIn("Scope mismatch", res["error"])

    def test_20_case_not_found_in_store_rejected(self):
        """Test 20: Non-existent case_id in data store returns INVALID_INPUT."""
        ds_ghost = dict(self.ds)
        ds_ghost["case_id"] = "CASE-GHOST-777"
        
        res = submit_case_disposition(
            case_id="CASE-GHOST-777",
            action_code="DISMISS_CASE",
            analyst_notes="Ghost case attempt.",
            decision_support_report=ds_ghost,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")

    def test_21_incomplete_traceability_ds_report_rejected(self):
        """Test 21: Decision support report with INCOMPLETE_TRACEABILITY returns INCOMPLETE_TRACEABILITY."""
        ds_broken = dict(self.ds)
        ds_broken["status"] = "INCOMPLETE_TRACEABILITY"
        ds_broken["unresolved_references"] = ["EV-999"]

        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Broken traceability report.",
            decision_support_report=ds_broken,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INCOMPLETE_TRACEABILITY")

    def test_22_unoffered_action_code_rejected(self):
        """Test 22: Valid action code that is not offered by DS report returns INVALID_INPUT."""
        ds_narrow = dict(self.ds)
        # Offer only DISMISS_CASE
        ds_narrow["disposition_options"] = [
            {"action_code": "DISMISS_CASE", "label": "Dismiss Case", "requires_reason_note": True, "requires_risk_acknowledgement": False}
        ]

        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="ESCALATE_SENIOR_COMPLIANCE",
            analyst_notes="Escalating unoffered option.",
            decision_support_report=ds_narrow,
            risk_acknowledged=True,
            store=data_store
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")
        self.assertIn("not offered", res["error"])

    def test_23_disposition_persistence_in_data_store(self):
        """Test 23: Successful disposition is persisted in data_store['dispositions']."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Persistence test rationale.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-505",
            store=data_store
        )
        self.assertTrue(res["ok"])
        disps = data_store["dispositions"].get(self.case_id, [])
        self.assertEqual(len(disps), 1)
        disp = disps[0]
        self.assertEqual(disp["action_code"], "DISMISS_CASE")
        self.assertEqual(disp["analyst_notes"], "Persistence test rationale.")
        self.assertEqual(disp["analyst_id"], "ANALYST-505")
        self.assertEqual(disp["previous_case_status"], STATE_NEW)
        self.assertEqual(disp["new_case_status"], STATE_RESOLVED_DISMISSED)

    def test_24_audit_log_persistence_in_data_store(self):
        """Test 24: Successful disposition appends an audit event to data_store['audit_log']."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Audit log test rationale.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-606",
            store=data_store
        )
        self.assertTrue(res["ok"])
        self.assertEqual(len(data_store["audit_log"]), 1)
        entry = data_store["audit_log"][0]
        self.assertEqual(entry["event_type"], "CASE_DISPOSITION_MUTATION")
        self.assertEqual(entry["case_id"], self.case_id)
        self.assertEqual(entry["analyst_id"], "ANALYST-606")
        self.assertEqual(entry["action_code"], "DISMISS_CASE")
        self.assertIn("decision_support_summary", entry)
        self.assertIn("traceability_chain", entry)

    def test_25_historical_disposition_immutability(self):
        """Test 25: Appending a subsequent disposition does not overwrite historical records."""
        # First disposition: REQUEST_CUSTOMER_CDD
        res1 = submit_case_disposition(
            case_id=self.case_id,
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="Initial CDD request.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-001",
            store=data_store
        )
        self.assertTrue(res1["ok"])

        # Second disposition: RESOLVED_APPROVED
        res2 = submit_case_disposition(
            case_id=self.case_id,
            action_code="APPROVE_TRANSACTION",
            analyst_notes="CDD documents verified.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-002",
            store=data_store
        )
        self.assertTrue(res2["ok"])

        history = get_case_disposition_history(self.case_id, store=data_store)
        self.assertEqual(len(history), 2)
        # First history record unchanged
        self.assertEqual(history[0]["action_code"], "REQUEST_CUSTOMER_CDD")
        self.assertEqual(history[0]["analyst_id"], "ANALYST-001")
        self.assertEqual(history[0]["new_case_status"], STATE_CDD_PENDING)
        # Second history record
        self.assertEqual(history[1]["action_code"], "APPROVE_TRANSACTION")
        self.assertEqual(history[1]["analyst_id"], "ANALYST-002")
        self.assertEqual(history[1]["new_case_status"], STATE_RESOLVED_APPROVED)

    def test_26_historical_audit_log_immutability(self):
        """Test 26: Audit log retains immutable history of multiple state transitions."""
        submit_case_disposition(
            case_id=self.case_id,
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="First transition notes.",
            decision_support_report=self.ds,
            store=data_store
        )
        submit_case_disposition(
            case_id=self.case_id,
            action_code="APPROVE_TRANSACTION",
            analyst_notes="Second transition notes.",
            decision_support_report=self.ds,
            store=data_store
        )

        audit_history = get_case_audit_history(self.case_id, store=data_store)
        self.assertEqual(len(audit_history), 2)
        self.assertEqual(audit_history[0]["action_code"], "REQUEST_CUSTOMER_CDD")
        self.assertEqual(audit_history[1]["action_code"], "APPROVE_TRANSACTION")

    def test_27_zero_mutation_on_failed_validation(self):
        """Test 27: Failed validation causes ZERO mutation to case status, dispositions, or audit_log."""
        initial_status = data_store["cases"][self.case_id]["status"]
        initial_disps = list(data_store["dispositions"].get(self.case_id, []))
        initial_audit = list(data_store["audit_log"])

        # Attempt invalid submission (forbidden action)
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="FREEZE",
            analyst_notes="Attempting forbidden action.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertFalse(res["ok"])

        # Verify ZERO state mutation
        self.assertEqual(data_store["cases"][self.case_id]["status"], initial_status)
        self.assertEqual(data_store["dispositions"].get(self.case_id, []), initial_disps)
        self.assertEqual(data_store["audit_log"], initial_audit)

    def test_28_traceability_chain_preserved_in_audit_event(self):
        """Test 28: Multi-tier traceability chain is properly populated in the audit entry."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Checking traceability preservation.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertTrue(res["ok"])
        audit_entry = res["audit_entry"]
        chain = audit_entry["traceability_chain"]
        self.assertIn("supporting_regulatory_ids", chain)
        self.assertIn("supporting_context_finding_ids", chain)
        self.assertIn("supporting_context_pattern_ids", chain)
        self.assertIn("supporting_evidence_ids", chain)

    def test_29_namespace_isolation_in_audit_chain(self):
        """Test 29: Context pattern IDs (e.g. RAPID_STRUCTURING) are strictly separate from context_finding_ids."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Checking namespace isolation.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertTrue(res["ok"])
        chain = res["audit_entry"]["traceability_chain"]
        for fid in chain["supporting_context_finding_ids"]:
            self.assertTrue(fid.startswith("CTX-"), f"Finding ID '{fid}' does not start with CTX-")

    def test_30_deterministic_output_schema(self):
        """Test 30: Successful disposition response contains all required fields."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Schema test notes.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["acknowledged"])
        self.assertIn("case_id", res)
        self.assertIn("previous_case_status", res)
        self.assertIn("new_case_status", res)
        self.assertIn("disposition", res)
        self.assertIn("audit_entry", res)

    def test_31_analyst_identity_preserved(self):
        """Test 31: Custom analyst_id and analyst_role are preserved verbatim in disposition record."""
        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Identity test.",
            decision_support_report=self.ds,
            analyst_id="ANALYST-SPEC-99",
            analyst_role="MLRO",
            store=data_store
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["disposition"]["analyst_id"], "ANALYST-SPEC-99")
        self.assertEqual(res["disposition"]["analyst_role"], "MLRO")
        self.assertEqual(res["audit_entry"]["analyst_id"], "ANALYST-SPEC-99")
        self.assertEqual(res["audit_entry"]["analyst_role"], "MLRO")

    def test_32_no_autonomous_enforcement_execution(self):
        """Test 32: Disposition execution does not execute account freeze or balance deduction."""
        acc_before = dict(data_store.get("accounts", {}).get("ACC-SENDER-01", {}))

        res = submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="No enforcement execution test.",
            decision_support_report=self.ds,
            store=data_store
        )
        self.assertTrue(res["ok"])
        acc_after = data_store.get("accounts", {}).get("ACC-SENDER-01", {})
        self.assertEqual(acc_before, acc_after)

    def test_33_helper_disposition_history(self):
        """Test 33: get_case_disposition_history returns correct records."""
        submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="History test.",
            decision_support_report=self.ds,
            store=data_store
        )
        history = get_case_disposition_history(self.case_id, store=data_store)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action_code"], "DISMISS_CASE")

    def test_34_helper_audit_history(self):
        """Test 34: get_case_audit_history returns correct audit events."""
        submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Audit history test.",
            decision_support_report=self.ds,
            store=data_store
        )
        audit_history = get_case_audit_history(self.case_id, store=data_store)
        self.assertEqual(len(audit_history), 1)
        self.assertEqual(audit_history[0]["action_code"], "DISMISS_CASE")

    def test_35_multiple_cases_isolation(self):
        """Test 35: Disposition and audit logs for multiple cases remain isolated."""
        tx2 = {
            "tx_id": "TX-P6-002",
            "timestamp": "2026-09-01T10:00:00Z",
            "sender_account": "ACC-SENDER-02",
            "receiver_account": "ACC-REC-02",
            "amount": 95000.0,
            "currency": "USD"
        }
        pipe2 = _run_full_pipeline(tx2, data_store)
        case_id2 = pipe2["case_id"]

        submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="Case 1 disposition.",
            decision_support_report=self.ds,
            store=data_store
        )
        submit_case_disposition(
            case_id=case_id2,
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="Case 2 disposition.",
            decision_support_report=pipe2["ds"],
            store=data_store
        )

        h1 = get_case_disposition_history(self.case_id, store=data_store)
        h2 = get_case_disposition_history(case_id2, store=data_store)

        self.assertEqual(len(h1), 1)
        self.assertEqual(h1[0]["action_code"], "DISMISS_CASE")
        self.assertEqual(len(h2), 1)
        self.assertEqual(h2[0]["action_code"], "REQUEST_CUSTOMER_CDD")


from fastapi.testclient import TestClient
from main import app


class TestCaseLifecycleAPI(unittest.TestCase):

    def setUp(self):
        data_store["transactions"].clear()
        data_store["cases"].clear()
        data_store["graphs"].clear()
        data_store["accounts"].clear()
        data_store["actions"].clear()
        data_store["dispositions"] = {}
        data_store["audit_log"] = []
        app.dependency_overrides[get_repository] = lambda: InMemoryCaseRepository(data_store)
        self.client = TestClient(app)

        self.tx = {
            "tx_id": "TX-API-LFC-01",
            "timestamp": "2026-09-01T10:00:00Z",
            "sender_account": "A1",
            "receiver_account": "A2",
            "amount": 120000.0,
            "currency": "USD"
        }
        self.pipe = _run_full_pipeline(self.tx, data_store)
        self.case_id = self.pipe["case_id"]

    def tearDown(self):
        app.dependency_overrides.clear()


    def test_api_1_stateful_disposition_success(self):
        """API Test 1: POST /cases/{case_id}/disposition executes stateful transition."""
        resp = self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "API disposition test rationale.",
            "analyst_id": "ANALYST-API-1",
            "analyst_role": "COMPLIANCE_ANALYST"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["previous_case_status"], STATE_NEW)
        self.assertEqual(data["new_case_status"], STATE_RESOLVED_DISMISSED)

    def test_api_2_disposition_persistence(self):
        """API Test 2: Disposition is persisted in data_store['dispositions']."""
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "analyst_notes": "API CDD rationale."
        })
        disps = data_store.get("dispositions", {}).get(self.case_id, [])
        self.assertEqual(len(disps), 1)
        self.assertEqual(disps[0]["action_code"], "REQUEST_CUSTOMER_CDD")

    def test_api_3_audit_event_persistence(self):
        """API Test 3: Audit event is appended to data_store['audit_log']."""
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "APPROVE_TRANSACTION",
            "analyst_notes": "API approval rationale."
        })
        self.assertEqual(len(data_store.get("audit_log", [])), 1)
        self.assertEqual(data_store["audit_log"][0]["action_code"], "APPROVE_TRANSACTION")

    def test_api_4_history_endpoint_success(self):
        """API Test 4: GET /cases/{case_id}/history returns complete history."""
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "analyst_notes": "Notes 1."
        })
        resp = self.client.get(f"/cases/{self.case_id}/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["current_case_status"], STATE_CDD_PENDING)
        self.assertEqual(len(data["disposition_history"]), 1)
        self.assertEqual(len(data["audit_history"]), 1)

    def test_api_5_history_preserves_notes_identity_risk_ack_traceability(self):
        """API Test 5: History endpoint preserves notes, identity, risk ack, and traceability."""
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "ESCALATE_SENIOR_COMPLIANCE",
            "analyst_notes": "Preservation API test notes.",
            "analyst_id": "ANALYST-SPEC-7",
            "analyst_role": "SENIOR_COMPLIANCE_OFFICER",
            "risk_acknowledged": True
        })
        resp = self.client.get(f"/cases/{self.case_id}/history")
        data = resp.json()
        disp = data["disposition_history"][0]
        audit = data["audit_history"][0]

        self.assertEqual(disp["analyst_notes"], "Preservation API test notes.")
        self.assertEqual(disp["analyst_id"], "ANALYST-SPEC-7")
        self.assertEqual(disp["analyst_role"], "SENIOR_COMPLIANCE_OFFICER")
        self.assertTrue(disp["risk_acknowledged"])
        self.assertIn("traceability_chain", audit)

    def test_api_6_get_cases_exposes_authoritative_lifecycle_status(self):
        """API Test 6: GET /cases exposes current persistent lifecycle status."""
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Dismissing case for status test."
        })
        resp = self.client.get("/cases")
        self.assertEqual(resp.status_code, 200)
        cases = resp.json()
        matched = next((c for c in cases if c["case_id"] == self.case_id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["status"], STATE_RESOLVED_DISMISSED)

    def test_api_7_closed_case_cannot_be_transitioned(self):
        """API Test 7: Closed case rejects subsequent invalid state transitions via API."""
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Closing case."
        })
        resp = self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "ESCALATE_SENIOR_COMPLIANCE",
            "analyst_notes": "Attempting transition from closed.",
            "risk_acknowledged": True
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_8_forbidden_freeze_rejected(self):
        """API Test 8: Forbidden FREEZE action rejected by disposition endpoint."""
        resp = self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "FREEZE",
            "analyst_notes": "Attempting autonomous freeze."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_9_cross_case_disposition_rejected(self):
        """API Test 9: Path vs Payload case_id mismatch returns INVALID_INPUT."""
        resp = self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": "CASE-FORGED-888",
            "action_code": "DISMISS_CASE",
            "analyst_notes": "Cross case attempt."
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "INVALID_INPUT")

    def test_api_10_failed_disposition_zero_mutation(self):
        """API Test 10: Failed disposition submission causes ZERO state mutation."""
        case_before = dict(data_store["cases"][self.case_id])
        disps_before = list(data_store.get("dispositions", {}).get(self.case_id, []))

        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "FREEZE",
            "analyst_notes": "Failed attempt."
        })

        case_after = data_store["cases"][self.case_id]
        disps_after = data_store.get("dispositions", {}).get(self.case_id, [])

        self.assertEqual(case_before["status"], case_after["status"])
        self.assertEqual(disps_before, disps_after)

    def test_api_11_multiple_dispositions_chronological(self):
        """API Test 11: Multiple API dispositions produce chronological history."""
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "analyst_notes": "Step 1 CDD."
        })
        self.client.post(f"/cases/{self.case_id}/disposition", json={
            "case_id": self.case_id,
            "action_code": "APPROVE_TRANSACTION",
            "analyst_notes": "Step 2 Approval."
        })

        resp = self.client.get(f"/cases/{self.case_id}/history")
        data = resp.json()
        self.assertEqual(len(data["disposition_history"]), 2)
        self.assertEqual(data["disposition_history"][0]["action_code"], "REQUEST_CUSTOMER_CDD")
        self.assertEqual(data["disposition_history"][1]["action_code"], "APPROVE_TRANSACTION")

    def test_api_12_nonexistent_case_history_handled_cleanly(self):
        """API Test 12: GET /cases/{case_id}/history for non-existent case returns INSUFFICIENT_DATA."""
        resp = self.client.get("/cases/CASE-GHOST-999/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["found"])
        self.assertEqual(data["status"], "INSUFFICIENT_DATA")


import asyncio
from app.repositories.in_memory import InMemoryCaseRepository
from app.services.case_lifecycle_agent import CaseLifecycleService


def _async_run(coro):
    return asyncio.run(coro)


class TestCaseLifecycleServiceDI(unittest.TestCase):

    def setUp(self):
        self.store = {
            "transactions": {},
            "cases": {},
            "graphs": {},
            "accounts": {},
            "actions": [],
            "dispositions": {},
            "audit_log": []
        }
        self.repo = InMemoryCaseRepository(self.store)
        self.service = CaseLifecycleService(self.repo)

        self.tx = {
            "tx_id": "TX-DI-01",
            "timestamp": "2026-09-01T10:00:00Z",
            "sender_account": "A1",
            "receiver_account": "A2",
            "amount": 100000.0,
            "currency": "USD"
        }
        self.pipe = _run_full_pipeline(self.tx, self.store)
        self.case_id = self.pipe["case_id"]

    def test_di_1_service_accepts_injected_repository(self):
        """Step 3 Test 1: CaseLifecycleService accepts injected repository."""
        self.assertEqual(self.service.repository, self.repo)

    def test_di_2_successful_disposition_through_repository(self):
        """Step 3 Test 2: Disposition processed through repository-injected service."""
        res = _async_run(self.service.submit_case_disposition(
            case_id=self.case_id,
            action_code="DISMISS_CASE",
            analyst_notes="DI test dismissal.",
            decision_support_report=self.pipe["ds"],
            analyst_id="ANALYST-DI-1",
            analyst_role="COMPLIANCE_ANALYST"
        ))
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["new_case_status"], "RESOLVED_DISMISSED")

    def test_di_3_failed_validation_zero_repository_mutation(self):
        """Step 3 Test 3: Failed validation causes ZERO mutation in repository."""
        res = _async_run(self.service.submit_case_disposition(
            case_id=self.case_id,
            action_code="FREEZE",
            analyst_notes="Forbidden attempt.",
            decision_support_report=self.pipe["ds"]
        ))
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "INVALID_INPUT")
        
        hist = _async_run(self.repo.get_case_history(self.case_id))
        self.assertEqual(len(hist["disposition_history"]), 0)

    def test_di_4_idempotency_cached_response(self):
        """Step 3 Test 4: Supplying existing idempotency_key returns cached response without duplicate audit."""
        res1 = _async_run(self.service.submit_case_disposition(
            case_id=self.case_id,
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="CDD step.",
            decision_support_report=self.pipe["ds"],
            idempotency_key="IDEM-KEY-DI-1"
        ))
        self.assertTrue(res1["ok"])

        res2 = _async_run(self.service.submit_case_disposition(
            case_id=self.case_id,
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="CDD step duplicate.",
            decision_support_report=self.pipe["ds"],
            idempotency_key="IDEM-KEY-DI-1"
        ))
        self.assertTrue(res2["ok"])
        self.assertTrue(res2.get("idempotent_cached_response"))

        hist = _async_run(self.repo.get_case_history(self.case_id))
        self.assertEqual(len(hist["disposition_history"]), 1)

    def test_di_5_static_architecture_check_no_direct_postgres_import(self):
        """Step 3 Test 5: case_lifecycle_agent.py does not import PostgreSQLCaseRepository directly."""
        import app.services.case_lifecycle_agent as agent_mod
        mod_dict = dir(agent_mod)
        self.assertNotIn("PostgreSQLCaseRepository", mod_dict)


if __name__ == "__main__":
    unittest.main()


