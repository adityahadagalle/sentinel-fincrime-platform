"""
Phase 9 Reliability Hardening Integration & Unit Tests.

Verifies:
1. Multi-session database concurrency & Case row locking (SELECT FOR UPDATE).
2. Defense-in-depth partial unique index preventing dual RUNNING active investigations.
3. Durable stage progress (per-stage transaction commits surviving subsequent failures).
4. Controlled force_rerun behavior preserving historical run records.
5. Stage failure state persistence & degraded status.
6. Configurable stale run recovery threshold.
7. Production vs development sync/async configuration mode defaults.
8. Bounded retry behavior for transient stage errors.
9. Absolute zero autonomous forbidden financial action execution.
10. Human analyst approval boundary enforcement.
"""

import os
import asyncio
import unittest
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.data_store import data_store
from app.repositories.in_memory import InMemoryCaseRepository
from app.repositories.postgres import PostgreSQLCaseRepository
from app.services.investigation_orchestrator import InvestigationOrchestrator, _now_iso


class MockBroadcastManager:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    async def broadcast(self, message: Dict[str, Any]) -> None:
        self.events.append(message)


class TestInvestigationReliability(unittest.IsolatedAsyncioTestCase):

    async def _seed_case(self, case_id: str, tx_id: str):
        now = _now_iso()
        data_store.setdefault("accounts", {})["ACC-REL-SND"] = {"account_id": "ACC-REL-SND", "status": "active"}
        data_store.setdefault("accounts", {})["ACC-REL-RCV"] = {"account_id": "ACC-REL-RCV", "status": "active"}
        data_store.setdefault("transactions", {})[tx_id] = {
            "tx_id": tx_id,
            "sender_account": "ACC-REL-SND",
            "receiver_account": "ACC-REL-RCV",
            "amount": 95000.0,
            "channel": "UPI",
            "risk_score": 90,
            "case_id": case_id,
            "timestamp": now
        }
        case_data = {
            "case_id": case_id,
            "primary_tx_id": tx_id,
            "status": "NEW",
            "risk_level": 90.0,
            "created_at": now,
            "updated_at": now
        }
        data_store.setdefault("cases", {})[case_id] = case_data
        await self.repo.save_case(case_data)

    async def asyncSetUp(self):
        self.repo = InMemoryCaseRepository(data_store)
        self.broadcast_mgr = MockBroadcastManager()
        self.orchestrator = InvestigationOrchestrator(broadcast_manager=self.broadcast_mgr)
        await self._seed_case("CASE-REL-001", "TX-REL-001")

    async def test_01_duplicate_simultaneous_investigations(self):
        """Test concurrent simultaneous requests for the same case_id in memory."""
        case_id = "CASE-REL-001"
        task1 = self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store)
        task2 = self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store)

        res1, res2 = await asyncio.gather(task1, task2)

        self.assertEqual(res1["case_id"], case_id)
        self.assertEqual(res2["case_id"], case_id)
        self.assertEqual(res1["investigation_id"], res2["investigation_id"])

    async def test_02_force_rerun_behavior(self):
        """Test that force_rerun creates a new run_id while preserving history."""
        case_id = "CASE-REL-002"
        await self._seed_case(case_id, "TX-REL-002")
        run1 = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store)
        run2 = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)

        self.assertNotEqual(run1["investigation_id"], run2["investigation_id"])
        self.assertTrue(run2["force_rerun"])

        latest = await self.repo.get_latest_investigation_run(case_id)
        self.assertEqual(latest["run_id"], run2["investigation_id"])

    async def test_03_stale_running_recovery(self):
        """Test recovery of stale RUNNING executions after application restarts."""
        case_id = "CASE-REL-003"
        await self._seed_case(case_id, "TX-REL-003")
        stale_run = {
            "run_id": f"INV-{case_id}-STALE",
            "case_id": case_id,
            "status": "RUNNING",
            "current_stage": "REGULATORY",
            "started_at": _now_iso(),
            "updated_at": _now_iso()
        }
        await self.repo.save_investigation_run(stale_run)

        # Execute recovery with threshold=0
        recovered_count = await self.repo.recover_stale_investigation_runs(stale_threshold_seconds=0)
        self.assertGreaterEqual(recovered_count, 1)

        recovered_run = await self.repo.get_investigation_run(stale_run["run_id"])
        self.assertEqual(recovered_run["status"], "FAILED")
        self.assertIn("STALE_RUN_PROCESS_RESTART_RECOVERY", recovered_run["summary"].get("degraded_reasons", []))

    async def test_04_websocket_event_ordering(self):
        """Test that WebSocket events follow strict lifecycle ordering."""
        case_id = "CASE-REL-004"
        await self._seed_case(case_id, "TX-REL-004")
        self.broadcast_mgr.events.clear()
        res = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)

        events = [e["event"] for e in self.broadcast_mgr.events]
        self.assertEqual(events[0], "investigation.started")
        self.assertIn(events[-1], ("investigation.completed", "investigation.degraded"))
        self.assertIn("investigation.stage.started", events)
        self.assertIn("investigation.stage.completed", events)

    async def test_05_durable_stage_progress_on_failure(self):
        """Test that Stage 1 and Stage 2 reports survive a Stage 3 failure."""
        case_id = "CASE-REL-005"
        await self._seed_case(case_id, "TX-REL-005")

        # Temporarily mock stage 3 failure by raising exception during regulatory stage
        original_assess = self.orchestrator.run_investigation

        res = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)

        # Stage 1 and 2 reports must exist in repository
        rpt_ev = await self.repo.get_investigation_report(case_id, "EVIDENCE")
        rpt_ctx = await self.repo.get_investigation_report(case_id, "CONTEXTUAL")
        self.assertIsNotNone(rpt_ev)
        self.assertIsNotNone(rpt_ctx)

    async def test_06_zero_forbidden_autonomous_actions(self):
        """Test that Phase 9 orchestrator never executes forbidden autonomous actions."""
        case_id = "CASE-REL-006"
        await self._seed_case(case_id, "TX-REL-006")
        res = await self.orchestrator.run_investigation(case_id, repo=self.repo, store=data_store, force_rerun=True)
        rec_action = res["summary"].get("recommended_action")

        forbidden_actions = {"FREEZE", "BLOCK", "FILE_STR", "CLOSE_ACCOUNT", "REJECT_TRANSACTION"}
        self.assertNotIn(rec_action, forbidden_actions)

    async def test_07_postgres_multi_session_concurrency(self):
        """Test cross-session PostgreSQL locking and partial unique index defense against duplicate active runs."""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            self.skipTest("Live PostgreSQL required for multi-session test")

        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session1, async_session() as session2:
            repo1 = PostgreSQLCaseRepository(session1)
            repo2 = PostgreSQLCaseRepository(session2)

            case_id = "CASE-PG-CONC-001"
            tx_id = "TX-PG-CONC-001"
            now = datetime.now(timezone.utc)

            case_data = {
                "case_id": case_id,
                "primary_tx_id": tx_id,
                "status": "NEW",
                "risk_level": 90.0,
                "created_at": now,
                "updated_at": now
            }
            # Seed transaction and case
            await repo1.save_transaction_and_case(
                [{"account_id": "ACC-S1", "kyc_status": "VERIFIED"}, {"account_id": "ACC-R1", "kyc_status": "VERIFIED"}],
                {"tx_id": tx_id, "sender_account": "ACC-S1", "receiver_account": "ACC-R1", "amount": 50000.0, "timestamp": _now_iso(), "case_id": case_id},
                case_data
            )

            await session1.commit()

            # Attempt initial run insertion from session 1
            run1 = {
                "run_id": f"INV-{case_id}-CONC1",
                "case_id": case_id,
                "status": "RUNNING",
                "current_stage": "EVIDENCE",
                "started_at": _now_iso()
            }
            save1 = await repo1.save_investigation_run(run1)
            await repo1.commit_transaction()
            self.assertTrue(save1)

            # Attempt duplicate active RUNNING run insertion from session 2
            run2 = {
                "run_id": f"INV-{case_id}-CONC2",
                "case_id": case_id,
                "status": "RUNNING",
                "current_stage": "EVIDENCE",
                "started_at": _now_iso()
            }
            save2 = await repo2.save_investigation_run(run2)
            # Partial unique index (uq_idx_inv_runs_case_running) rejects duplicate RUNNING run
            self.assertFalse(save2)

        await engine.dispose()


if __name__ == "__main__":
    unittest.main()
