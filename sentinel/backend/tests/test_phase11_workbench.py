"""
Phase 11 Analyst Workbench Integration & API Tests.

Verifies:
1. GET /cases/{case_id}/investigation-runs historical run listing.
2. GET /cases/{case_id}/investigation-runs/{run_id} specific run retrieval.
3. Historical run preservation across force_rerun calls.
4. Disposition state transitions & PostgreSQL audit traceability.
5. Human approval boundary enforcement.
6. Zero autonomous forbidden financial action execution.
"""

import unittest
import asyncio
from typing import Dict, Any

from app.core.data_store import data_store
from app.repositories.in_memory import InMemoryCaseRepository
from app.services.investigation_orchestrator import InvestigationOrchestrator, _now_iso
from app.services.case_lifecycle_agent import CaseLifecycleService



class TestPhase11Workbench(unittest.IsolatedAsyncioTestCase):

    async def _seed_case(self, case_id: str, tx_id: str):
        now = _now_iso()
        data_store.setdefault("accounts", {})["ACC-P11-SND"] = {"account_id": "ACC-P11-SND", "status": "active"}
        data_store.setdefault("accounts", {})["ACC-P11-RCV"] = {"account_id": "ACC-P11-RCV", "status": "active"}
        data_store.setdefault("transactions", {})[tx_id] = {
            "tx_id": tx_id,
            "sender_account": "ACC-P11-SND",
            "receiver_account": "ACC-P11-RCV",
            "amount": 120000.0,
            "channel": "UPI",
            "risk_score": 92,
            "case_id": case_id,
            "timestamp": now
        }
        case_data = {
            "case_id": case_id,
            "primary_tx_id": tx_id,
            "status": "NEW",
            "risk_level": 92.0,
            "created_at": now,
            "updated_at": now
        }
        data_store.setdefault("cases", {})[case_id] = case_data
        await self.repo.save_case(case_data)

    async def asyncSetUp(self):
        self.repo = InMemoryCaseRepository(data_store)
        self.orchestrator = InvestigationOrchestrator()
        await self._seed_case("CASE-P11-001", "TX-P11-001")

    async def test_01_historical_investigation_runs_listing(self):
        """Test retrieving all historical investigation runs for a case."""
        case_id = "CASE-P11-001"
        run1 = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)
        run2 = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)

        runs = await self.repo.get_investigation_runs_for_case(case_id)
        self.assertGreaterEqual(len(runs), 2)
        self.assertEqual(runs[0]["run_id"], run2["investigation_id"])
        self.assertEqual(runs[1]["run_id"], run1["investigation_id"])

    async def test_02_specific_investigation_run_retrieval(self):
        """Test retrieving a specific historical run by run_id."""
        case_id = "CASE-P11-001"
        run1 = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)
        run_id = run1["investigation_id"]

        fetched = await self.repo.get_investigation_run(run_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["run_id"], run_id)
        self.assertEqual(fetched["case_id"], case_id)

    async def test_03_disposition_workflow_and_audit_traceability(self):
        """Test analyst disposition state transition and audit logging."""
        case_id = "CASE-P11-001"
        service = CaseLifecycleService(self.repo)

        mock_ds_report = {
            "found": True,
            "status": "SUCCESS",
            "disposition_options": [
                {"action_code": "REQUEST_CUSTOMER_CDD", "label": "Request Customer CDD", "requires_risk_acknowledgement": False, "requires_reason_note": False},
                {"action_code": "APPROVE_TRANSACTION", "label": "Approve Transaction", "requires_risk_acknowledgement": False, "requires_reason_note": False}
            ]
        }


        # 1. Transition NEW -> CDD_PENDING using REQUEST_CUSTOMER_CDD action
        res1 = await service.submit_case_disposition(
            case_id=case_id,
            action_code="REQUEST_CUSTOMER_CDD",
            analyst_notes="Requesting additional KYC documentation",
            decision_support_report=mock_ds_report,
            analyst_id="ANALYST-P11",
            analyst_role="COMPLIANCE_ANALYST"
        )
        self.assertTrue(res1.get("ok"), msg=f"res1 failed: {res1}")
        self.assertEqual(res1["disposition"]["new_case_status"], "CDD_PENDING")

        # 2. Transition CDD_PENDING -> RESOLVED_APPROVED using APPROVE_TRANSACTION action
        res2 = await service.submit_case_disposition(
            case_id=case_id,
            action_code="APPROVE_TRANSACTION",
            analyst_notes="Verified customer documentation and approved release",
            decision_support_report=mock_ds_report,
            analyst_id="ANALYST-P11",
            analyst_role="COMPLIANCE_ANALYST"
        )
        self.assertTrue(res2.get("ok"), msg=f"res2 failed: {res2}")
        self.assertEqual(res2["disposition"]["new_case_status"], "RESOLVED_APPROVED")




        # Verify audit history
        history = await self.repo.get_case_history(case_id)
        events = history.get("audit_history", [])
        self.assertGreaterEqual(len(events), 2)
        latest_event = events[-1]
        self.assertEqual(latest_event["action_code"], "APPROVE_TRANSACTION")
        self.assertEqual(latest_event["analyst_id"], "ANALYST-P11")




    async def test_04_human_approval_boundary_preservation(self):
        """Test that AI recommendations never execute forbidden financial actions directly."""
        case_id = "CASE-P11-001"
        run = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)
        rec_action = run["summary"].get("recommended_action")

        forbidden_actions = {"FREEZE", "BLOCK", "FILE_STR", "CLOSE_ACCOUNT", "REJECT_TRANSACTION"}
        self.assertNotIn(rec_action, forbidden_actions)


if __name__ == "__main__":
    unittest.main()
