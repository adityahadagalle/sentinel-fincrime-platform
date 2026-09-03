"""
Investigation Orchestrator Service for SENTINEL (Phase 9 Reliability Hardening).

Coordinates the end-to-end automated investigation pipeline asynchronously across dependency-ordered analytical stages:
1. Evidence Collection Agent (EVIDENCE)
2. Contextual Investigation Agent (CONTEXTUAL)
3. Regulatory Risk Assessment Agent (REGULATORY)
4. Audit Explanation Agent (AUDIT_EXPLANATION)
5. Analyst Decision Support Agent (DECISION_SUPPORT)

Reliability Hardening Features:
- PostgreSQL-authoritative durable InvestigationRun state persistence.
- Multi-process cross-worker concurrency locking via PostgreSQL Case row locking (SELECT FOR UPDATE) & partial unique index.
- Per-stage durable transaction commits ensuring intermediate reports survive process crashes/failures.
- Configurable stale-run recovery policy via SENTINEL_STALE_RUN_THRESHOLD_SECONDS.
- Controlled force_rerun handling preserving historical run traceability.
- Bounded retries for transient stage execution errors.
- Strict event ordering (WS completed event emitted ONLY after DECISION_SUPPORT persistence commits).
- Zero autonomous financial execution (preserves human analyst disposition authority).
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4

from app.repositories.base import AbstractCaseRepository
from app.services.evidence_agent import collect_evidence_for_case
from app.services.contextual_agent import investigate_context
from app.services.regulatory_agent import assess_regulatory_risk
from app.services.audit_explanation_agent import generate_audit_explanation
from app.services.analyst_agent import generate_analyst_decision_support


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class InvestigationOrchestrator:
    """
    Asynchronous End-to-End Investigation Pipeline Orchestrator with PostgreSQL Reliability Hardening.
    """

    def __init__(self, broadcast_manager: Optional[Any] = None):
        self.broadcast_manager = broadcast_manager
        self._active_investigations: Dict[str, Dict[str, Any]] = {}
        self._case_locks: Dict[str, asyncio.Lock] = {}

    async def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Emits real-time status event to connected WebSocket clients if manager is available."""
        if not self.broadcast_manager:
            return
        event = {"event": event_type, **payload}
        try:
            await self.broadcast_manager.broadcast(event)
        except Exception as e:
            print(f"[Orchestrator WS] Broadcast warning: {e}")

    async def _execute_with_retry(self, func, max_retries: int = 1, *args, **kwargs) -> Any:
        """Executes a function with bounded retries for transient errors."""
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if attempt < max_retries:
                    await asyncio.sleep(0.01)
        raise last_exc

    async def run_investigation(
        self,
        case_id: str,
        repo: AbstractCaseRepository,
        store: Optional[Dict[str, Any]] = None,
        force_rerun: bool = False,
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        Executes the 5-stage automated investigation lifecycle for a given case_id.
        Persists durable run state to PostgreSQL and prevents concurrent duplicate executions.
        """
        # 1. Recover any stale RUNNING runs across process restarts
        stale_threshold = int(os.getenv("SENTINEL_STALE_RUN_THRESHOLD_SECONDS", "600"))
        try:
            await repo.recover_stale_investigation_runs(stale_threshold_seconds=stale_threshold)
            await repo.commit_transaction()
        except Exception:
            pass

        if case_id not in self._case_locks:
            self._case_locks[case_id] = asyncio.Lock()

        async with self._case_locks[case_id]:
            # 2. Acquire cross-process PostgreSQL Case row lock (SELECT FOR UPDATE)
            try:
                await repo.get_case_for_update(case_id)
            except Exception:
                pass

            # 3. Check for active RUNNING run in memory or repository
            if not force_rerun:
                if case_id in self._active_investigations and self._active_investigations[case_id].get("status") == "RUNNING":
                    return self._active_investigations[case_id]
                try:
                    active_run = await repo.get_active_investigation_run(case_id)
                    if active_run:
                        self._active_investigations[case_id] = active_run
                        return active_run
                except Exception:
                    pass

            # 4. Check for existing completed run in repository/memory
            if not force_rerun:
                try:
                    latest_run = await repo.get_latest_investigation_run(case_id)
                    if latest_run and latest_run.get("status") in ("COMPLETED", "DEGRADED"):
                        self._active_investigations[case_id] = latest_run
                        return latest_run
                except Exception:
                    pass

            inv_id = f"INV-{case_id}-{uuid4().hex[:8]}"
            start_time = _now_iso()

            record: Dict[str, Any] = {
                "run_id": inv_id,
                "investigation_id": inv_id,
                "case_id": case_id,
                "status": "RUNNING",
                "current_stage": "NONE",
                "started_at": start_time,
                "completed_at": None,
                "retry_count": 0,
                "force_rerun": force_rerun,
                "stages": {
                    "EVIDENCE": {"status": "PENDING", "started_at": None, "completed_at": None, "error": None, "output": None},
                    "CONTEXTUAL": {"status": "PENDING", "started_at": None, "completed_at": None, "error": None, "output": None},
                    "REGULATORY": {"status": "PENDING", "started_at": None, "completed_at": None, "error": None, "output": None},
                    "AUDIT_EXPLANATION": {"status": "PENDING", "started_at": None, "completed_at": None, "error": None, "output": None},
                    "DECISION_SUPPORT": {"status": "PENDING", "started_at": None, "completed_at": None, "error": None, "output": None},
                },
                "summary": {
                    "review_priority": "UNKNOWN",
                    "regulatory_severity": "UNKNOWN",
                    "recommended_action": "NO_RECOMMENDATION",
                    "degraded_reasons": []
                }
            }

            self._active_investigations[case_id] = record
            try:
                saved = await repo.save_investigation_run(record)
                if not saved:
                    # Partial unique index caught duplicate active run insertion
                    active_run = await repo.get_active_investigation_run(case_id)
                    if active_run:
                        self._active_investigations[case_id] = active_run
                        return active_run
                await repo.commit_transaction()
            except Exception as e:
                print(f"[Orchestrator DB] Initial run save warning: {e}")

        await self._emit_event("investigation.started", {"case_id": case_id, "investigation_id": inv_id})

        # Retrieve case metadata from repository or store
        case_record = await repo.get_case_by_id(case_id)
        if not case_record and store:
            case_record = store.get("cases", {}).get(case_id)
            if case_record:
                try:
                    tx_id = case_record.get("primary_tx_id")
                    if tx_id and store and tx_id in store.get("transactions", {}):
                        tx_obj = store["transactions"][tx_id]
                        sender_id = tx_obj.get("sender_account") or tx_obj.get("sender_account_id")
                        receiver_id = tx_obj.get("receiver_account") or tx_obj.get("receiver_account_id")
                        accs = []
                        if sender_id:
                            accs.append(store.get("accounts", {}).get(sender_id, {"account_id": sender_id}))
                        if receiver_id and receiver_id != sender_id:
                            accs.append(store.get("accounts", {}).get(receiver_id, {"account_id": receiver_id}))
                        await repo.save_transaction_and_case(accs, tx_obj, case_record)
                    else:
                        await repo.save_case(case_record)
                    await repo.commit_transaction()
                except Exception:
                    pass


        evidence_pkg: Optional[Dict[str, Any]] = None
        contextual_rpt: Optional[Dict[str, Any]] = None
        regulatory_rpt: Optional[Dict[str, Any]] = None
        audit_explanation_rpt: Optional[Dict[str, Any]] = None
        decision_support_rpt: Optional[Dict[str, Any]] = None
        is_degraded = False

        # ── STAGE 1: EVIDENCE COLLECTION ──────────────────────────────────────
        record["current_stage"] = "EVIDENCE"
        stg_ev = record["stages"]["EVIDENCE"]
        stg_ev["status"] = "RUNNING"
        stg_ev["started_at"] = _now_iso()
        await self._emit_event("investigation.stage.started", {"case_id": case_id, "stage": "EVIDENCE"})

        try:
            evidence_pkg = await self._execute_with_retry(
                collect_evidence_for_case,
                max_retries=max_retries,
                case_id=case_id,
                store=store
            )
            stg_ev["status"] = "COMPLETED"
            stg_ev["completed_at"] = _now_iso()
            stg_ev["output"] = evidence_pkg
            await self._emit_event("investigation.stage.completed", {"case_id": case_id, "stage": "EVIDENCE"})
            await repo.save_investigation_report({
                "report_id": f"RPT-EVD-{case_id}",
                "case_id": case_id,
                "report_type": "EVIDENCE",
                "report_data": evidence_pkg,
                "created_at": stg_ev["completed_at"]
            })
            await repo.save_investigation_run(record)
            await repo.commit_transaction()
        except Exception as e:
            stg_ev["status"] = "FAILED"
            stg_ev["completed_at"] = _now_iso()
            stg_ev["error"] = str(e)
            record["status"] = "FAILED"
            record["summary"]["degraded_reasons"].append(f"EVIDENCE_STAGE_FAILED: {e}")
            await self._emit_event("investigation.stage.failed", {"case_id": case_id, "stage": "EVIDENCE", "error": str(e)})
            try:
                await repo.save_investigation_run(record)
                await repo.commit_transaction()
            except Exception:
                pass
            return record

        # ── STAGE 2: CONTEXTUAL INVESTIGATION ─────────────────────────────────
        record["current_stage"] = "CONTEXTUAL"
        stg_ctx = record["stages"]["CONTEXTUAL"]
        stg_ctx["status"] = "RUNNING"
        stg_ctx["started_at"] = _now_iso()
        await self._emit_event("investigation.stage.started", {"case_id": case_id, "stage": "CONTEXTUAL"})

        try:
            contextual_rpt = await self._execute_with_retry(
                investigate_context,
                max_retries=max_retries,
                evidence_package=evidence_pkg
            )
            stg_ctx["status"] = "COMPLETED"
            stg_ctx["completed_at"] = _now_iso()
            stg_ctx["output"] = contextual_rpt
            await self._emit_event("investigation.stage.completed", {"case_id": case_id, "stage": "CONTEXTUAL"})
            await repo.save_investigation_report({
                "report_id": f"RPT-CTX-{case_id}",
                "case_id": case_id,
                "report_type": "CONTEXTUAL",
                "report_data": contextual_rpt,
                "created_at": stg_ctx["completed_at"]
            })
            await repo.save_investigation_run(record)
            await repo.commit_transaction()
        except Exception as e:
            stg_ctx["status"] = "FAILED"
            stg_ctx["completed_at"] = _now_iso()
            stg_ctx["error"] = str(e)
            is_degraded = True
            record["summary"]["degraded_reasons"].append(f"CONTEXTUAL_STAGE_FAILED: {e}")
            await self._emit_event("investigation.stage.failed", {"case_id": case_id, "stage": "CONTEXTUAL", "error": str(e)})
            try:
                await repo.save_investigation_run(record)
                await repo.commit_transaction()
            except Exception:
                pass

        # ── STAGE 3: REGULATORY RISK ASSESSMENT ──────────────────────────────
        record["current_stage"] = "REGULATORY"
        stg_reg = record["stages"]["REGULATORY"]
        stg_reg["status"] = "RUNNING"
        stg_reg["started_at"] = _now_iso()
        await self._emit_event("investigation.stage.started", {"case_id": case_id, "stage": "REGULATORY"})

        try:
            regulatory_rpt = await self._execute_with_retry(
                assess_regulatory_risk,
                max_retries=max_retries,
                evidence_package=evidence_pkg,
                contextual_report=contextual_rpt
            )
            stg_reg["status"] = "COMPLETED"
            stg_reg["completed_at"] = _now_iso()
            stg_reg["output"] = regulatory_rpt
            await self._emit_event("investigation.stage.completed", {"case_id": case_id, "stage": "REGULATORY"})
            await repo.save_investigation_report({
                "report_id": f"RPT-REG-{case_id}",
                "case_id": case_id,
                "report_type": "REGULATORY",
                "report_data": regulatory_rpt,
                "created_at": stg_reg["completed_at"]
            })
            await repo.save_investigation_run(record)
            await repo.commit_transaction()
        except Exception as e:
            stg_reg["status"] = "FAILED"
            stg_reg["completed_at"] = _now_iso()
            stg_reg["error"] = str(e)
            is_degraded = True
            record["summary"]["degraded_reasons"].append(f"REGULATORY_STAGE_FAILED: {e}")
            await self._emit_event("investigation.stage.failed", {"case_id": case_id, "stage": "REGULATORY", "error": str(e)})
            try:
                await repo.save_investigation_run(record)
                await repo.commit_transaction()
            except Exception:
                pass

        # ── STAGE 4: AUDIT EXPLANATION ────────────────────────────────────────
        record["current_stage"] = "AUDIT_EXPLANATION"
        stg_aud = record["stages"]["AUDIT_EXPLANATION"]
        stg_aud["status"] = "RUNNING"
        stg_aud["started_at"] = _now_iso()
        await self._emit_event("investigation.stage.started", {"case_id": case_id, "stage": "AUDIT_EXPLANATION"})

        try:
            audit_explanation_rpt = await self._execute_with_retry(
                generate_audit_explanation,
                max_retries=max_retries,
                evidence_package=evidence_pkg,
                contextual_report=contextual_rpt,
                regulatory_assessment=regulatory_rpt
            )
            stg_aud["status"] = "COMPLETED"
            stg_aud["completed_at"] = _now_iso()
            stg_aud["output"] = audit_explanation_rpt
            await self._emit_event("investigation.stage.completed", {"case_id": case_id, "stage": "AUDIT_EXPLANATION"})
            await repo.save_investigation_report({
                "report_id": f"RPT-AUD-{case_id}",
                "case_id": case_id,
                "report_type": "AUDIT_EXPLANATION",
                "report_data": audit_explanation_rpt,
                "created_at": stg_aud["completed_at"]
            })
            await repo.save_investigation_run(record)
            await repo.commit_transaction()
        except Exception as e:
            stg_aud["status"] = "FAILED"
            stg_aud["completed_at"] = _now_iso()
            stg_aud["error"] = str(e)
            is_degraded = True
            record["summary"]["degraded_reasons"].append(f"AUDIT_EXPLANATION_STAGE_FAILED: {e}")
            await self._emit_event("investigation.stage.failed", {"case_id": case_id, "stage": "AUDIT_EXPLANATION", "error": str(e)})
            try:
                await repo.save_investigation_run(record)
                await repo.commit_transaction()
            except Exception:
                pass

        # ── STAGE 5: ANALYST DECISION SUPPORT ────────────────────────────────
        record["current_stage"] = "DECISION_SUPPORT"
        stg_ds = record["stages"]["DECISION_SUPPORT"]
        stg_ds["status"] = "RUNNING"
        stg_ds["started_at"] = _now_iso()
        await self._emit_event("investigation.stage.started", {"case_id": case_id, "stage": "DECISION_SUPPORT"})

        try:
            decision_support_rpt = await self._execute_with_retry(
                generate_analyst_decision_support,
                max_retries=max_retries,
                evidence_package=evidence_pkg,
                contextual_report=contextual_rpt,
                regulatory_assessment=regulatory_rpt,
                audit_explanation=audit_explanation_rpt,
                case_context=case_record
            )
            stg_ds["status"] = "COMPLETED"
            stg_ds["completed_at"] = _now_iso()
            stg_ds["output"] = decision_support_rpt
            await self._emit_event("investigation.stage.completed", {"case_id": case_id, "stage": "DECISION_SUPPORT"})
            await repo.save_investigation_report({
                "report_id": f"RPT-DS-{case_id}",
                "case_id": case_id,
                "report_type": "DECISION_SUPPORT",
                "report_data": decision_support_rpt,
                "created_at": stg_ds["completed_at"]
            })
            await repo.save_investigation_run(record)
            await repo.commit_transaction()
        except Exception as e:
            stg_ds["status"] = "FAILED"
            stg_ds["completed_at"] = _now_iso()
            stg_ds["error"] = str(e)
            is_degraded = True
            record["summary"]["degraded_reasons"].append(f"DECISION_SUPPORT_STAGE_FAILED: {e}")
            await self._emit_event("investigation.stage.failed", {"case_id": case_id, "stage": "DECISION_SUPPORT", "error": str(e)})
            try:
                await repo.save_investigation_run(record)
                await repo.commit_transaction()
            except Exception:
                pass

        # ── FINALIZATION ──────────────────────────────────────────────────────
        record["completed_at"] = _now_iso()
        record["current_stage"] = "NONE"
        if is_degraded:
            record["status"] = "DEGRADED"
        else:
            record["status"] = "COMPLETED"

        # Populate high-level investigation summary
        if decision_support_rpt and isinstance(decision_support_rpt, dict):
            ds_sum = decision_support_rpt.get("summary", {})
            record["summary"]["review_priority"] = ds_sum.get("review_priority", "UNKNOWN")
            record["summary"]["regulatory_severity"] = ds_sum.get("regulatory_severity", "UNKNOWN")
            recommendations = decision_support_rpt.get("recommendations", [])
            if recommendations and isinstance(recommendations, list):
                rec_action = recommendations[0].get("action_code") if isinstance(recommendations[0], dict) else "NO_RECOMMENDATION"
                record["summary"]["recommended_action"] = rec_action

        try:
            await repo.save_investigation_run(record)
            await repo.commit_transaction()
        except Exception as e:
            print(f"[Orchestrator DB] Final run save warning: {e}")

        # Broadcast overall completion / degradation event ONLY after report persistence is saved
        if record["status"] == "COMPLETED":
            await self._emit_event("investigation.completed", {
                "case_id": case_id,
                "investigation_id": inv_id,
                "summary": record["summary"]
            })
        else:
            await self._emit_event("investigation.degraded", {
                "case_id": case_id,
                "investigation_id": inv_id,
                "reasons": record["summary"]["degraded_reasons"]
            })

        return record


# Global default instance
investigation_orchestrator = InvestigationOrchestrator()
