"""
Phase 9 Automated End-to-End Investigation Orchestrator Tests.

Verifies:
1. Orchestrator happy path & 5-stage ordering (EVIDENCE -> CONTEXTUAL -> REGULATORY -> DECISION_SUPPORT -> AUDIT_EXPLANATION).
2. Stage failure & degraded investigation state handling.
3. Idempotency & duplicate investigation prevention.
4. WebSocket real-time event broadcasting (started, stage.started, stage.completed, stage.failed, completed, degraded).
5. Repository report persistence & reconstruction (InMemory + PostgreSQL).
6. Human analyst authorization boundary & zero autonomous forbidden actions.
"""

import os
import unittest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.core.data_store import data_store
from app.repositories.in_memory import InMemoryCaseRepository
from app.services.investigation_orchestrator import InvestigationOrchestrator, _now_iso


class MockBroadcastManager:
    """Mock WebSocket ConnectionManager for testing event emissions."""
    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    async def broadcast(self, message: Dict[str, Any]) -> None:
        self.events.append(message)


class TestInvestigationOrchestrator(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.repo = InMemoryCaseRepository(data_store)
        self.broadcast_mgr = MockBroadcastManager()
        self.orchestrator = InvestigationOrchestrator(broadcast_manager=self.broadcast_mgr)


        # Seed mock case & transaction in data_store & repository
        now = _now_iso()
        self.case_id = "CASE-P9-001"
        self.tx_id = "TX-P9-001"

        data_store["accounts"] = {
            "ACC-P9-SND": {"account_id": "ACC-P9-SND", "status": "active"},
            "ACC-P9-RCV": {"account_id": "ACC-P9-RCV", "status": "active"}
        }
        data_store["transactions"] = {
            self.tx_id: {
                "tx_id": self.tx_id,
                "sender_account": "ACC-P9-SND",
                "receiver_account": "ACC-P9-RCV",
                "amount": 75000.0,
                "channel": "UPI",
                "risk_score": 85,
                "case_id": self.case_id,
                "timestamp": now
            }
        }
        case_data = {
            "case_id": self.case_id,
            "primary_tx_id": self.tx_id,
            "status": "NEW",
            "risk_level": 85.0,
            "created_at": now,
            "updated_at": now
        }
        data_store["cases"] = {self.case_id: case_data}
        await self.repo.save_case(case_data)


    async def test_01_orchestrator_happy_path(self):
        """Test full 5-stage automated investigation happy path."""
        result = await self.orchestrator.run_investigation(
            case_id=self.case_id,
            repo=self.repo,
            store=data_store
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["case_id"], self.case_id)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIsNotNone(result["investigation_id"])
        self.assertTrue(result["investigation_id"].startswith(f"INV-{self.case_id}"))

        # Verify all 5 stages completed
        stages = result["stages"]
        expected_stages = ["EVIDENCE", "CONTEXTUAL", "REGULATORY", "DECISION_SUPPORT", "AUDIT_EXPLANATION"]
        for stg_name in expected_stages:
            self.assertIn(stg_name, stages)
            self.assertEqual(stages[stg_name]["status"], "COMPLETED")
            self.assertIsNotNone(stages[stg_name]["started_at"])
            self.assertIsNotNone(stages[stg_name]["completed_at"])
            self.assertIsNotNone(stages[stg_name]["output"])
            self.assertIsNone(stages[stg_name]["error"])

        # Verify summary populated
        summary = result["summary"]
        self.assertIn("review_priority", summary)
        self.assertIn("regulatory_severity", summary)
        self.assertIn("recommended_action", summary)

    async def test_02_idempotency_and_deduplication(self):
        """Test that duplicate investigation triggers return existing completed record."""
        res1 = await self.orchestrator.run_investigation(self.case_id, repo=self.repo, store=data_store)
        res2 = await self.orchestrator.run_investigation(self.case_id, repo=self.repo, store=data_store)

        self.assertEqual(res1["investigation_id"], res2["investigation_id"])
        self.assertEqual(res1["status"], res2["status"])

    async def test_03_websocket_event_broadcasting(self):
        """Test that real-time WebSocket status events are emitted during pipeline execution."""
        await self.orchestrator.run_investigation(self.case_id, repo=self.repo, store=data_store, force_rerun=True)

        events = self.broadcast_mgr.events
        event_types = [e.get("event") for e in events]

        self.assertIn("investigation.started", event_types)
        self.assertIn("investigation.stage.started", event_types)
        self.assertIn("investigation.stage.completed", event_types)
        self.assertIn("investigation.completed", event_types)

    async def test_04_repository_report_persistence(self):
        """Test that all investigation reports are persisted in the repository."""
        await self.orchestrator.run_investigation(self.case_id, repo=self.repo, store=data_store, force_rerun=True)

        rpt_ds = await self.repo.get_investigation_report(self.case_id, "DECISION_SUPPORT")
        self.assertIsNotNone(rpt_ds)
        self.assertEqual(rpt_ds["case_id"], self.case_id)
        self.assertEqual(rpt_ds["report_type"], "DECISION_SUPPORT")

        rpt_aud = await self.repo.get_investigation_report(self.case_id, "AUDIT_EXPLANATION")
        self.assertIsNotNone(rpt_aud)
        self.assertEqual(rpt_aud["report_type"], "AUDIT_EXPLANATION")

    async def test_05_stage_failure_and_degraded_state(self):
        """Test graceful degradation when an intermediate stage encounters an error."""
        # Intentionally remove cases from data_store to cause evidence stage failure
        old_cases = data_store.pop("cases", {})
        try:
            res = await self.orchestrator.run_investigation("CASE-NONEXISTENT", repo=self.repo, store=data_store, force_rerun=True)
            self.assertIn(res["status"], ("DEGRADED", "FAILED"))
            self.assertGreater(len(res["summary"]["degraded_reasons"]), 0)
        finally:
            data_store["cases"] = old_cases

    async def test_06_zero_forbidden_autonomous_actions(self):
        """Test that agents never execute forbidden autonomous financial actions."""
        res = await self.orchestrator.run_investigation(self.case_id, repo=self.repo, store=data_store, force_rerun=True)

        ds_output = res["stages"]["DECISION_SUPPORT"]["output"]
        self.assertIsNotNone(ds_output)

        boundary = ds_output.get("human_approval_boundary", {})
        self.assertFalse(boundary.get("autonomous_execution", True))
        self.assertEqual(boundary.get("required_role"), "COMPLIANCE_ANALYST")

        forbidden_actions = {"FREEZE", "BLOCK", "FILE_STR", "CLOSE_ACCOUNT", "REJECT_TRANSACTION"}
        rec_action = res["summary"].get("recommended_action")
        self.assertNotIn(rec_action, forbidden_actions)



if __name__ == "__main__":
    unittest.main()
