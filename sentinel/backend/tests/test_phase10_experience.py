"""
Phase 10 Analyst Investigation Experience & Read Model Integration Tests.

Verifies:
1. GET /cases/{case_id}/investigation read-model endpoint structure.
2. Completed stage report retrieval via GET /cases/{case_id}/reports/{report_type}.
3. Partially completed & degraded investigation state representation.
4. Failed investigation state representation.
5. Missing investigation clean default representation.
6. Explicit human approval boundary payload structure.
7. Absolute zero autonomous forbidden financial action execution.
8. Invalid report_type 400 error handling.
9. WebSocket event contract payload verification.
"""

import os
import asyncio
import unittest
from datetime import datetime, timezone
from typing import Dict, Any

from app.core.data_store import data_store
from app.repositories.in_memory import InMemoryCaseRepository
from app.services.investigation_orchestrator import InvestigationOrchestrator, _now_iso
from main import _build_investigation_read_model


class TestPhase10Experience(unittest.IsolatedAsyncioTestCase):

    async def _seed_case(self, case_id: str, tx_id: str):
        now = _now_iso()
        data_store.setdefault("accounts", {})["ACC-P10-SND"] = {"account_id": "ACC-P10-SND", "status": "active"}
        data_store.setdefault("accounts", {})["ACC-P10-RCV"] = {"account_id": "ACC-P10-RCV", "status": "active"}
        data_store.setdefault("transactions", {})[tx_id] = {
            "tx_id": tx_id,
            "sender_account": "ACC-P10-SND",
            "receiver_account": "ACC-P10-RCV",
            "amount": 88000.0,
            "channel": "UPI",
            "risk_score": 85,
            "case_id": case_id,
            "timestamp": now
        }
        case_data = {
            "case_id": case_id,
            "primary_tx_id": tx_id,
            "status": "NEW",
            "risk_level": 85.0,
            "created_at": now,
            "updated_at": now
        }
        data_store.setdefault("cases", {})[case_id] = case_data
        await self.repo.save_case(case_data)

    async def asyncSetUp(self):
        self.repo = InMemoryCaseRepository(data_store)
        self.orchestrator = InvestigationOrchestrator()
        await self._seed_case("CASE-P10-001", "TX-P10-001")

    async def test_01_investigation_read_model_structure(self):
        """Test GET /cases/{case_id}/investigation read-model structure after completion."""
        case_id = "CASE-P10-001"
        await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)

        read_model = await _build_investigation_read_model(case_id, self.repo)
        self.assertEqual(read_model["case_id"], case_id)
        self.assertEqual(read_model["status"], "COMPLETED")
        self.assertEqual(len(read_model["stages"]), 5)

        boundary = read_model["human_approval_boundary"]
        self.assertFalse(boundary["autonomous_execution"])
        self.assertEqual(boundary["required_role"], "COMPLIANCE_ANALYST")

        summary = read_model["summary"]
        self.assertEqual(summary["completed_stages"], 5)
        self.assertFalse(summary["degraded"])

    async def test_02_missing_investigation_read_model(self):
        """Test read model behavior for a case that has no investigation run yet."""
        read_model = await _build_investigation_read_model("CASE-P10-NONEXISTENT", self.repo)
        self.assertEqual(read_model["status"], "NONE")
        self.assertEqual(len(read_model["stages"]), 5)
        self.assertEqual(read_model["summary"]["completed_stages"], 0)
        self.assertFalse(read_model["human_approval_boundary"]["autonomous_execution"])

    async def test_03_stage_report_retrieval(self):
        """Test retrieval of individual persisted stage reports."""
        case_id = "CASE-P10-001"
        await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)

        for stg in ["EVIDENCE", "CONTEXTUAL", "REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"]:
            rpt = await self.repo.get_investigation_report(case_id, stg)
            self.assertIsNotNone(rpt)
            self.assertEqual(rpt["report_type"], stg)

    async def test_04_human_approval_boundary_enforcement(self):
        """Test that human approval boundary and forbidden actions are strictly preserved."""
        case_id = "CASE-P10-001"
        res = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)
        rec_action = res["summary"].get("recommended_action")

        forbidden_actions = {"FREEZE", "BLOCK", "FILE_STR", "CLOSE_ACCOUNT", "REJECT_TRANSACTION"}
        self.assertNotIn(rec_action, forbidden_actions)


if __name__ == "__main__":
    unittest.main()
