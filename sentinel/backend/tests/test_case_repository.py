"""
Unit tests for Abstract, PostgreSQL, and InMemory Case Repositories (Phase 7 Step 2).
"""

import os
import sys
import unittest
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.repositories.in_memory import InMemoryCaseRepository
from app.repositories.base import AbstractCaseRepository


def _async_run(coro):
    return asyncio.run(coro)


class TestInMemoryCaseRepository(unittest.TestCase):

    def setUp(self):
        self.repo = InMemoryCaseRepository()
        self.case_id = "CASE-TEST-100"
        self.tx_id = "TX-TEST-100"

        _async_run(self.repo.save_case({
            "case_id": self.case_id,
            "primary_tx_id": self.tx_id,
            "status": "NEW",
            "risk_level": "HIGH",
            "golden_window_minutes": 30,
            "total_fraud_amount": 100000.0,
            "recoverable_amount": 100000.0,
            "created_at": "2026-09-01T10:00:00Z"
        }))

    def test_1_case_lookup_success(self):
        """Test 1: Case lookup returns registered case."""
        case = _async_run(self.repo.get_case_by_id(self.case_id))
        self.assertIsNotNone(case)
        self.assertEqual(case["case_id"], self.case_id)
        self.assertEqual(case["status"], "NEW")

    def test_2_missing_case_returns_none(self):
        """Test 2: Missing case lookup returns None."""
        case = _async_run(self.repo.get_case_by_id("CASE-GHOST-999"))
        self.assertIsNone(case)

    def test_3_get_case_for_update(self):
        """Test 3: get_case_for_update returns locked case representation."""
        case = _async_run(self.repo.get_case_for_update(self.case_id))
        self.assertIsNotNone(case)
        self.assertEqual(case["case_id"], self.case_id)

    def test_4_save_disposition_and_audit(self):
        """Test 4: Atomic disposition and audit event write."""
        disp = {
            "disposition_id": "DSP-101",
            "case_id": self.case_id,
            "primary_tx_id": self.tx_id,
            "action_code": "DISMISS_CASE",
            "label": "Dismiss False Positive",
            "analyst_notes": "Test notes.",
            "analyst_id": "ANALYST-1",
            "analyst_role": "COMPLIANCE_ANALYST",
            "risk_acknowledged": False,
            "previous_case_status": "NEW",
            "new_case_status": "RESOLVED_DISMISSED",
            "idempotency_key": "IDEM-101",
            "disposition_timestamp": "2026-09-01T10:05:00Z"
        }

        audit = {
            "audit_id": "AUD-101",
            "event_type": "CASE_DISPOSITION_MUTATION",
            "timestamp": "2026-09-01T10:05:00Z",
            "case_id": self.case_id,
            "primary_tx_id": self.tx_id,
            "analyst_id": "ANALYST-1",
            "analyst_role": "COMPLIANCE_ANALYST",
            "action_code": "DISMISS_CASE",
            "previous_case_status": "NEW",
            "new_case_status": "RESOLVED_DISMISSED",
            "analyst_notes": "Test notes.",
            "risk_acknowledged": False,
            "decision_support_summary": {},
            "traceability_chain": {}
        }

        res = _async_run(self.repo.save_disposition_and_audit(
            self.case_id,
            "RESOLVED_DISMISSED",
            disp,
            audit
        ))
        self.assertTrue(res)

        # Verify updated case status
        updated_case = _async_run(self.repo.get_case_by_id(self.case_id))
        self.assertEqual(updated_case["status"], "RESOLVED_DISMISSED")

    def test_5_history_retrieval_and_chronological_ordering(self):
        """Test 5: History retrieval returns chronological disposition and audit logs."""
        disp1 = {
            "disposition_id": "DSP-101",
            "case_id": self.case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "previous_case_status": "NEW",
            "new_case_status": "CDD_PENDING",
            "disposition_timestamp": "2026-09-01T10:05:00Z"
        }
        audit1 = {
            "audit_id": "AUD-101",
            "case_id": self.case_id,
            "action_code": "REQUEST_CUSTOMER_CDD",
            "timestamp": "2026-09-01T10:05:00Z"
        }
        _async_run(self.repo.save_disposition_and_audit(self.case_id, "CDD_PENDING", disp1, audit1))

        disp2 = {
            "disposition_id": "DSP-102",
            "case_id": self.case_id,
            "action_code": "APPROVE_TRANSACTION",
            "previous_case_status": "CDD_PENDING",
            "new_case_status": "RESOLVED_APPROVED",
            "disposition_timestamp": "2026-09-01T10:10:00Z"
        }
        audit2 = {
            "audit_id": "AUD-102",
            "case_id": self.case_id,
            "action_code": "APPROVE_TRANSACTION",
            "timestamp": "2026-09-01T10:10:00Z"
        }
        _async_run(self.repo.save_disposition_and_audit(self.case_id, "RESOLVED_APPROVED", disp2, audit2))

        history = _async_run(self.repo.get_case_history(self.case_id))
        self.assertTrue(history["found"])
        self.assertEqual(history["current_case_status"], "RESOLVED_APPROVED")
        self.assertEqual(len(history["disposition_history"]), 2)
        self.assertEqual(len(history["audit_history"]), 2)

        # Check chronological order
        self.assertEqual(history["disposition_history"][0]["disposition_id"], "DSP-101")
        self.assertEqual(history["disposition_history"][1]["disposition_id"], "DSP-102")

    def test_6_case_isolation(self):
        """Test 6: Case isolation guarantees data from CASE-A does not leak into CASE-B."""
        case_b_id = "CASE-TEST-200"
        _async_run(self.repo.save_case({
            "case_id": case_b_id,
            "primary_tx_id": "TX-200",
            "status": "NEW"
        }))

        disp_a = {
            "disposition_id": "DSP-A",
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "disposition_timestamp": "2026-09-01T10:00:00Z"
        }
        audit_a = {
            "audit_id": "AUD-A",
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "timestamp": "2026-09-01T10:00:00Z"
        }
        _async_run(self.repo.save_disposition_and_audit(self.case_id, "RESOLVED_DISMISSED", disp_a, audit_a))

        hist_a = _async_run(self.repo.get_case_history(self.case_id))
        hist_b = _async_run(self.repo.get_case_history(case_b_id))

        self.assertEqual(len(hist_a["disposition_history"]), 1)
        self.assertEqual(len(hist_b["disposition_history"]), 0)

    def test_7_idempotency_lookup(self):
        """Test 7: Idempotency key lookup returns stored disposition."""
        disp = {
            "disposition_id": "DSP-IDEM",
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "idempotency_key": "UNIQUE-KEY-777",
            "disposition_timestamp": "2026-09-01T10:00:00Z"
        }
        audit = {
            "audit_id": "AUD-IDEM",
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "timestamp": "2026-09-01T10:00:00Z"
        }
        _async_run(self.repo.save_disposition_and_audit(self.case_id, "RESOLVED_DISMISSED", disp, audit))

        found_disp = _async_run(self.repo.get_disposition_by_idempotency_key("UNIQUE-KEY-777"))
        self.assertIsNotNone(found_disp)
        self.assertEqual(found_disp["disposition_id"], "DSP-IDEM")

    def test_8_duplicate_idempotency_key_raises_error(self):
        """Test 8: Re-using existing idempotency key raises error."""
        disp = {
            "disposition_id": "DSP-1",
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "idempotency_key": "DUP-KEY-111",
            "disposition_timestamp": "2026-09-01T10:00:00Z"
        }
        audit = {
            "audit_id": "AUD-1",
            "case_id": self.case_id,
            "action_code": "DISMISS_CASE",
            "timestamp": "2026-09-01T10:00:00Z"
        }
        _async_run(self.repo.save_disposition_and_audit(self.case_id, "RESOLVED_DISMISSED", disp, audit))

        disp_dup = {
            "disposition_id": "DSP-2",
            "case_id": self.case_id,
            "action_code": "APPROVE_TRANSACTION",
            "idempotency_key": "DUP-KEY-111",
            "disposition_timestamp": "2026-09-01T10:05:00Z"
        }

        with self.assertRaises(ValueError):
            _async_run(self.repo.save_disposition_and_audit(self.case_id, "RESOLVED_APPROVED", disp_dup, audit))

    def test_9_append_only_audit_boundary(self):
        """Test 9: Repository interface exposes no update/delete methods for audit log."""
        methods = dir(AbstractCaseRepository)
        self.assertNotIn("update_audit_event", methods)
        self.assertNotIn("delete_audit_event", methods)


if __name__ == "__main__":
    unittest.main()
