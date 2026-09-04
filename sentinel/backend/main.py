from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import asyncio
import random
import string

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query

from pydantic import BaseModel

import os
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session, close_async_engine
from app.repositories.postgres import PostgreSQLCaseRepository
from app.core.data_store import data_store
from app.repositories.base import AbstractCaseRepository
from app.repositories.in_memory import InMemoryCaseRepository
from app.services.mock_apis import mock_bank_freeze, mock_police_alert, mock_telecom_flag, mock_monitor_account, mock_close_case
from app.services.orchestrator import run_pipeline
from app.services.evidence_agent import collect_evidence, collect_evidence_for_case, collect_evidence_for_transaction
from app.services.contextual_agent import investigate_context, investigate_case, investigate_transaction
from app.services.regulatory_agent import assess_regulatory_risk, assess_case_regulatory_risk, assess_transaction_regulatory_risk
from app.services.audit_explanation_agent import generate_audit_explanation, generate_case_audit_explanation, generate_transaction_audit_explanation
from app.services.analyst_agent import generate_analyst_decision_support, generate_case_analyst_decision_support, generate_transaction_analyst_decision_support
from app.services.case_lifecycle_agent import (
    CaseLifecycleService,
    submit_case_disposition as submit_case_disposition_service,
    get_case_disposition_history,
    get_case_audit_history,
)
from app.services.investigation_orchestrator import investigation_orchestrator


from fastapi.middleware.cors import CORSMiddleware


from app.repositories.dependencies import get_repository



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager that handles background simulation loop startup, production fail-fast check, and engine cleanup.
    """
    sentinel_mode = os.getenv("SENTINEL_MODE", "development").lower()
    db_url = os.getenv("DATABASE_URL")
    if sentinel_mode == "production" and not db_url:
        raise RuntimeError("PRODUCTION CONFIGURATION FAILURE: DATABASE_URL environment variable is required in production mode.")

    loop_task = asyncio.create_task(_baseline_loop())
    yield
    loop_task.cancel()
    await close_async_engine()


app = FastAPI(title="SENTINEL - Real-Time Fraud Response System", lifespan=lifespan)

# Safe CORS configuration (Phase 12 Hardening)
cors_env = os.getenv("CORS_ORIGINS")
if cors_env:
    allowed_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── INTELLIGENCE ROUTER (Ollama/Qwen advisory layer) ──────────────────────────
from app.routes.intelligence import router as intelligence_router
app.include_router(intelligence_router)

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections = [ws for ws in self.active_connections if ws is not websocket]

    async def broadcast(self, message: dict[str, Any]) -> None:
        failed: list[WebSocket] = []
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                failed.append(ws)
        for ws in failed:
            self.disconnect(ws)


manager = ConnectionManager()
investigation_orchestrator.broadcast_manager = manager




def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_nodes(nodes: Any) -> list[dict[str, Any]]:
    if not isinstance(nodes, list):
        return []
    normalized = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        account_id = node.get("account_id") or node.get("accountId") or node.get("id")
        if not account_id:
            continue
        normalized.append(
            {
                "account_id": str(account_id),
                "accountId": str(account_id),
                "id": str(account_id),
                "status": node.get("status", "active"),
                "balance": float(node.get("balance", 0.0)),
                "account_type": node.get("account_type", "UNKNOWN"),
                "inbound_count": int(node.get("inbound_count", 0)),
                "outbound_count": int(node.get("outbound_count", 0)),
                "total_inbound": float(node.get("total_inbound", 0.0)),
                "total_outbound": float(node.get("total_outbound", 0.0)),
                "risk_score": float(node.get("risk_score", 0.0))
            }
        )
    return normalized


def _normalize_edges(edges: Any) -> list[dict[str, Any]]:
    if not isinstance(edges, list):
        return []
    normalized = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source") or edge.get("from")
        target = edge.get("target") or edge.get("to")
        tx_id = edge.get("tx_id") or edge.get("id") or f"{source}-{target}"
        if not source or not target:
            continue
        normalized.append(
            {
                "id": str(tx_id),
                "tx_id": str(tx_id),
                "source": str(source),
                "target": str(target),
                "from": str(source),
                "to": str(target),
                "amount": float(edge.get("amount", 0.0)),
                "timestamp": edge.get("timestamp", ""),
                "hop_number": int(edge.get("hop_number", 1)),
                "total_hops": int(edge.get("total_hops", 1)),
                "chain_id": edge.get("chain_id") or f"CHAIN-{str(tx_id)[:8]}",
                "pattern_type": edge.get("pattern_type") or "STANDARD",
                "parent_transaction_id": edge.get("parent_transaction_id"),
                "root_transaction_id": edge.get("root_transaction_id") or tx_id
            }
        )
    return normalized



def _normalize_action_log(case: dict[str, Any]) -> list[dict[str, Any]]:
    raw = case.get("actionLog")
    if isinstance(raw, list):
        return raw
    raw = case.get("actions_taken")
    if not isinstance(raw, list):
        return []
    normalized = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        target_id = entry.get("target_id") or entry.get("target") or "GLOBAL"
        normalized.append(
            {
                "action_id": str(entry.get("action_id") or f"action_{uuid4().hex[:10]}"),
                "case_id": entry.get("case_id") or case.get("case_id"),
                "action_type": str(entry.get("action_type") or "").upper(),
                "action": str(entry.get("action") or entry.get("action_type") or "").lower(),
                "target_id": target_id,
                "target": target_id,
                "status": entry.get("status", "ACK"),
                "timestamp": entry.get("timestamp") or _now_iso(),
                "reason": entry.get("reason", "System Action"),
                "latency": int(entry.get("latency", 0)),
            }
        )
    return normalized


def _case_payload(case: dict[str, Any]) -> dict[str, Any]:
    case_id = case.get("case_id", "")
    from app.engines.graph_engine import build_investigation_graph
    graph = build_investigation_graph(case_id, data_store)
    nodes = _normalize_nodes(graph.get("nodes", []))
    edges = _normalize_edges(graph.get("edges", []))

    # Fetch full transaction objects linked to this case
    tx_ids = case.get("transactions", [])
    tx_store = data_store.get("transactions", {})
    transactions = [tx_store[tid] for tid in tx_ids if tid in tx_store]
    if not transactions and case.get("primary_tx_id") and case.get("primary_tx_id") in tx_store:
        transactions = [tx_store[case.get("primary_tx_id")]]
    if not transactions:
        transactions = [t for t in tx_store.values() if t.get("case_id") == case_id]
    evidence_package = collect_evidence_for_case(case_id, data_store)
    contextual_investigation = investigate_context(evidence_package)
    regulatory_assessment = assess_regulatory_risk(evidence_package, contextual_investigation)
    audit_explanation = generate_audit_explanation(evidence_package, contextual_investigation, regulatory_assessment)
    analyst_decision_support = generate_analyst_decision_support(evidence_package, contextual_investigation, regulatory_assessment, audit_explanation, case_context=case)

    raw_rl = case.get("risk_level", "LOW")
    try:
        rl_val: Any = float(raw_rl)
    except (ValueError, TypeError):
        rl_val = str(raw_rl)

    return {
        "case_id": case_id,
        "status": case.get("status", "NEW"),
        "primary_tx_id": case.get("primary_tx_id", ""), # Expose primary TX
        "nodes": nodes,
        "edges": edges,
        "transactions": transactions, # Added full objects
        "recoverable_amount": float(case.get("recoverable_amount", 0.0)),
        "recovery_pct": float(case.get("recovery_pct", 0.0)),
        "actionLog": _normalize_action_log(case),
        "risk_level": rl_val,
        "golden_window_minutes": int(case.get("golden_window_minutes", 0)),
        "total_fraud_amount": float(case.get("total_fraud_amount", 0.0)),

        "chain": case.get("chain", []),
        "evidence_package": evidence_package,
        "contextual_investigation": contextual_investigation,
        "regulatory_assessment": regulatory_assessment,
        "audit_explanation": audit_explanation,
        "analyst_decision_support": analyst_decision_support,
    }


class EvidenceRequest(BaseModel):
    target_id: str | None = None
    case_id: str | None = None
    tx_id: str | None = None


class ActionRequest(BaseModel):
    case_id: str
    account_id: str | None = None
    target_id: str | None = None
    reason: str | None = None
    operator_id: str | None = "OPERATOR_ADMIN"



class DispositionRequest(BaseModel):
    case_id: str | None = None
    action_code: str
    analyst_notes: str | None = None
    analyst_id: str | None = "ANALYST-001"
    analyst_role: str | None = "COMPLIANCE_ANALYST"
    risk_acknowledged: bool = False
    idempotency_key: str | None = None



@app.get("/health")
async def health_check(
    session: Optional[AsyncSession] = Depends(get_db_session)
) -> dict[str, Any]:
    db_url = os.getenv("DATABASE_URL")
    sentinel_mode = os.getenv("SENTINEL_MODE", "development").lower()

    db_status = "disabled"
    if db_url or sentinel_mode == "production":
        if session is not None:
            try:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                db_status = "connected"
            except Exception as e:
                db_status = f"error: {str(e)}"
                raise HTTPException(status_code=503, detail={"status": "unhealthy", "database": db_status})
        else:
            db_status = "disconnected"
            raise HTTPException(status_code=503, detail={"status": "unhealthy", "database": db_status})

    return {
        "status": "healthy",
        "mode": sentinel_mode,
        "database": db_status,
        "timestamp": _now_iso()
    }



async def _run_background_investigation(case_id: str, store: dict):
    """
    Executes the automated investigation in a dedicated, isolated database session
    without holding or sharing the HTTP request's session.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url or os.getenv("SENTINEL_MODE") == "production":
        try:
            async for session in get_db_session():
                if session is None:
                    repo = InMemoryCaseRepository(store)
                    await investigation_orchestrator.run_investigation(case_id, repo=repo, store=store)
                    break
                repo = PostgreSQLCaseRepository(session)
                try:
                    await investigation_orchestrator.run_investigation(case_id, repo=repo, store=store)
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    print(f"[Background Investigation Error] {e}")
                break
        except Exception as e:
            print(f"[Background Session Error] {e}")
    else:
        repo = InMemoryCaseRepository(store)
        await investigation_orchestrator.run_investigation(case_id, repo=repo, store=store)



async def _process_policy_and_action(transaction: dict[str, Any], case: dict[str, Any] | None, repo=None) -> tuple[dict[str, Any], dict[str, Any]]:
    automate_mode = bool(data_store.get("automation_mode", False))
    from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
    from app.services.simulated_action_executor import execute_simulated_action

    policy_decision = evaluate_autonomous_policy(
        tx=transaction,
        case=case,
        automate_mode=automate_mode
    )

    execution_record = await execute_simulated_action(
        case_id=case.get("case_id") if case else transaction.get("case_id"),
        tx_id=transaction.get("tx_id"),
        action_code=policy_decision.get("action", "MONITOR"),
        policy_decision=policy_decision,
        repo=repo,
        actor_type="AUTOMATION_ENGINE"
    )


    transaction["execution_record"] = execution_record
    transaction["response_decision"] = policy_decision
    return policy_decision, execution_record


def _get_account_kyc_status(acc_id: str, acc_record: Optional[dict] = None) -> str:
    if acc_record and acc_record.get("kyc_status"):
        return str(acc_record["kyc_status"]).upper()
    if not acc_id:
        return "PENDING"
    upper = acc_id.upper()
    if upper.startswith("ACC-USR") or upper.startswith("ACC-MERCH") or upper.startswith("ACC-REGULAR"):
        return "VERIFIED"
    elif upper.startswith("ACC-EXIT"):
        return "UNVERIFIED"
    elif upper.startswith("ACC-MULE") or upper.startswith("ACC-HUB") or upper.startswith("ACC-LAYER"):
        return "PENDING"
    return "PENDING"


@app.post("/transaction")
async def process_tx(
    request: Request,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    try:
        tx = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(tx, dict) or not tx.get("tx_id"):
        raise HTTPException(status_code=400, detail="Invalid transaction payload structure")

    result = run_pipeline(tx, data_store)

    transaction = result.get("transaction") or {}
    case = result.get("case")

    sender_id = transaction.get("sender_account")
    receiver_id = transaction.get("receiver_account")
    accounts_to_save = []

    if sender_id:
        acc_s = data_store.get("accounts", {}).get(sender_id) or {
            "account_id": sender_id,
            "kyc_status": _get_account_kyc_status(sender_id)
        }
        accounts_to_save.append(acc_s)
    if receiver_id and receiver_id != sender_id:
        acc_r = data_store.get("accounts", {}).get(receiver_id) or {
            "account_id": receiver_id,
            "kyc_status": _get_account_kyc_status(receiver_id)
        }
        accounts_to_save.append(acc_r)

    await repo.save_transaction_and_case(accounts_to_save, transaction, case)

    policy_decision, execution_record = await _process_policy_and_action(transaction, case, repo=repo)
    result["execution_record"] = execution_record

    if isinstance(repo, PostgreSQLCaseRepository):
        await repo.session.commit()


    tx_event = {
        "event": "tx_scored",
        "tx_id": transaction.get("tx_id", ""),
        "timestamp": transaction.get("timestamp") or _now_iso(),
        "case_id": transaction.get("case_id", ""),
        "risk_score": float(transaction.get("risk_score", 0.0)),
        "amount": float(transaction.get("amount", 0.0)),
        "sender_account": transaction.get("sender_account", "UNKNOWN"),
        "receiver_account": transaction.get("receiver_account", "UNKNOWN"),
        "channel": transaction.get("channel", "UPI"),
        "risk_factors": transaction.get("risk_factors", []),
        "threshold": transaction.get("threshold", "LOW"),
        "reason": transaction.get("reason", "Low risk pattern"),
        "full_reason": transaction.get("full_reason", ""),
        "confidence": transaction.get("confidence", "LOW"),
        "ml_score": transaction.get("ml_score", 0),
        "rule_score": transaction.get("rule_score", 0),
        "ml_feature_importance": transaction.get("ml_feature_importance", {}),
        "account_status": execution_record.get("resulting_account_state", "ACTIVE"),
        "execution_record": execution_record,
        "policy_decision": policy_decision,
        "response_decision": policy_decision
    }
    await manager.broadcast(tx_event)


    # Broadcast transaction.action and automation WebSocket events
    response_decision = result.get("response_decision") or {}
    exec_status = execution_record.get("execution_status", "NOT_EXECUTED")
    is_operator_req = (exec_status == "REQUIRES_OPERATOR_ACTION")

    action_event = {
        "event": "transaction.action",
        "transaction_id": transaction.get("tx_id", ""),
        "tx_id": transaction.get("tx_id", ""),
        "risk_score": float(transaction.get("risk_score", 0.0)),
        "risk_level": policy_decision.get("risk_level", "LOW"),
        "action": policy_decision.get("action", "MONITOR"),
        "action_status": exec_status,
        "reason": policy_decision.get("reason", transaction.get("reason", "")),
        "automated": bool(execution_record.get("automation_mode") == "AUTOMATE_ON" and not is_operator_req),
        "mode": execution_record.get("automation_mode", "AUTOMATE_OFF"),
        "requires_human_approval": bool(exec_status == "REJECTED" or is_operator_req),
        "financial_action_status": "HUMAN AUTHORIZATION REQUIRED" if (exec_status == "REJECTED" or is_operator_req) else "NOT_APPLICABLE",
        "case_id": case.get("case_id") if case else transaction.get("case_id", ""),
        "investigation_run_id": response_decision.get("investigation_run_id", ""),
        "timestamp": execution_record.get("timestamp") or _now_iso(),
        "execution_record": execution_record,
        "policy_decision": policy_decision
    }
    await manager.broadcast(action_event)

    # Specific Phase 16 WebSocket event
    if exec_status == "SUCCESS":
        ws_event_name = "automation.action.executed"
    elif is_operator_req:
        ws_event_name = "automation.action.requires_operator"
    elif exec_status == "REJECTED" or exec_status == "NOT_EXECUTED":
        ws_event_name = "automation.action.blocked"
    else:
        ws_event_name = "automation.action.failed"

    automation_event = {
        "event": ws_event_name,
        "case_id": case.get("case_id") if case else transaction.get("case_id", ""),
        "transaction_id": transaction.get("tx_id", ""),
        "tx_id": transaction.get("tx_id", ""),
        "account_id": transaction.get("sender_account", "UNKNOWN"),
        "risk_score": float(transaction.get("risk_score", 0.0)),
        "risk_level": policy_decision.get("risk_level", "CRITICAL"),
        "action_code": policy_decision.get("action", "FREEZE"),
        "policy_rule_id": policy_decision.get("policy_rule_id", "POL-DEFAULT"),
        "policy_decision": policy_decision.get("decision", "EXECUTE"),
        "execution_status": exec_status,
        "reason": policy_decision.get("reason", ""),
        "execution_result": execution_record,
        "action_executed": exec_status == "SUCCESS",
        "timestamp": execution_record.get("timestamp") or _now_iso()
    }
    await manager.broadcast(automation_event)




    if case:
        case_id = case.get("case_id")
        if case_id:
            sync_env = os.getenv("SENTINEL_SYNC_INVESTIGATION")
            if sync_env is not None:
                is_sync = (sync_env == "1")
            else:
                is_sync = not (os.getenv("SENTINEL_MODE") == "production" or os.getenv("DATABASE_URL"))

            if is_sync:
                await investigation_orchestrator.run_investigation(case_id, repo=repo, store=data_store)
            else:
                asyncio.create_task(_run_background_investigation(case_id, data_store))
        case_event = {"event": "case_updated", **_case_payload(case)}
        await manager.broadcast(case_event)

    if isinstance(repo, PostgreSQLCaseRepository):
        await repo.session.commit()

    return result







@app.get("/cases")
async def get_cases(
    repo: AbstractCaseRepository = Depends(get_repository)
) -> list[dict[str, Any]]:
    case_list = await repo.get_cases()
    return [_case_payload(c) for c in case_list]


@app.get("/cases/{case_id}")
async def get_case_by_id(
    case_id: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    case = data_store.get("cases", {}).get(case_id)
    if not case:
        case_list = await repo.get_cases()
        case = next((c for c in case_list if c.get("case_id") == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return _case_payload(case)


@app.get("/cases/{case_id}/graph")
def get_case_graph(case_id: str, tx_id: Optional[str] = None) -> dict[str, Any]:
    from app.engines.graph_engine import build_investigation_graph
    return build_investigation_graph(case_id, data_store, focus_tx_id=tx_id)


@app.get("/transactions/{tx_id}/graph")
def get_transaction_graph(tx_id: str) -> dict[str, Any]:
    tx = data_store.get("transactions", {}).get(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction '{tx_id}' not found")
    case_id = tx.get("case_id") or f"CASE-{tx_id[:8]}"
    from app.engines.graph_engine import build_investigation_graph
    return build_investigation_graph(case_id, data_store, focus_tx_id=tx_id)



@app.post("/cases/{case_id}/investigate")
async def trigger_case_investigation(
    case_id: str,
    force_rerun: bool = False,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Triggers/re-runs the Phase 9 automated end-to-end investigation pipeline for a given case_id.
    Reuses existing active/completed run unless force_rerun=True.
    """
    record = await investigation_orchestrator.run_investigation(case_id, repo=repo, store=data_store, force_rerun=force_rerun)
    if isinstance(repo, PostgreSQLCaseRepository):
        await repo.session.commit()
    return record


@app.get("/cases/{case_id}/investigation-status")
async def get_investigation_status(
    case_id: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Returns current Phase 9 automated investigation status and stage execution metrics.
    """
    if case_id in investigation_orchestrator._active_investigations:
        return investigation_orchestrator._active_investigations[case_id]

    rpt = await repo.get_investigation_report(case_id, "DECISION_SUPPORT")
    if rpt and isinstance(rpt.get("report_data"), dict):
        return rpt["report_data"]

    raise HTTPException(status_code=404, detail=f"No investigation record found for case '{case_id}'")




@app.get("/cases/{case_id}/evidence")
def get_case_evidence(case_id: str) -> dict[str, Any]:
    """
    Returns structured, machine-readable evidence package for a given case.
    """
    return collect_evidence_for_case(case_id, data_store)


@app.get("/transactions/{tx_id}/evidence")
def get_transaction_evidence(tx_id: str) -> dict[str, Any]:
    """
    Returns structured, machine-readable evidence package for a given transaction.
    """
    return collect_evidence_for_transaction(tx_id, data_store)


@app.post("/evidence")
def get_evidence_post(payload: EvidenceRequest) -> dict[str, Any]:
    """
    Universal evidence collection endpoint supporting target_id, case_id, or tx_id.
    """
    target = payload.target_id or payload.case_id or payload.tx_id or ""
    return collect_evidence(target, data_store)


async def _build_investigation_read_model(case_id: str, repo: AbstractCaseRepository) -> dict[str, Any]:
    run = await repo.get_active_investigation_run(case_id) or await repo.get_latest_investigation_run(case_id)

    stage_types = ["EVIDENCE", "CONTEXTUAL", "REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"]

    stages_output = []
    completed_count = 0
    failed_count = 0
    skipped_count = 0
    degraded_reasons = []

    stage_states = run.get("stages", {}) if run else {}

    for stg in stage_types:
        stg_info = stage_states.get(stg, {})
        stg_status = stg_info.get("status", "PENDING")
        stg_start = stg_info.get("started_at")
        stg_comp = stg_info.get("completed_at")
        stg_err = stg_info.get("error")

        duration_ms = None
        if stg_start and stg_comp:
            try:
                dt_s = datetime.fromisoformat(stg_start.replace("Z", "+00:00"))
                dt_c = datetime.fromisoformat(stg_comp.replace("Z", "+00:00"))
                duration_ms = int((dt_c - dt_s).total_seconds() * 1000)
            except Exception:
                pass

        rpt = None
        rpt_id = None
        if stg_status == "COMPLETED":
            rpt_obj = await repo.get_investigation_report(case_id, stg)
            if rpt_obj:
                rpt_id = rpt_obj.get("report_id")
                rpt = rpt_obj.get("report_data")

        # Deterministic fallback for EVIDENCE collection stage if report is missing
        if stg == "EVIDENCE" and (not rpt or stg_status != "COMPLETED"):
            try:
                ev_fallback = collect_evidence_for_case(case_id, data_store)
                if ev_fallback and ev_fallback.get("evidence"):
                    rpt = ev_fallback
                    stg_status = "COMPLETED"
                    stg_comp = stg_comp or datetime.utcnow().isoformat() + "Z"
            except Exception:
                pass

        if stg_status == "COMPLETED":
            completed_count += 1
        elif stg_status == "FAILED":
            failed_count += 1
            if stg_err:
                degraded_reasons.append(f"{stg}_STAGE_FAILED: {stg_err}")
        elif stg_status == "SKIPPED":
            skipped_count += 1

        stages_output.append({
            "stage": stg,
            "status": stg_status,
            "started_at": stg_start,
            "completed_at": stg_comp,
            "duration_ms": duration_ms,
            "report_id": rpt_id,
            "output": rpt,
            "error": stg_err
        })

    ds_rpt_obj = await repo.get_investigation_report(case_id, "DECISION_SUPPORT")
    ds_output = ds_rpt_obj.get("report_data") if ds_rpt_obj else None

    run_status = run.get("status", "NONE") if run else "NONE"
    is_degraded = (run_status == "DEGRADED") or (failed_count > 0)

    sum_dict = run.get("summary", {}) if run else {}
    degraded_reasons = sum_dict.get("degraded_reasons") or degraded_reasons

    return {
        "case_id": case_id,
        "run_id": run.get("run_id") if run else None,
        "status": run_status,
        "started_at": run.get("started_at") if run else None,
        "completed_at": run.get("completed_at") if run else None,
        "current_stage": run.get("current_stage", "NONE") if run else "NONE",
        "stages": stages_output,
        "summary": {
            "completed_stages": completed_count,
            "failed_stages": failed_count,
            "skipped_stages": skipped_count,
            "degraded": is_degraded,
            "degraded_reasons": degraded_reasons,
            "review_priority": sum_dict.get("review_priority", "UNKNOWN"),
            "regulatory_severity": sum_dict.get("regulatory_severity", "UNKNOWN"),
            "recommended_action": sum_dict.get("recommended_action", "NO_RECOMMENDATION")
        },
        "decision_support": ds_output,
        "human_approval_boundary": {
            "autonomous_execution": False,
            "required_role": "COMPLIANCE_ANALYST"
        }
    }


@app.get("/cases/{case_id}/investigation")
async def get_case_investigation(
    case_id: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Returns Phase 10 read-oriented comprehensive investigation representation for a given case.
    """
    return await _build_investigation_read_model(case_id, repo)


@app.get("/cases/{case_id}/reports/{report_type}")
async def get_case_stage_report(
    case_id: str,
    report_type: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Retrieves historical, immutable persisted investigation report for a given stage.
    """
    valid_types = {"EVIDENCE", "CONTEXTUAL", "REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"}
    clean_type = report_type.upper()
    if clean_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid report_type '{report_type}'. Must be one of {valid_types}")

    rpt = await repo.get_investigation_report(case_id, clean_type)
    if not rpt or not rpt.get("report_data"):
        raise HTTPException(status_code=404, detail=f"Report '{clean_type}' not found or stage failed for case '{case_id}'")

    return rpt


@app.get("/cases/{case_id}/investigation-runs")
async def get_case_investigation_runs(
    case_id: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> list[dict[str, Any]]:
    """
    Returns all historical durable InvestigationRun records for a given case_id.
    """
    return await repo.get_investigation_runs_for_case(case_id)


@app.get("/cases/{case_id}/investigation-runs/{run_id}")
async def get_specific_investigation_run(
    case_id: str,
    run_id: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Returns specific historical InvestigationRun record by run_id.
    """
    run = await repo.get_investigation_run(run_id)
    if not run or run.get("case_id") != case_id:
        raise HTTPException(status_code=404, detail=f"Investigation run '{run_id}' not found for case '{case_id}'")
    return run



@app.get("/transactions/{tx_id}/investigation")
def get_transaction_investigation(tx_id: str) -> dict[str, Any]:
    """
    Returns Phase 2 Contextual Investigation Report for a given transaction.
    """
    return investigate_transaction(tx_id, data_store)



@app.post("/investigation")
def get_investigation_post(payload: EvidenceRequest) -> dict[str, Any]:
    """
    Universal investigation endpoint supporting target_id, case_id, or tx_id.
    """
    target = payload.target_id or payload.case_id or payload.tx_id or ""
    evidence_pkg = collect_evidence(target, data_store)
    return investigate_context(evidence_pkg)


@app.get("/cases/{case_id}/regulatory-assessment")
def get_case_regulatory_assessment(case_id: str) -> dict[str, Any]:
    """
    Returns Phase 3 Regulatory Risk Assessment Report for a given case.
    """
    return assess_case_regulatory_risk(case_id, data_store)


@app.get("/transactions/{tx_id}/regulatory-assessment")
def get_transaction_regulatory_assessment(tx_id: str) -> dict[str, Any]:
    """
    Returns Phase 3 Regulatory Risk Assessment Report for a given transaction.
    """
    return assess_transaction_regulatory_risk(tx_id, data_store)


@app.post("/regulatory-assessment")
def get_regulatory_assessment_post(payload: EvidenceRequest) -> dict[str, Any]:
    """
    Universal regulatory assessment endpoint supporting target_id, case_id, or tx_id.
    """
    target = payload.target_id or payload.case_id or payload.tx_id or ""
    evidence_pkg = collect_evidence(target, data_store)
    contextual_rpt = investigate_context(evidence_pkg)
    return assess_regulatory_risk(evidence_pkg, contextual_rpt)


@app.get("/cases/{case_id}/audit-explanation")
def get_case_audit_explanation(case_id: str) -> dict[str, Any]:
    """
    Returns Phase 4 Audit Explanation Report for a given case.
    """
    return generate_case_audit_explanation(case_id, data_store)


@app.get("/transactions/{tx_id}/audit-explanation")
def get_transaction_audit_explanation(tx_id: str) -> dict[str, Any]:
    """
    Returns Phase 4 Audit Explanation Report for a given transaction.
    """
    return generate_transaction_audit_explanation(tx_id, data_store)


@app.post("/audit-explanation")
def get_audit_explanation_post(payload: EvidenceRequest) -> dict[str, Any]:
    """
    Universal audit explanation endpoint supporting target_id, case_id, or tx_id.
    """
    target = payload.target_id or payload.case_id or payload.tx_id or ""
    evidence_pkg = collect_evidence(target, data_store)
    contextual_rpt = investigate_context(evidence_pkg)
    regulatory_rpt = assess_regulatory_risk(evidence_pkg, contextual_rpt)
    return generate_audit_explanation(evidence_pkg, contextual_rpt, regulatory_rpt)


@app.get("/cases/{case_id}/decision-support")
def get_case_decision_support(case_id: str) -> dict[str, Any]:
    """
    Returns Phase 5 Analyst Decision Support Report for a given case.
    """
    return generate_case_analyst_decision_support(case_id, data_store)


@app.get("/transactions/{tx_id}/decision-support")
def get_transaction_decision_support(tx_id: str) -> dict[str, Any]:
    """
    Returns Phase 5 Analyst Decision Support Report for a given transaction.
    """
    return generate_transaction_analyst_decision_support(tx_id, data_store)


@app.post("/decision-support")
def get_decision_support_post(payload: EvidenceRequest) -> dict[str, Any]:
    """
    Universal decision support endpoint supporting target_id, case_id, or tx_id.
    Validates scope matching if both case_id and tx_id are provided.
    """
    target = payload.target_id or payload.case_id or payload.tx_id or ""
    if payload.case_id and payload.tx_id:
        tx_obj = data_store.get("transactions", {}).get(payload.tx_id)
        if tx_obj and tx_obj.get("case_id") and tx_obj.get("case_id") != payload.case_id:
            return {
                "found": False,
                "status": "INVALID_INPUT",
                "target_id": target,
                "case_id": payload.case_id,
                "primary_tx_id": payload.tx_id,
                "generated_at": _now_iso(),
                "summary": {
                    "review_priority": "UNKNOWN",
                    "regulatory_severity": "UNKNOWN",
                    "assessment_heuristic_index": 0.0,
                    "recommended_step_count": 0,
                    "requires_human_approval": True
                },
                "analyst_executive_brief": f"Decision support failed: Mismatched case_id ({payload.case_id}) and primary_tx_id ({payload.tx_id}).",
                "review_priority": "UNKNOWN",
                "priority_rationale": "Case and transaction ID scope mismatch.",
                "recommended_review_steps": [],
                "disposition_options": [],
                "uncertainties": ["Input payload contains conflicting case_id and tx_id."],
                "data_gaps": ["Scope mismatch between case_id and tx_id."],
                "human_approval_boundary": {
                    "autonomous_execution": False,
                    "required_role": "COMPLIANCE_ANALYST"
                },
                "audit_trail": {
                    "source_stages": [],
                    "input_case_id": payload.case_id,
                    "input_transaction_id": payload.tx_id,
                    "generator": "analyst_decision_support_agent",
                    "generator_version": "phase5-v1",
                    "deterministic": True
                }
            }

    if payload.case_id:
        return generate_case_analyst_decision_support(payload.case_id, data_store)
    elif payload.tx_id:
        return generate_transaction_analyst_decision_support(payload.tx_id, data_store)
    else:
        evidence_pkg = collect_evidence(target, data_store)
        contextual_rpt = investigate_context(evidence_pkg)
        regulatory_rpt = assess_regulatory_risk(evidence_pkg, contextual_rpt)
        audit_exp = generate_audit_explanation(evidence_pkg, contextual_rpt, regulatory_rpt)
        return generate_analyst_decision_support(evidence_pkg, contextual_rpt, regulatory_rpt, audit_exp)


async def _ensure_pg_case_seeded(session: AsyncSession, case_dict: dict[str, Any]) -> None:
    if not case_dict or not isinstance(case_dict, dict):
        return
    case_id = case_dict.get("case_id")
    if not case_id:
        return
    from sqlalchemy import select
    from app.models.case import Case
    from app.models.account import Account
    from app.models.transaction import Transaction

    res = await session.execute(select(Case).filter(Case.case_id == case_id))
    case_obj = res.scalar_one_or_none()
    if case_obj:
        target_status = case_dict.get("status", "NEW")
        if case_obj.status != target_status:
            case_obj.status = target_status
            await session.flush()
        return

    now = datetime.now(timezone.utc)
    primary_tx_id = case_dict.get("primary_tx_id") or f"TX-SEED-{case_id}"
    acc1_id = case_dict.get("sender_account") or f"ACC-SND-{case_id}"
    acc2_id = case_dict.get("receiver_account") or f"ACC-RCV-{case_id}"

    for acc_id in [acc1_id, acc2_id]:
        acc_res = await session.execute(select(Account).filter(Account.account_id == acc_id))
        if not acc_res.scalar_one_or_none():
            session.add(Account(account_id=acc_id, created_at=now, updated_at=now))

    tx_res = await session.execute(select(Transaction).filter(Transaction.tx_id == primary_tx_id))
    if not tx_res.scalar_one_or_none():
        session.add(Transaction(
            tx_id=primary_tx_id,
            sender_account_id=acc1_id,
            receiver_account_id=acc2_id,
            amount=float(case_dict.get("total_fraud_amount", 1000.0)),
            channel="UPI",
            timestamp=now,
            raw_payload={},
            created_at=now
        ))

    session.add(Case(
        case_id=case_id,
        primary_tx_id=primary_tx_id,
        status=case_dict.get("status", "NEW"),
        risk_level=str(case_dict.get("risk_level", "LOW")),
        golden_window_minutes=int(case_dict.get("golden_window_minutes", 30)),
        total_fraud_amount=float(case_dict.get("total_fraud_amount", 0.0)),
        recoverable_amount=float(case_dict.get("recoverable_amount", 0.0)),
        created_at=now,
        updated_at=now
    ))
    await session.flush()



@app.post("/cases/{case_id}/disposition")
async def submit_case_disposition(
    case_id: str,
    payload: DispositionRequest,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Stateful Case Lifecycle Disposition Endpoint (Phase 7 Repository Adapter / Phase 8 Step 1 DI).
    """
    case_dict = None
    if isinstance(repo, PostgreSQLCaseRepository):
        case_dict = await repo.get_case_by_id(case_id)
    if not case_dict:
        case_dict = data_store.get("cases", {}).get(case_id)
        if case_dict and isinstance(repo, PostgreSQLCaseRepository):
            await _ensure_pg_case_seeded(repo.session, case_dict)

    if not case_dict:
        return {
            "ok": False,
            "status": "INVALID_INPUT",
            "error": f"Case '{case_id}' not found.",
            "acknowledged": False
        }

    if payload.case_id and payload.case_id != case_id:
        return {
            "ok": False,
            "status": "INVALID_INPUT",
            "error": f"Payload case_id '{payload.case_id}' does not match path case_id '{case_id}'.",
            "acknowledged": False
        }

    forbidden_codes = {"FREEZE", "BLOCK", "FILE_STR", "CLOSE_ACCOUNT", "REJECT_TRANSACTION"}
    if payload.action_code and payload.action_code.upper() in forbidden_codes:
        return {
            "ok": False,
            "status": "INVALID_INPUT",
            "error": f"Forbidden action code '{payload.action_code}'. Phase 7 does not execute autonomous enforcement actions.",
            "acknowledged": False
        }

    # Resolve Phase 5 decision support report
    ds_report = generate_case_analyst_decision_support(case_id, data_store)

    # Invoke repository-backed stateful disposition service directly (async)
    service = CaseLifecycleService(repo)
    res = await service.submit_case_disposition(
        case_id=case_id,
        action_code=payload.action_code,
        analyst_notes=payload.analyst_notes or "",
        decision_support_report=ds_report,
        analyst_id=payload.analyst_id or "ANALYST-001",
        analyst_role=payload.analyst_role or "COMPLIANCE_ANALYST",
        risk_acknowledged=payload.risk_acknowledged,
        idempotency_key=payload.idempotency_key
    )


    if res.get("ok"):
        c_ds = data_store.get("cases", {}).get(case_id)
        if c_ds and res.get("new_case_status"):
            c_ds["status"] = res["new_case_status"]
            if res.get("disposition"):
                c_ds.setdefault("actions_taken", []).insert(0, res["disposition"])

        if isinstance(repo, PostgreSQLCaseRepository):
            await repo.session.commit()

    return res


@app.get("/cases/{case_id}/history")
async def get_case_history_endpoint(
    case_id: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Returns complete chronological lifecycle and disposition audit history for a given case via repository.
    """
    case_dict = None
    if isinstance(repo, PostgreSQLCaseRepository):
        case_dict = await repo.get_case_by_id(case_id)
    if not case_dict:
        case_dict = data_store.get("cases", {}).get(case_id)
        if case_dict and isinstance(repo, PostgreSQLCaseRepository):
            await _ensure_pg_case_seeded(repo.session, case_dict)

    if not case_dict:
        return {
            "found": False,
            "status": "INSUFFICIENT_DATA",
            "error": f"Case '{case_id}' not found.",
            "case_id": case_id,
            "disposition_history": [],
            "audit_history": []
        }

    service = CaseLifecycleService(repo)
    hist = await service.get_case_history(case_id)

    dispositions = hist.get("disposition_history", [])
    audit_log = hist.get("audit_history", [])

    return {
        "found": True,
        "status": "SUCCESS",
        "case_id": case_id,
        "primary_tx_id": case_dict.get("primary_tx_id"),
        "current_case_status": case_dict.get("status", "NEW"),
        "disposition_count": len(dispositions),
        "audit_count": len(audit_log),
        "disposition_history": dispositions,
        "audit_history": audit_log
    }




def _sanitize_csv_field(val: Any) -> str:
    """Escapes leading formula injection characters for CSV security."""
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


ACTION_DISPLAY_MAP = {
    "FREEZE": "Freeze Account",
    "BLOCK": "Block Account",
    "REJECT_TRANSACTION": "Reject Transaction",
    "CLOSE_ACCOUNT": "Close Account",
    "FILE_STR": "File STR",
    "MONITOR": "Monitor",
    "ENHANCED_MONITORING": "Enhanced Monitoring",
    "ESCALATE_ANALYST_REVIEW": "Escalate Analyst Review",
    "MARK_FALSE_POSITIVE": "Mark False Positive",
    "FLAG": "Flag Case",
    "ALERT": "Trigger Alert"
}

def _fmt_label(val: Any) -> str:
    if not val:
        return ""
    v_str = str(val)
    if v_str.upper() in ACTION_DISPLAY_MAP:
        return ACTION_DISPLAY_MAP[v_str.upper()]
    return v_str.replace("_", " ").title()


@app.get("/export/sentinel_audit.csv")
async def export_csv(
    repo: AbstractCaseRepository = Depends(get_repository)
):
    """
    Generates and streams a comprehensive CSV audit log from authoritative repository store.
    Exports complete action audit history (automatic & manual) with 16 canonical fields.
    Browser handles this as a native file download.
    """
    from fastapi.responses import StreamingResponse
    import io, csv
    from datetime import datetime, timezone as _tz

    output = io.StringIO()
    # UTF-8 BOM so Excel opens correctly
    output.write('\ufeff')

    writer = csv.writer(output, lineterminator='\r\n')

    # ── Section 1: Complete Action Audit Log ────────────────────────────────────
    writer.writerow(['SENTINEL COMPLETE ACTION AUDIT LOG'])
    writer.writerow([
        'Timestamp', 'Audit ID', 'Case ID', 'Transaction ID',
        'Account ID', 'Risk Score', 'Risk Level', 'Action',
        'Execution Mode', 'Actor', 'Action Status',
        'Previous State', 'Resulting State', 'Reason',
        'Policy Rule ID', 'Operator / Analyst ID'
    ])

    # Fetch all authoritative audit events across all data sources
    audit_events = await repo.get_all_audit_events()
    ds_audits = data_store.get("audit_events", [])
    exec_actions = list(data_store.get("executed_actions", {}).values())

    combined_map = {}
    
    # Process repo audit_events
    for a in audit_events:
        aid = a.get("audit_id") or a.get("execution_id") or f"AUD-{uuid4().hex[:8]}"
        combined_map[aid] = a

    # Process in-memory audit_events
    for a in ds_audits:
        aid = a.get("audit_id") or a.get("execution_id") or f"AUD-{uuid4().hex[:8]}"
        if aid not in combined_map:
            combined_map[aid] = a

    # Process executed_actions dictionary
    for ea in exec_actions:
        aid = ea.get("execution_id") or ea.get("idempotency_key")
        if aid and aid not in combined_map:
            combined_map[aid] = {
                "audit_id": ea.get("execution_id", f"EXEC-{uuid4().hex[:8]}"),
                "timestamp": ea.get("timestamp", _now_iso()),
                "case_id": ea.get("case_id", ""),
                "primary_tx_id": ea.get("transaction_id", ""),
                "target_account": ea.get("account_id", ""),
                "risk_score": ea.get("risk_score", 0),
                "risk_level": ea.get("risk_level", "LOW"),
                "action_code": ea.get("action_code", "MONITOR"),
                "actor_type": ea.get("actor_type", "AUTOMATION_ENGINE"),
                "analyst_id": ea.get("actor_id", "SENTINEL_SIMULATED_EXECUTOR"),
                "execution_status": ea.get("execution_status", "SUCCESS"),
                "previous_case_status": ea.get("previous_account_state", "ACTIVE"),
                "new_case_status": ea.get("resulting_account_state", "ACTIONED"),
                "reason": ea.get("reason", "Autonomous policy decision"),
                "policy_rule_id": ea.get("policy_rule_id", "POL-DEFAULT")
            }

    # Fetch case disposition history
    cases = await repo.get_cases()
    for c in cases:
        c_hist = await repo.get_case_history(c.get("case_id", ""))
        c_actions = c_hist.get("disposition_history", []) if isinstance(c_hist, dict) else []
        for ca in c_actions:
            aid = ca.get("disposition_id") or ca.get("action_id")
            if aid and aid not in combined_map:
                combined_map[aid] = {
                    "audit_id": aid,
                    "timestamp": ca.get("disposition_timestamp") or ca.get("timestamp", _now_iso()),
                    "case_id": ca.get("case_id", c.get("case_id", "")),
                    "primary_tx_id": c.get("primary_tx_id", ""),
                    "target_account": ca.get("target", "GLOBAL"),
                    "risk_score": c.get("risk_score", 0),
                    "risk_level": c.get("risk_level", "LOW"),
                    "action_code": ca.get("action_code") or ca.get("action_type", "MONITOR"),
                    "actor_type": ca.get("actor_type", "HUMAN_OPERATOR"),
                    "analyst_id": ca.get("analyst_id", "OPERATOR_ADMIN"),
                    "execution_status": ca.get("status", "SUCCESS"),
                    "previous_case_status": "ACTIVE",
                    "new_case_status": ca.get("new_case_status", "ACTIONED"),
                    "reason": ca.get("analyst_notes") or ca.get("reason", "Analyst disposition action"),
                    "policy_rule_id": "POL-OPERATOR-DISPOSITION"
                }

    tx_store = data_store.get("transactions", {})

    for aid, a in combined_map.items():
        # Traceability chain fallback
        tc = a.get("traceability_chain") or a.get("decision_support_summary") or {}
        
        tx_id = a.get("primary_tx_id") or a.get("transaction_id") or tc.get("transaction_id") or ""
        tx_obj = tx_store.get(tx_id, {})

        score = float(a.get("risk_score") or tc.get("risk_score") or tx_obj.get("risk_score", 0))
        r_level_raw = a.get("risk_level") or tc.get("risk_level") or tx_obj.get("risk_level", "")
        if not r_level_raw:
            r_level_raw = "HIGH_RISK" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"
        risk_level_disp = _fmt_label(r_level_raw)

        action_code = a.get("action_code") or a.get("action_type") or tc.get("action_code") or "MONITOR"
        action_disp = _fmt_label(action_code)

        actor_type_raw = a.get("actor_type") or tc.get("actor_type") or a.get("analyst_role") or ""
        is_manual = actor_type_raw in ("HUMAN_OPERATOR", "OPERATOR", "Human Operator")
        exec_mode = "Manual" if is_manual else "Automatic"
        actor_disp = "Human Operator" if is_manual else "Automation Engine"

        exec_stat_raw = a.get("execution_status") or a.get("status") or tc.get("execution_status") or "SUCCESS"
        if exec_stat_raw in ("SUCCESS", "EXECUTED", "ACK"):
            status_disp = "Executed"
        elif exec_stat_raw in ("REJECTED", "POLICY_BLOCKED"):
            status_disp = "Blocked"
        elif exec_stat_raw == "FAILED":
            status_disp = "Failed"
        elif exec_stat_raw == "REQUIRES_OPERATOR_ACTION":
            status_disp = "Requires Operator Action"
        else:
            status_disp = _fmt_label(exec_stat_raw)

        prev_state = _fmt_label(a.get("previous_case_status") or tc.get("previous_account_state") or "Active")
        new_state = _fmt_label(a.get("new_case_status") or tc.get("resulting_account_state") or "Actioned")

        reason = a.get("reason") or tc.get("reason") or a.get("analyst_notes") or "Autonomous policy execution"
        rule_id = a.get("policy_rule_id") or tc.get("policy_rule_id") or "POL-DEFAULT"
        operator_id = a.get("analyst_id") or tc.get("actor_id") or a.get("operator_id") or ("OPERATOR_ADMIN" if is_manual else "SENTINEL_SIMULATED_EXECUTOR")

        writer.writerow([
            _sanitize_csv_field(a.get("timestamp") or tc.get("timestamp") or _now_iso()),
            _sanitize_csv_field(aid),
            _sanitize_csv_field(a.get("case_id") or tc.get("case_id") or ""),
            _sanitize_csv_field(tx_id),
            _sanitize_csv_field(a.get("target_account") or a.get("account_id") or tc.get("account_id") or "ACC-GLOBAL"),
            score,
            risk_level_disp,
            action_disp,
            exec_mode,
            actor_disp,
            status_disp,
            prev_state,
            new_state,
            _sanitize_csv_field(reason),
            _sanitize_csv_field(rule_id),
            _sanitize_csv_field(operator_id)
        ])

    # ── Section 2: Transaction Feed Audit ──────────────────────────────────────
    writer.writerow([])
    writer.writerow(['SENTINEL TRANSACTION FEED AUDIT'])
    writer.writerow([
        'Tx ID', 'Timestamp', 'Channel',
        'Sender Account', 'Receiver Account',
        'Amount (INR)', 'Risk Score', 'Risk Level', 'Case ID'
    ])

    tx_list = await repo.get_all_transactions()
    for tx in tx_list:
        score = float(tx.get("risk_score", 0))
        level = "High Risk" if score >= 70 else "Medium Risk" if score >= 40 else "Low Risk"
        writer.writerow([
            _sanitize_csv_field(tx.get("tx_id", "")),
            _sanitize_csv_field(tx.get("timestamp", "")),
            _sanitize_csv_field(tx.get("channel", "")),
            _sanitize_csv_field(tx.get("sender_account") or tx.get("sender_account_id") or ""),
            _sanitize_csv_field(tx.get("receiver_account") or tx.get("receiver_account_id") or ""),
            tx.get("amount", 0.0),
            score,
            level,
            _sanitize_csv_field(tx.get("case_id", ""))
        ])

    output.seek(0)
    now = datetime.now(_tz.utc)
    filename = f"SENTINEL_Audit_Log_{now.strftime('%Y-%m-%d_%H-%M')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



def _record_action(case_id: str, action_type: str, target_id: str, status: str, reason: str | None = None) -> dict[str, Any]:
    case = data_store.get("cases", {}).get(case_id)
    if not case:
        return {}
    entry = {
        "action_id": f"ACT-{uuid4().hex[:10].upper()}",
        "case_id": case_id,
        "action_type": action_type,
        "target_id": target_id,
        "target": target_id,
        "status": "ACK" if status == "SUCCESS" else "NACK",
        "timestamp": _now_iso(),
        "reason": reason or "Operator decision",
        "latency": 0,
    }
    case.setdefault("actions_taken", []).insert(0, entry)
    
    # Status Mapping based on actions
    if entry["status"] == "ACK":
        if action_type in ["FREEZE", "FLAG", "ALERT"]:
            case["status"] = "ACTIONED"
        elif action_type == "MONITOR":
            case["status"] = "MONITORING"
        elif action_type == "CLOSE":
            case["status"] = "CLOSED"
        elif action_type == "CLOSE_FP":
            case["status"] = "CLOSED_FP"
            
    return entry


async def _handle_action(action_name: str, payload: ActionRequest, repo=None) -> dict[str, Any]:
    tx_id = payload.target_id or payload.account_id or "GLOBAL"
    case_id = payload.case_id or "CASE-SYSTEM"

    action_code_map = {
        "freeze": "FREEZE",
        "block": "BLOCK",
        "reject": "REJECT_TRANSACTION",
        "file_str": "FILE_STR",
        "close_account": "CLOSE_ACCOUNT",
        "monitor": "MONITOR",
        "enhanced_monitoring": "ENHANCED_MONITORING",
        "flag": "ESCALATE_ANALYST_REVIEW",
        "alert": "ESCALATE_ANALYST_REVIEW",
        "close": "CLOSE",
        "close_fp": "MARK_FALSE_POSITIVE",
        "escalate": "ESCALATE_ANALYST_REVIEW"
    }
    action_code = action_code_map.get(action_name.lower(), action_name.upper())

    tx = data_store.get("transactions", {}).get(tx_id)
    if not tx and case_id:
        tx = next((t for t in data_store.get("transactions", {}).values() if t.get("case_id") == case_id), None)
    if not tx:
        tx = {
            "tx_id": tx_id,
            "case_id": case_id,
            "sender_account": payload.account_id or "ACC-UNKNOWN",
            "receiver_account": "ACC-UNKNOWN",
            "amount": 1000.0,
            "risk_score": 50
        }

    case_obj = data_store.get("cases", {}).get(case_id)

    from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
    pol = evaluate_autonomous_policy(tx, case_obj, automate_mode=True)
    pol["decision"] = "EXECUTE"
    pol["action"] = action_code

    from app.services.simulated_action_executor import execute_simulated_action
    exec_rec = await execute_simulated_action(
        case_id=case_id,
        tx_id=tx.get("tx_id", tx_id),
        action_code=action_code,
        policy_decision=pol,
        repo=repo,
        actor_type="HUMAN_OPERATOR",
        actor_id=payload.operator_id or "HUMAN_OPERATOR"
    )

    await manager.broadcast({
        "event": "automation.action.executed",
        "action": action_code,
        "action_code": action_code,
        "transaction_id": tx.get("tx_id", tx_id),
        "tx_id": tx.get("tx_id", tx_id),
        "case_id": case_id,
        "execution_result": exec_rec,
        "policy_decision": pol,
        "action_executed": True,
        "actor_type": "HUMAN_OPERATOR",
        "actor_id": payload.operator_id or "HUMAN_OPERATOR",
        "timestamp": exec_rec.get("timestamp") or _now_iso()
    })

    await manager.broadcast({
        "event": "transaction.action",
        "transaction_id": tx.get("tx_id", tx_id),
        "tx_id": tx.get("tx_id", tx_id),
        "risk_score": tx.get("risk_score", 50),
        "risk_level": pol.get("risk_level", "MEDIUM"),
        "action": action_code,
        "action_status": exec_rec.get("execution_status", "SUCCESS"),
        "reason": payload.reason or pol.get("reason", "Action executed by human operator"),
        "automated": False,
        "actor_type": "HUMAN_OPERATOR",
        "case_id": case_id,
        "timestamp": exec_rec.get("timestamp") or _now_iso(),
        "execution_record": exec_rec,
        "policy_decision": pol
    })

    if case_obj and exec_rec.get("execution_status") == "SUCCESS":
        act_entry = {
            "action_id": f"ACT-{uuid4().hex[:10].upper()}",
            "case_id": case_id,
            "action_type": action_code,
            "action": action_code,
            "target_id": payload.account_id or payload.target_id or "GLOBAL",
            "status": "SUCCESS",
            "timestamp": exec_rec.get("timestamp") or _now_iso(),
            "reason": payload.reason or "Operator executed action"
        }
        case_obj.setdefault("actions_taken", []).insert(0, act_entry)
        if action_code in ["CLOSE", "MARK_FALSE_POSITIVE", "CLOSE_ACCOUNT"]:
            case_obj["status"] = "CLOSED" if action_code != "MARK_FALSE_POSITIVE" else "CLOSED_FP"
        elif action_code in ["FREEZE", "BLOCK", "FILE_STR", "FLAG", "ALERT", "MONITOR", "ENHANCED_MONITORING"]:
            case_obj["status"] = "ACTIONED"

    if case_obj:
        await manager.broadcast({"event": "case_updated", **_case_payload(case_obj)})

    return {
        "ok": exec_rec.get("execution_status") == "SUCCESS",
        "event": "action_taken",
        "case_id": case_id,
        "action": action_code,
        "target_id": payload.account_id or payload.target_id or "GLOBAL",
        "status": "ACK" if exec_rec.get("execution_status") == "SUCCESS" else "NACK",
        "execution_record": exec_rec
    }


class FreezeRequestPayload(BaseModel):
    operator_id: Optional[str] = "OPERATOR_ADMIN"
    reason: Optional[str] = "Operator initiated account freeze"


@app.post("/cases/{case_id}/transactions/{transaction_id}/freeze")
@app.post("/transactions/{transaction_id}/freeze")
async def execute_operator_freeze(
    transaction_id: str,
    case_id: Optional[str] = None,
    payload: Optional[FreezeRequestPayload] = None,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    tx = None
    if isinstance(repo, PostgreSQLCaseRepository):
        tx = await repo.get_transaction_by_id(transaction_id)
    if not tx:
        tx = data_store.get("transactions", {}).get(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found.")

    eff_case_id = case_id or tx.get("case_id") or "CASE-SYSTEM"
    case_obj = None
    if isinstance(repo, PostgreSQLCaseRepository):
        case_obj = await repo.get_case_by_id(eff_case_id)
    if not case_obj:
        case_obj = data_store.get("cases", {}).get(eff_case_id)

    closed_statuses = {"CLOSED_CONFIRMED_FRAUD", "CLOSED_FALSE_POSITIVE"}
    if case_obj and case_obj.get("status") in closed_statuses:
        raise HTTPException(status_code=400, detail=f"Case '{eff_case_id}' is closed and invalid for FREEZE.")

    from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
    pol = evaluate_autonomous_policy(tx, case_obj, automate_mode=True)

    req_act = tx.get("requested_action") or tx.get("action")
    score = float(tx.get("risk_score", 0.0))
    if pol.get("action") != "FREEZE" and req_act != "FREEZE" and score < 70:
        raise HTTPException(status_code=403, detail="Arbitrary FREEZE request rejected: policy engine does not authorize FREEZE for this transaction.")

    op_id = (payload.operator_id if payload else None) or "OPERATOR_ADMIN"
    from app.services.simulated_action_executor import execute_simulated_action
    exec_rec = await execute_simulated_action(
        case_id=eff_case_id,
        tx_id=transaction_id,
        action_code="FREEZE",
        policy_decision=pol,
        repo=repo,
        actor_type="HUMAN_OPERATOR",
        actor_id=op_id
    )

    if isinstance(repo, PostgreSQLCaseRepository):
        await repo.session.commit()

    await manager.broadcast({
        "event": "automation.action.executed",
        "action": "FREEZE",
        "action_code": "FREEZE",
        "transaction_id": transaction_id,
        "tx_id": transaction_id,
        "case_id": eff_case_id,
        "execution_result": exec_rec,
        "policy_decision": pol,
        "action_executed": True,
        "actor_type": "HUMAN_OPERATOR",
        "actor_id": op_id,
        "timestamp": exec_rec.get("timestamp") or _now_iso()
    })

    await manager.broadcast({
        "event": "transaction.action",
        "transaction_id": transaction_id,
        "tx_id": transaction_id,
        "risk_score": score,
        "risk_level": pol.get("risk_level", "CRITICAL"),
        "action": "FREEZE",
        "action_status": "SUCCESS",
        "reason": pol.get("reason", "Operator executed account freeze"),
        "automated": False,
        "actor_type": "HUMAN_OPERATOR",
        "actor_id": op_id,
        "case_id": eff_case_id,
        "timestamp": exec_rec.get("timestamp") or _now_iso(),
        "execution_record": exec_rec,
        "policy_decision": pol
    })

    if case_obj and exec_rec.get("execution_status") == "SUCCESS":
        act_entry = {
            "action_id": f"ACT-{uuid4().hex[:10].upper()}",
            "case_id": eff_case_id,
            "action_type": "FREEZE",
            "action": "FREEZE",
            "target_id": transaction_id,
            "status": "SUCCESS",
            "timestamp": exec_rec.get("timestamp") or _now_iso(),
            "reason": (payload.reason if payload else None) or "Operator executed account freeze"
        }
        case_obj.setdefault("actions_taken", []).insert(0, act_entry)
        case_obj["status"] = "ACTIONED"
        await manager.broadcast({"event": "case_updated", **_case_payload(case_obj)})

    return exec_rec


@app.post("/action/freeze")
async def freeze_action(
    payload: ActionRequest,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    tx_id = payload.target_id or getattr(payload, 'tx_id', None)
    case_id = payload.case_id

    if not tx_id and case_id:
        if isinstance(repo, PostgreSQLCaseRepository):
            case_obj = await repo.get_case_by_id(case_id)
        else:
            case_obj = data_store.get("cases", {}).get(case_id)
        
        if case_obj and case_obj.get("primary_tx_id"):
            tx_id = case_obj.get("primary_tx_id")
        else:
            for t_id, t_obj in data_store.get("transactions", {}).items():
                if t_obj.get("case_id") == case_id:
                    tx_id = t_id
                    break

    if not tx_id:
        # Fallback to first available transaction or default
        all_txs = list(data_store.get("transactions", {}).keys())
        tx_id = all_txs[0] if all_txs else "TX-27678ED4"

    res = await execute_operator_freeze(
        transaction_id=tx_id,
        case_id=case_id,
        payload=FreezeRequestPayload(operator_id=payload.operator_id, reason=payload.reason),
        repo=repo
    )
    if isinstance(res, dict):
        res["action_status"] = res.get("execution_status", "SUCCESS")
        res["status"] = res.get("resulting_account_state", "FROZEN")
        res["action"] = "FREEZE"
    return res


@app.post("/action/flag")
@app.post("/action/escalate")
async def flag_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("flag", payload)


@app.post("/action/alert")
async def alert_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("alert", payload)


@app.post("/action/monitor")
async def monitor_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("monitor", payload)


@app.post("/action/enhanced_monitoring")
async def enhanced_monitoring_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("enhanced_monitoring", payload)


@app.post("/action/block")
async def block_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("block", payload)


@app.post("/action/reject")
async def reject_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("reject", payload)


@app.post("/action/file_str")
async def file_str_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("file_str", payload)


@app.post("/action/close_account")
async def close_account_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("close_account", payload)


@app.post("/action/close")
async def close_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("close", payload)


@app.post("/action/close_fp")
async def close_fp_action(payload: ActionRequest) -> dict[str, Any]:
    return await _handle_action("close_fp", payload)



class AutomationModeRequest(BaseModel):
    enabled: bool
    operator_id: Optional[str] = "OPERATOR_ADMIN"


@app.get("/automation-mode")
async def get_automation_mode() -> dict[str, Any]:
    return {
        "automate_mode": data_store.get("automation_mode", False),
        "updated_at": data_store.get("automation_mode_updated_at"),
        "updated_by": data_store.get("automation_mode_updated_by", "SYSTEM")
    }


def compute_case_investigation_confidence(
    evidence_package: Optional[dict] = None,
    contextual_report: Optional[dict] = None,
    regulatory_report: Optional[dict] = None,
    audit_report: Optional[dict] = None,
    analyst_report: Optional[dict] = None
) -> dict[str, Any]:
    """
    Deterministically computes Investigation Confidence from actual multi-agent
    investigation outputs in SENTINEL.
    
    Formula:
      Score = clamp(round(0.35 * completeness + 0.40 * agreement + 0.25 * diversity - 1.0 * contradictions, 1), 0.0, 100.0)
    """
    # 1. Evidence Completeness (35% Weight)
    # Evaluates presence across the 5 core empirical evidence dimensions from Phase 1
    completeness = 0.0
    ev_list = []
    if evidence_package and isinstance(evidence_package, dict):
        ev_list = evidence_package.get("evidence", [])
        if not isinstance(ev_list, list):
            ev_list = []

    if ev_list:
        has_tx = any(e.get("type") == "transaction" for e in ev_list if isinstance(e, dict))
        has_baseline = any(
            e.get("type") == "historical_behavior" and "Baseline" in str(e.get("category", ""))
            for e in ev_list if isinstance(e, dict)
        )
        has_flow = any(
            (e.get("type") in ("historical_behavior", "related_activity"))
            and any(k in str(e.get("category", "")) for k in ("Counterparty", "Flow", "Chain"))
            for e in ev_list if isinstance(e, dict)
        )
        has_graph = any(
            e.get("type") == "graph_network" or "Graph" in str(e.get("category", ""))
            for e in ev_list if isinstance(e, dict)
        )
        has_fin = any(
            e.get("type") == "financial" or any(k in str(e.get("category", "")) for k in ("Financial", "Recovery"))
            for e in ev_list if isinstance(e, dict)
        )
        present_dims = sum([1 if x else 0 for x in (has_tx, has_baseline, has_flow, has_graph, has_fin)])
        completeness = round((present_dims / 5.0) * 100.0, 1)

    # 2. Agent Agreement (40% Weight)
    # Evaluates severity consensus across the evaluating agents (Contextual, Regulatory, Decision Support)
    sev_map = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}
    active_sevs = []

    if contextual_report and isinstance(contextual_report, dict):
        ctx_s = contextual_report.get("summary", {}).get("contextual_severity")
        if ctx_s in sev_map:
            active_sevs.append(("contextual", sev_map[ctx_s]))

    if regulatory_report and isinstance(regulatory_report, dict):
        reg_s = regulatory_report.get("summary", {}).get("regulatory_severity")
        if reg_s in sev_map:
            active_sevs.append(("regulatory", sev_map[reg_s]))

    if analyst_report and isinstance(analyst_report, dict):
        dec_s = analyst_report.get("summary", {}).get("regulatory_severity")
        if dec_s in sev_map:
            active_sevs.append(("decision_support", sev_map[dec_s]))

    if len(active_sevs) >= 2:
        pair_diffs = []
        for i in range(len(active_sevs)):
            for j in range(i + 1, len(active_sevs)):
                diff = abs(active_sevs[i][1] - active_sevs[j][1])
                pair_diffs.append(max(0.0, 100.0 - diff))
        agreement = round(sum(pair_diffs) / len(pair_diffs), 1)
    elif len(active_sevs) == 1:
        agreement = 75.0  # Single evaluated agent baseline
    else:
        agreement = 0.0

    # 3. Source Diversity (25% Weight)
    # Evaluates number of independent evidence sources supporting the investigation
    sources = set()
    if ev_list:
        for e in ev_list:
            if isinstance(e, dict) and e.get("source"):
                sources.add(str(e.get("source")).strip())

    if sources:
        diversity = round(min(100.0, (len(sources) / 5.0) * 100.0), 1)
    else:
        diversity = 0.0

    # 4. Contradictions (-1.0% penalty per contradiction)
    # Detects polar conflicts (e.g. CRITICAL/HIGH vs LOW)
    contradictions = 0
    if len(active_sevs) >= 2:
        for i in range(len(active_sevs)):
            for j in range(i + 1, len(active_sevs)):
                val_i = active_sevs[i][1]
                val_j = active_sevs[j][1]
                if (val_i >= 75 and val_j <= 25) or (val_j >= 75 and val_i <= 25):
                    contradictions += 1

    # Final Confidence Score & Label
    raw_score = (0.35 * completeness) + (0.40 * agreement) + (0.25 * diversity) - (1.0 * contradictions)
    score = round(min(100.0, max(0.0, raw_score)), 1)

    if score >= 85.0:
        label = "HIGH CONFIDENCE"
    elif score >= 60.0:
        label = "MEDIUM CONFIDENCE"
    elif score > 0.0:
        label = "LOW CONFIDENCE"
    else:
        label = "LOW CONFIDENCE"

    return {
        "evidence_completeness": completeness,
        "agent_agreement": agreement,
        "source_diversity": diversity,
        "contradiction_count": contradictions,
        "score": score,
        "label": label
    }


@app.get("/analytics/overview")
async def get_analytics_overview(
    timeframe: str = Query(default="30d", pattern="^(24h|7d|30d|12m)$"),
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:

    """
    Returns comprehensive AML Intelligence & Risk Analytics Telemetry
    aggregated across live data_store and persisted repository metrics.
    """
    tx_list = list(data_store.get("transactions", {}).values())
    if not tx_list and isinstance(repo, AbstractCaseRepository):
        try:
            tx_list = await repo.get_all_transactions()
        except Exception:
            tx_list = []

    cases_list = list(data_store.get("cases", {}).values())
    if not cases_list and isinstance(repo, AbstractCaseRepository):
        try:
            cases_list = await repo.get_cases()
        except Exception:
            cases_list = []

    # Apply timeframe filter if transactions have timestamps
    if tx_list and timeframe:
        from datetime import timedelta
        now_utc = datetime.now(timezone.utc)
        tf_delta = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "12m": timedelta(days=365)
        }.get(timeframe)

        if tf_delta:
            cutoff = now_utc - tf_delta
            def parse_tx_time(tx):
                raw = tx.get("timestamp")
                if not raw:
                    return None
                try:
                    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except Exception:
                    return None

            timed_txs = [t for t in tx_list if parse_tx_time(t) is not None]
            if timed_txs:
                in_range = [t for t in timed_txs if parse_tx_time(t) >= cutoff]
                if in_range:
                    tx_list = in_range

    total_tx = len(tx_list)
    risk_alerts = [t for t in tx_list if float(t.get("risk_score", 0)) >= 40]
    total_alerts = len(risk_alerts)

    avg_score = round(sum(float(t.get("risk_score", 0)) for t in tx_list) / max(total_tx, 1), 1) if total_tx else 0.0

    resolved_cases = [c for c in cases_list if c.get("status") in ("CLOSED", "CLOSED_CONFIRMED_FRAUD", "CLOSED_FALSE_POSITIVE", "ACTIONED")]
    total_resolved = len(resolved_cases)

    # 1. Risk Trend Time Series
    sorted_txs = sorted(tx_list, key=lambda x: str(x.get("timestamp", "")))
    risk_trend = []
    chunk_size = max(1, len(sorted_txs) // 10) if sorted_txs else 1
    for i in range(0, max(len(sorted_txs), 1), chunk_size):
        chunk = sorted_txs[i:i+chunk_size]
        if not chunk:
            continue
        scores = [float(t.get("risk_score", 0)) for t in chunk]
        high_cnt = sum(1 for s in scores if 70 <= s < 85)
        crit_cnt = sum(1 for s in scores if s >= 85)
        last_t = chunk[-1]
        ts_label = str(last_t.get("timestamp", ""))[11:16] or f"T-{i}"
        risk_trend.append({
            "timestamp": ts_label,
            "avg_score": round(sum(scores) / len(scores), 1),
            "high_risk": high_cnt,
            "critical_risk": crit_cnt
        })

    if not risk_trend:
        risk_trend = []

    # 2. Alerts by Risk Level (Authenticated Forensic Grouping)
    crit_txs = [t for t in tx_list if float(t.get("risk_score", 0)) >= 85]
    high_txs = [t for t in tx_list if 70 <= float(t.get("risk_score", 0)) < 85]
    med_txs = [t for t in tx_list if 40 <= float(t.get("risk_score", 0)) < 70]
    low_txs = [t for t in tx_list if float(t.get("risk_score", 0)) < 40]

    def _build_tier_summary(txs, name, color, threshold_desc, guidance):
        cnt = len(txs)
        pct = round((cnt / max(total_tx, 1)) * 100, 1)
        vol = round(sum(float(t.get("amount", 0)) for t in txs), 2)
        scores = [float(t.get("risk_score", 0)) for t in txs]
        avg_s = round(sum(scores) / len(scores), 1) if scores else 0.0
        return {
            "name": name,
            "value": cnt,
            "color": color,
            "percentage": pct,
            "volume": vol,
            "avg_score": avg_s,
            "threshold": threshold_desc,
            "guidance": guidance
        }

    alerts_by_risk_level = [
        _build_tier_summary(crit_txs, "CRITICAL", "#ef4444", "Score ≥ 85", "Immediate automated block or hard freeze"),
        _build_tier_summary(high_txs, "HIGH", "#f59e0b", "Score 70–84", "Enhanced monitoring and analyst escalation"),
        _build_tier_summary(med_txs, "MEDIUM", "#38bdf8", "Score 40–69", "Automated telemetry and rule screening"),
        _build_tier_summary(low_txs, "LOW", "#10b981", "Score < 40", "Normal baseline transaction routing")
    ]

    # 3. Investigation Performance
    cases_opened = len(cases_list)
    cases_escalated = sum(1 for c in cases_list if c.get("status") in ("HIGH_RISK", "ESCALATED"))
    resolution_rate = round((total_resolved / max(cases_opened, 1)) * 100, 1)

    investigation_performance = {
        "cases_opened": cases_opened,
        "cases_investigated": cases_opened,
        "cases_resolved": total_resolved,
        "cases_escalated": cases_escalated,
        "resolution_rate": resolution_rate
    }

    # 3b. Investigation Confidence Telemetry (Tier 04 Investigation Performance)
    tf_tx_ids = {t.get("tx_id") for t in tx_list}
    active_cases = [
        c for c in cases_list
        if c.get("primary_tx_id") in tf_tx_ids or any(tx.get("tx_id") in tf_tx_ids for tx in c.get("transactions", []))
    ] if tx_list else cases_list
    if not active_cases and cases_list:
        active_cases = cases_list

    inv_runs_store = data_store.get("investigation_runs", {})
    reports_store = data_store.get("investigation_reports", {})

    cases_evaluated = 0
    total_ev_comp = 0.0
    total_agent_agree = 0.0
    total_source_div = 0.0
    total_contradictions = 0

    for case in active_cases:
        cid = case.get("case_id")
        if not cid:
            continue

        run = next((r for r in inv_runs_store.values() if r.get("case_id") == cid), None)
        stages = run.get("stages", {}) if run else {}

        ev_pkg = case.get("evidence_package") or stages.get("EVIDENCE", {}).get("output") or reports_store.get(f"{cid}::EVIDENCE", {}).get("report_data")
        ctx_rpt = case.get("contextual_investigation") or case.get("contextual_report") or stages.get("CONTEXTUAL", {}).get("output") or reports_store.get(f"{cid}::CONTEXTUAL", {}).get("report_data")
        reg_rpt = case.get("regulatory_assessment") or case.get("regulatory_report") or stages.get("REGULATORY", {}).get("output") or reports_store.get(f"{cid}::REGULATORY", {}).get("report_data")
        aud_rpt = case.get("audit_explanation") or case.get("audit_report") or stages.get("AUDIT", {}).get("output") or stages.get("AUDIT_EXPLANATION", {}).get("output") or reports_store.get(f"{cid}::AUDIT", {}).get("report_data")
        dec_rpt = case.get("analyst_report") or case.get("decision_support") or stages.get("DECISION", {}).get("output") or stages.get("DECISION_SUPPORT", {}).get("output") or reports_store.get(f"{cid}::DECISION", {}).get("report_data")

        # Only evaluate cases that have actual investigation run/stage data
        has_any_output = any(x is not None for x in (ev_pkg, ctx_rpt, reg_rpt, aud_rpt, dec_rpt))
        if not has_any_output and not run:
            continue

        case_conf = compute_case_investigation_confidence(
            evidence_package=ev_pkg,
            contextual_report=ctx_rpt,
            regulatory_report=reg_rpt,
            audit_report=aud_rpt,
            analyst_report=dec_rpt
        )

        cases_evaluated += 1
        total_ev_comp += case_conf["evidence_completeness"]
        total_agent_agree += case_conf["agent_agreement"]
        total_source_div += case_conf["source_diversity"]
        total_contradictions += case_conf["contradiction_count"]

    if cases_evaluated > 0:
        avg_ev_comp = round(total_ev_comp / cases_evaluated, 1)
        avg_agree = round(total_agent_agree / cases_evaluated, 1)
        avg_div = round(total_source_div / cases_evaluated, 1)
        avg_contra = int(round(total_contradictions / cases_evaluated))

        raw_score = (0.35 * avg_ev_comp) + (0.40 * avg_agree) + (0.25 * avg_div) - (1.0 * avg_contra)
        composite_score = round(min(100.0, max(0.0, raw_score)), 1)
        conf_level = "HIGH CONFIDENCE" if composite_score >= 85.0 else ("MEDIUM CONFIDENCE" if composite_score >= 60.0 else "LOW CONFIDENCE")
        status_val = "AVAILABLE"
    else:
        avg_ev_comp = 0.0
        avg_agree = 0.0
        avg_div = 0.0
        avg_contra = 0
        composite_score = 0.0
        conf_level = "INSUFFICIENT DATA"
        status_val = "INSUFFICIENT_DATA"

    investigation_confidence = {
        "status": status_val,
        "score": composite_score,
        "confidence_score": composite_score,
        "label": conf_level,
        "confidence_level": conf_level,
        "evidence_completeness": avg_ev_comp,
        "agent_agreement": avg_agree,
        "source_diversity": avg_div,
        "contradiction_count": avg_contra,
        "cases_evaluated": cases_evaluated,
        "timeframe": timeframe,
        "weights": {
            "evidence_completeness": 0.35,
            "agent_agreement": 0.40,
            "source_diversity": 0.25,
            "contradiction_penalty": 1.0
        },
        "distinction": "Evidence Support Index • Not Fraud Probability",
        "explanation": "Measures how strongly the investigation conclusion is supported by empirical evidence completeness, agent agreement, source diversity, and identified contradictions."
    }

    # 4. Action Outcomes (Deterministic policy enforcement records filtered by selected timeframe)
    executed_map = data_store.get("executed_actions", {})
    action_counts = {}
    status_breakdown = {}
    auto_count = 0
    human_count = 0

    from datetime import timedelta
    def parse_action_time(rec):
        raw = rec.get("timestamp")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            return None

    cutoff_action = None
    if timeframe:
        tf_delta_map = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "12m": timedelta(days=365)
        }
        delta = tf_delta_map.get(timeframe)
        if delta:
            cutoff_action = datetime.now(timezone.utc) - delta

    filtered_action_records = []
    for rec in executed_map.values():
        rec_time = parse_action_time(rec)
        if cutoff_action is not None and rec_time is not None:
            if rec_time < cutoff_action:
                continue
        filtered_action_records.append(rec)

    is_auto = bool(data_store.get("automation_mode", False))

    for rec in filtered_action_records:
        ac = rec.get("action_code") or rec.get("action", "MONITOR")
        action_counts[ac] = action_counts.get(ac, 0) + 1
        st = rec.get("execution_status", "UNKNOWN")
        if ac not in status_breakdown:
            status_breakdown[ac] = {}
        status_breakdown[ac][st] = status_breakdown[ac].get(st, 0) + 1

        if rec.get("actor_type") == "AUTOMATION_ENGINE":
            auto_count += 1
        elif rec.get("actor_type") == "HUMAN_OPERATOR":
            human_count += 1

    total_actions_timeframe = len(filtered_action_records)

    SUPPORTED_ACTION_CONFIG = [
        {"code": "ESCALATE_ANALYST_REVIEW", "action": "ESCALATE", "severity": "HIGH", "default_status": "Escalated to Queue"},
        {"code": "FREEZE", "action": "FREEZE", "severity": "CRITICAL", "default_status": "Requires Operator Action"},
        {"code": "ENHANCED_MONITORING", "action": "ENHANCED MONITORING", "severity": "MEDIUM", "default_status": "High Risk Watch"},
        {"code": "MONITOR", "action": "MONITOR", "severity": "LOW", "default_status": "Standard Baseline"},
        {"code": "BLOCK", "action": "BLOCK", "severity": "CRITICAL", "default_status": "Simulated Block"},
        {"code": "REJECT_TRANSACTION", "action": "REJECT", "severity": "CRITICAL", "default_status": "Transaction Rejection"},
        {"code": "FILE_STR", "action": "FILE STR", "severity": "HIGH", "default_status": "Regulatory Filing"},
        {"code": "CLOSE_ACCOUNT", "action": "CLOSE ACCOUNT", "severity": "CRITICAL", "default_status": "Account Closure"}
    ]

    action_outcomes = []
    for cfg in SUPPORTED_ACTION_CONFIG:
        cnt = action_counts.get(cfg["code"], 0)
        pct = round((cnt / max(total_actions_timeframe, 1)) * 100, 1) if total_actions_timeframe > 0 else 0.0
        st_dict = status_breakdown.get(cfg["code"], {})

        if cfg["code"] == "FREEZE":
            status_desc = f"Requires Operator Action ({cnt} pending)" if cnt > 0 else "Supported • 0 recorded in timeframe"
        elif cnt > 0:
            if not is_auto:
                status_desc = f"Policy Evaluated • Held ({cnt} records)"
            else:
                status_desc = f"Autonomous Execution ({cnt} executed)"
        else:
            status_desc = "Supported • 0 recorded in timeframe"

        action_outcomes.append({
            "action": cfg["action"],
            "code": cfg["code"],
            "count": cnt,
            "percentage": pct,
            "severity": cfg["severity"],
            "status": status_desc,
            "status_breakdown": st_dict,
            "supported": True,
            "is_tracked": True
        })

    # 5. Automation Intelligence
    total_actions = auto_count + human_count
    automation_rate = round((auto_count / max(total_actions, 1)) * 100, 1) if total_actions > 0 else 0.0

    automation_intelligence = {
        "automation_mode": is_auto,
        "automated_actions_count": auto_count,
        "human_actions_count": human_count,
        "automation_rate": automation_rate,
        "operator_interventions_count": human_count,
        "freeze_interventions_count": action_counts.get("FREEZE", 0),
        "total_actions_recorded": total_actions_timeframe
    }

    # 6. Channel Performance
    channels = ["UPI", "IMPS", "NEFT", "CARD", "NET BANKING"]
    channel_performance = []
    for ch in channels:
        ch_txs = [t for t in tx_list if (t.get("channel") or "").upper() == ch.replace(" ", "")]
        if not ch_txs:
            ch_txs = [t for t in tx_list if ch.split()[0] in (t.get("channel") or "").upper()]
        c_cnt = len(ch_txs)
        c_amt = sum(float(t.get("amount", 0)) for t in ch_txs)
        c_risk = sum(1 for t in ch_txs if float(t.get("risk_score", 0)) >= 40)
        channel_performance.append({
            "channel": ch,
            "tx_count": c_cnt,
            "total_amount": c_amt,
            "risk_rate": round((c_risk / max(c_cnt, 1)) * 100, 1)
        })

    # 7. Detected Patterns
    detected_patterns = [
        {"pattern": "New Receiver", "occurrences": sum(1 for t in tx_list if "New receiver" in str(t.get("reason", ""))), "risk_contribution": "Medium"},
        {"pattern": "High Transaction Amount", "occurrences": sum(1 for t in tx_list if "High transaction amount" in str(t.get("reason", ""))), "risk_contribution": "High"},
        {"pattern": "Cross-Border Activity", "occurrences": sum(1 for t in tx_list if t.get("is_cross_border") or "cross-border" in str(t.get("reason", "")).lower()), "risk_contribution": "Critical"},
        {"pattern": "Multi-Hop Mule Chain", "occurrences": sum(1 for t in tx_list if t.get("pattern_type") == "MULE_CHAIN" or (t.get("total_hops") or 1) > 1), "risk_contribution": "Critical"},
        {"pattern": "Funnel Account", "occurrences": sum(1 for t in tx_list if t.get("pattern_type") == "FUNNEL"), "risk_contribution": "High"},
        {"pattern": "Circular Flow", "occurrences": sum(1 for t in tx_list if t.get("pattern_type") == "CIRCULAR"), "risk_contribution": "Critical"}
    ]

    # 8. Network Intelligence (Multi-Hop)
    multihop_txs = [t for t in tx_list if (t.get("total_hops") or 1) > 1]
    max_hops = max([t.get("total_hops", 1) for t in tx_list] + [1])
    avg_hops = round(sum([t.get("total_hops", 1) for t in tx_list]) / max(total_tx, 1), 1) if total_tx else 1.0

    network_intelligence = {
        "avg_hops": avg_hops,
        "max_hops": max_hops,
        "multihop_cases": len(multihop_txs),
        "mule_networks": sum(1 for t in tx_list if t.get("pattern_type") == "MULE_CHAIN"),
        "circular_flows": sum(1 for t in tx_list if t.get("pattern_type") == "CIRCULAR"),
        "shared_intermediaries": sum(1 for t in tx_list if t.get("pattern_type") == "SHARED_INTERMEDIARY")
    }

    # 9. Financial Impact
    total_exposure = sum(float(c.get("total_fraud_amount", 0)) for c in cases_list) or sum(float(t.get("amount", 0)) for t in tx_list if float(t.get("risk_score", 0)) >= 70)
    recovered_assets = sum(float(c.get("recoverable_amount", 0)) for c in cases_list)
    estimated_loss = max(0.0, total_exposure - recovered_assets)
    recovery_rate = round((recovered_assets / max(total_exposure, 1.0)) * 100, 1)

    financial_impact = {
        "total_exposure": total_exposure,
        "recovered_assets": recovered_assets,
        "estimated_loss": estimated_loss,
        "recovery_rate": recovery_rate
    }

    # 10. System Health
    system_health = {
        "pipeline": "Operational",
        "database": "Operational",
        "websocket": "Operational",
        "risk_engine": "Operational",
        "policy_engine": "Operational",
        "automation_engine": "Operational" if is_auto else "Standby (Manual Mode)"
    }

    return {
        "timeframe": timeframe,
        "kpis": {
            "total_transactions": total_tx,
            "risk_alerts": total_alerts,
            "avg_risk_score": avg_score,
            "cases_resolved": total_resolved
        },
        "risk_trend": risk_trend,
        "alerts_by_risk_level": alerts_by_risk_level,
        "investigation_performance": investigation_performance,
        "investigation_confidence": investigation_confidence,
        "action_outcomes": action_outcomes,
        "automation_intelligence": automation_intelligence,
        "risk_distribution": alerts_by_risk_level,
        "channel_performance": channel_performance,
        "detected_patterns": detected_patterns,
        "network_intelligence": network_intelligence,
        "financial_impact": financial_impact,
        "system_health": system_health
    }



@app.post("/automation-mode")
async def set_automation_mode(
    payload: AutomationModeRequest,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    enabled = bool(payload.enabled)
    data_store["automation_mode"] = enabled
    now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data_store["automation_mode_updated_at"] = now_str
    data_store["automation_mode_updated_by"] = payload.operator_id or "OPERATOR_ADMIN"

    event_type = "AUTOMATION_MODE_ENABLED" if enabled else "AUTOMATION_MODE_DISABLED"

    audit_record = {
        "audit_id": f"AUD-MODE-{str(uuid4())[:8].upper()}",
        "event_type": event_type,

        "case_id": "CASE-SYSTEM",
        "primary_tx_id": "TX-SYSTEM-MODE",
        "analyst_id": payload.operator_id or "OPERATOR_ADMIN",
        "analyst_role": "OPERATOR",
        "action_code": "TOGGLE_AUTOMATION_MODE",
        "previous_case_status": "NEW",
        "new_case_status": "NEW",
        "analyst_notes": f"AUTOMATE MODE set to {'ON' if enabled else 'OFF'} by {payload.operator_id or 'OPERATOR_ADMIN'}",
        "risk_acknowledged": False,
        "decision_support_summary": {
            "automate_mode": enabled,
            "event_type": event_type,
            "operator_id": payload.operator_id or "OPERATOR_ADMIN",
            "timestamp": now_str
        },
        "traceability_chain": {
            "automate_mode": enabled,
            "event_type": event_type,
            "operator_id": payload.operator_id or "OPERATOR_ADMIN",
            "timestamp": now_str
        },
        "timestamp": now_str
    }

    try:
        await repo.save_audit_event(audit_record)
        if isinstance(repo, PostgreSQLCaseRepository):
            await repo.session.commit()
    except Exception as err:
        print(f"[Main] Warning: Failed to persist mode change audit: {err}")

    await manager.broadcast({
        "event": "automation.mode.changed",
        "automate_mode": enabled,
        "updated_at": now_str,
        "updated_by": payload.operator_id or "OPERATOR_ADMIN"
    })

    # When Automation Mode is set to ON, sweep pending eligible transactions
    if enabled:
        from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
        from app.services.simulated_action_executor import execute_simulated_action
        
        tx_dict = data_store.get("transactions", {})
        cases_dict = data_store.get("cases", {})

        for tx_id, tx in list(tx_dict.items()):
            exec_rec = tx.get("execution_record") or {}
            exec_status = exec_rec.get("execution_status")
            if exec_status in ("NOT_EXECUTED", None) or exec_rec.get("automation_mode") == "AUTOMATE_OFF":
                case_id = tx.get("case_id")
                case_obj = cases_dict.get(case_id) if case_id else None
                pol = evaluate_autonomous_policy(tx, case_obj, automate_mode=True)
                
                if pol.get("action") != "FREEZE" and pol.get("decision") == "EXECUTE":
                    updated_rec = await execute_simulated_action(
                        case_id=case_id,
                        tx_id=tx_id,
                        action_code=pol.get("action", "MONITOR"),
                        policy_decision=pol,
                        repo=repo,
                        actor_type="AUTOMATION_ENGINE",
                        actor_id="AUTOMATION_ENGINE"
                    )
                    tx["execution_record"] = updated_rec
                    tx["response_decision"] = pol

                    await manager.broadcast({
                        "event": "automation.action.executed",
                        "action": pol.get("action"),
                        "action_code": pol.get("action"),
                        "transaction_id": tx_id,
                        "tx_id": tx_id,
                        "case_id": case_id,
                        "execution_result": updated_rec,
                        "policy_decision": pol,
                        "action_executed": True,
                        "actor_type": "AUTOMATION_ENGINE",
                        "timestamp": updated_rec.get("timestamp") or _now_iso()
                    })

                    await manager.broadcast({
                        "event": "transaction.action",
                        "transaction_id": tx_id,
                        "tx_id": tx_id,
                        "risk_score": tx.get("risk_score", 0),
                        "risk_level": pol.get("risk_level", "LOW"),
                        "action": pol.get("action"),
                        "action_status": "SUCCESS",
                        "reason": pol.get("reason", "Autonomous execution on mode enable"),
                        "automated": True,
                        "actor_type": "AUTOMATION_ENGINE",
                        "case_id": case_id,
                        "timestamp": updated_rec.get("timestamp") or _now_iso(),
                        "execution_record": updated_rec,
                        "policy_decision": pol
                    })

    return {
        "status": "success",
        "automate_mode": enabled,
    }



@app.post("/attack-mode")
async def trigger_attack_mode() -> dict[str, Any]:
    """
    Triggers a connected suspicious multi-hop attack chain (5 hops across 6 nodes).
    Generates ACC-ATTACK-SOURCE -> ACC-MULE-01 -> ACC-INTERMEDIARY-01 -> ACC-MULE-02 -> ACC-INTERMEDIARY-02 -> ACC-DRAIN-DESTINATION.
    Injects each hop into the pipeline under a single case_id and broadcasts updates via WebSocket.
    The final hop triggers CRITICAL risk score and FREEZE policy evaluation.
    """
    import asyncio, random, string, uuid as _uuid
    from datetime import datetime, timezone as _tz

    def _now():
        return datetime.now(_tz.utc).isoformat().replace("+00:00", "Z")

    chain_id = f"CHAIN-ATTACK-{_uuid.uuid4().hex[:8].upper()}"
    case_id = f"CASE-{chain_id[6:]}"
    root_tx_id = f"TX-{_uuid.uuid4().hex[:8].upper()}"
    seed = random.randint(1000, 9999)

    attack_nodes = [
        (f"ACC-USR-{seed}", "SOURCE"),
        (f"ACC-MULE-{random.randint(1000, 9999)}", "MULE"),
        (f"ACC-HUB-{random.randint(1000, 9999)}", "INTERMEDIARY"),
        (f"ACC-MULE-{random.randint(1000, 9999)}", "MULE"),
        (f"ACC-HUB-{random.randint(1000, 9999)}", "INTERMEDIARY"),
        (f"ACC-MERCH-{random.randint(1000, 9999)}", "DESTINATION")
    ]
    for acc_id, acc_type in attack_nodes:
        data_store.setdefault("accounts", {})[acc_id] = {
            "account_id": acc_id,
            "account_type": acc_type,
            "status": "active"
        }

    ATTACK_HOPS = [
        {"is_cross_border": True, "channel": "NEFT", "amount": 480000.0, "risk_score": 75},
        {"is_crypto_related": True, "channel": "IMPS", "amount": 465000.0, "risk_score": 80},
        {"device_changed": True, "location_changed": True, "channel": "UPI", "amount": 450000.0, "risk_score": 85},
        {"on_active_call": True, "is_scripted": True, "channel": "CARD", "amount": 435000.0, "risk_score": 90},
        {"bulk_transfer_flag": True, "channel": "NEFT", "amount": 420000.0, "risk_score": 98, "requested_action": "FREEZE", "reason": "Active multi-hop fraud attack chain detected requiring account freeze."}
    ]

    async def _fire_burst():
        prev_tx_id = None
        for i, hspec in enumerate(ATTACK_HOPS):
            tx_id = root_tx_id if i == 0 else f"TX-{_uuid.uuid4().hex[:8].upper()}"
            sender_acc = attack_nodes[i][0]
            receiver_acc = attack_nodes[i+1][0]
            tx = {
                "tx_id": tx_id,
                "timestamp": _now(),
                "case_id": case_id,
                "sender_account": sender_acc,
                "receiver_account": receiver_acc,
                "amount": hspec["amount"],
                "currency": "INR",
                "channel": hspec.get("channel", "NEFT"),
                "chain_id": chain_id,
                "hop_number": i + 1,
                "total_hops": 5,
                "pattern_type": "MULE_CHAIN",
                "parent_transaction_id": prev_tx_id,
                "root_transaction_id": root_tx_id,
                "risk_score": hspec["risk_score"]
            }
            prev_tx_id = tx_id
            for k, v in hspec.items():
                if k not in ("channel", "amount"):
                    tx[k] = v

            result = run_pipeline(tx, data_store)
            transaction = result.get("transaction") or {}
            tx_event = {
                "event": "tx_scored",
                "tx_id": transaction.get("tx_id", ""),
                "timestamp": transaction.get("timestamp") or _now(),
                "case_id": transaction.get("case_id", ""),
                "risk_score": float(transaction.get("risk_score", 0.0)),
                "amount": float(transaction.get("amount", 0.0)),
                "sender_account": transaction.get("sender_account", "UNKNOWN"),
                "receiver_account": transaction.get("receiver_account", "UNKNOWN"),
                "channel": transaction.get("channel", "NEFT"),
                "risk_factors": transaction.get("risk_factors", []),
                "threshold": transaction.get("threshold", "LOW"),
                "reason": transaction.get("reason", "Attack chain hop"),
                "full_reason": transaction.get("full_reason", ""),
                "confidence": transaction.get("confidence", "HIGH"),
                "ml_score": transaction.get("ml_score", 0),
                "rule_score": transaction.get("rule_score", 0),
                "ml_feature_importance": transaction.get("ml_feature_importance", {})
            }
            await manager.broadcast(tx_event)
            case = result.get("case")
            if case:
                await manager.broadcast({"event": "case_updated", **_case_payload(case)})
            await asyncio.sleep(0.1)

    await _fire_burst()
    return {"ok": True, "message": "Attack mode connected 5-hop chain initiated", "case_id": case_id, "chain_id": chain_id}




@app.post("/simulate/multi_hop_scenario/{scenario_id}")
async def trigger_multi_hop_scenario(
    scenario_id: str,
    repo: AbstractCaseRepository = Depends(get_repository)
) -> dict[str, Any]:
    """
    Generates deterministic multi-hop transaction scenarios (Patterns A-F):
    1. normal / scenario-1 (1 hop)
    2. 3-hop / scenario-2 (3 hops)
    3. 5-hop / scenario-3 (5-hop mule chain)
    4. funnel / scenario-4 (Funnel account)
    5. fan-out / scenario-5 (Fan-out distribution)
    6. circular / scenario-6 (Circular flow)
    """
    s_key = scenario_id.lower().strip()
    chain_id = f"CHAIN-{uuid4().hex[:8].upper()}"
    case_id = f"CASE-{chain_id[6:]}"
    ts = _now_iso()
    generated_txs = []

    if s_key in ("scenario-1", "normal", "1-hop"):
        # Pattern A: Normal Payment (1-2 hops)
        tx = {
            "tx_id": f"TX-M1-001",
            "timestamp": ts,
            "case_id": case_id,
            "sender_account": "ACC-USR-1023",
            "receiver_account": "ACC-MERCH-4412",
            "amount": 1500.0,
            "risk_score": 15,
            "channel": "UPI",
            "chain_id": chain_id,
            "hop_number": 1,
            "total_hops": 1,
            "pattern_type": "NORMAL_PAYMENT"
        }
        generated_txs.append(tx)

    elif s_key in ("scenario-2", "3-hop"):
        # Pattern B: 3-Hop Transfer
        nodes = ["ACC-USR-1023", "ACC-INT-7732", "ACC-MULE-4821", "ACC-MERCH-4412"]
        root_tx_id = f"TX-M3-001"
        for i in range(len(nodes) - 1):
            tx_id = f"TX-M3-00{i+1}"
            tx = {
                "tx_id": tx_id,
                "timestamp": ts,
                "case_id": case_id,
                "sender_account": nodes[i],
                "receiver_account": nodes[i+1],
                "amount": round(45000.0 * (0.98 ** i), 2),
                "risk_score": 65 + (i * 10),
                "channel": "IMPS",
                "chain_id": chain_id,
                "hop_number": i + 1,
                "total_hops": 3,
                "pattern_type": "3_HOP_TRANSFER",
                "parent_transaction_id": f"TX-M3-00{i}" if i > 0 else None,
                "root_transaction_id": root_tx_id
            }
            generated_txs.append(tx)

    elif s_key in ("scenario-3", "5-hop", "mule-chain"):
        # Pattern B: 5-Hop Mule Chain / Layering (Critical FREEZE)
        nodes = [
            ("ACC-USR-1023", "SOURCE"),
            ("ACC-MULE-4821", "MULE"),
            ("ACC-INT-7732", "INTERMEDIARY"),
            ("ACC-MULE-9182", "MULE"),
            ("ACC-MERCH-4412", "DESTINATION")
        ]
        root_tx_id = f"TX-M5-001"
        for i in range(len(nodes) - 1):
            tx_id = f"TX-M5-00{i+1}"
            s_acc, _ = nodes[i]
            r_acc, _ = nodes[i+1]
            tx = {
                "tx_id": tx_id,
                "timestamp": ts,
                "case_id": case_id,
                "sender_account": s_acc,
                "receiver_account": r_acc,
                "amount": round(98000.0 * (0.97 ** i), 2),
                "risk_score": min(95, 75 + (i * 5)),
                "requested_action": "FREEZE" if i == len(nodes) - 2 else "ENHANCED_MONITORING",
                "reason": f"Multi-hop mule chain layering (Hop {i+1}/4) across rapid velocity accounts.",
                "channel": "SWIFT" if i >= 2 else "NEFT",
                "chain_id": chain_id,
                "hop_number": i + 1,
                "total_hops": 4,
                "pattern_type": "MULE_CHAIN",
                "parent_transaction_id": f"TX-M5-00{i}" if i > 0 else None,
                "root_transaction_id": root_tx_id
            }
            generated_txs.append(tx)

    elif s_key in ("scenario-4", "funnel"):
        # Pattern C: Funnel Account (Multiple senders -> Funnel -> Destination)
        senders = ["ACC-USR-101", "ACC-USR-102", "ACC-USR-103", "ACC-USR-104"]
        funnel = "ACC-FUNNEL-9900"
        dest = "ACC-MERCH-4412"
        root_tx_id = f"TX-FN-001"
        for i, s_acc in enumerate(senders):
            tx = {
                "tx_id": f"TX-FN-IN-00{i+1}",
                "timestamp": ts,
                "case_id": case_id,
                "sender_account": s_acc,
                "receiver_account": funnel,
                "amount": 25000.0,
                "risk_score": 70,
                "channel": "UPI",
                "chain_id": chain_id,
                "hop_number": 1,
                "total_hops": 2,
                "pattern_type": "FUNNEL_ACCOUNT",
                "root_transaction_id": root_tx_id
            }
            generated_txs.append(tx)
        # Outflow from Funnel
        generated_txs.append({
            "tx_id": f"TX-FN-OUT-001",
            "timestamp": ts,
            "case_id": case_id,
            "sender_account": funnel,
            "receiver_account": dest,
            "amount": 100000.0,
            "risk_score": 88,
            "channel": "NEFT",
            "chain_id": chain_id,
            "hop_number": 2,
            "total_hops": 2,
            "pattern_type": "FUNNEL_ACCOUNT",
            "parent_transaction_id": "TX-FN-IN-001",
            "root_transaction_id": root_tx_id
        })

    elif s_key in ("scenario-5", "fan-out"):
        # Pattern D: Fan-Out (Source -> Multiple receivers)
        source = "ACC-USR-1023"
        receivers = ["ACC-RECV-A", "ACC-RECV-B", "ACC-RECV-C", "ACC-RECV-D"]
        root_tx_id = f"TX-FO-001"
        for i, r_acc in enumerate(receivers):
            tx = {
                "tx_id": f"TX-FO-00{i+1}",
                "timestamp": ts,
                "case_id": case_id,
                "sender_account": source,
                "receiver_account": r_acc,
                "amount": 12500.0,
                "risk_score": 82,
                "channel": "IMPS",
                "chain_id": chain_id,
                "hop_number": 1,
                "total_hops": 1,
                "pattern_type": "FAN_OUT",
                "root_transaction_id": root_tx_id
            }
            generated_txs.append(tx)

    elif s_key in ("scenario-6", "circular"):
        # Pattern E: Circular Flow (A -> B -> C -> D -> A)
        nodes = ["ACC-A-101", "ACC-B-102", "ACC-C-103", "ACC-D-104", "ACC-A-101"]
        root_tx_id = f"TX-CIRC-001"
        for i in range(len(nodes) - 1):
            tx = {
                "tx_id": f"TX-CIRC-00{i+1}",
                "timestamp": ts,
                "case_id": case_id,
                "sender_account": nodes[i],
                "receiver_account": nodes[i+1],
                "amount": 50000.0,
                "risk_score": 90,
                "channel": "NEFT",
                "chain_id": chain_id,
                "hop_number": i + 1,
                "total_hops": 4,
                "pattern_type": "CIRCULAR_FLOW",
                "parent_transaction_id": f"TX-CIRC-00{i}" if i > 0 else None,
                "root_transaction_id": root_tx_id
            }
            generated_txs.append(tx)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario_id '{scenario_id}'. Use scenario-1 to scenario-6.")

    processed_records = []
    from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
    from app.services.simulated_action_executor import execute_simulated_action

    automate_mode = data_store.get("automation_mode", False)

    for tx in generated_txs:
        res = run_pipeline(tx, data_store)
        transaction = res.get("transaction") or tx
        case = res.get("case")

        sender_id = transaction.get("sender_account")
        receiver_id = transaction.get("receiver_account")
        accounts_to_save = []
        if sender_id:
            accounts_to_save.append(data_store.get("accounts", {}).get(sender_id) or {
                "account_id": sender_id,
                "kyc_status": _get_account_kyc_status(sender_id)
            })
        if receiver_id and receiver_id != sender_id:
            accounts_to_save.append(data_store.get("accounts", {}).get(receiver_id) or {
                "account_id": receiver_id,
                "kyc_status": _get_account_kyc_status(receiver_id)
            })

        await repo.save_transaction_and_case(accounts_to_save, transaction, case)

        p_dec = evaluate_autonomous_policy(tx=transaction, case=case, automate_mode=automate_mode)
        exec_rec = await execute_simulated_action(
            case_id=case.get("case_id") if case else transaction.get("case_id"),
            tx_id=transaction.get("tx_id"),
            action_code=p_dec.get("action", "MONITOR"),
            policy_decision=p_dec,
            repo=repo
        )
        transaction["execution_record"] = exec_rec
        res["execution_record"] = exec_rec

        # Broadcast real-time events
        await manager.broadcast({
            "event": "tx_scored",
            "tx_id": transaction.get("tx_id"),
            "timestamp": transaction.get("timestamp"),
            "case_id": transaction.get("case_id"),
            "risk_score": float(transaction.get("risk_score", 0.0)),
            "amount": float(transaction.get("amount", 0.0)),
            "sender_account": sender_id,
            "receiver_account": receiver_id,
            "channel": transaction.get("channel", "UPI"),
            "chain_id": transaction.get("chain_id"),
            "hop_number": transaction.get("hop_number"),
            "total_hops": transaction.get("total_hops"),
            "pattern_type": transaction.get("pattern_type")
        })
        if case:
            await manager.broadcast({"event": "case_updated", **_case_payload(case)})

        processed_records.append({
            "tx_id": transaction.get("tx_id"),
            "chain_id": transaction.get("chain_id"),
            "hop_number": transaction.get("hop_number"),
            "total_hops": transaction.get("total_hops"),
            "pattern_type": transaction.get("pattern_type"),
            "risk_score": transaction.get("risk_score"),
            "action": p_dec.get("action"),
            "execution_status": exec_rec.get("execution_status")
        })

    if isinstance(repo, PostgreSQLCaseRepository):
        await repo.session.commit()

    return {
        "ok": True,
        "scenario_id": s_key,
        "chain_id": chain_id,
        "pattern_type": generated_txs[0].get("pattern_type"),
        "total_transactions": len(processed_records),
        "transactions": processed_records
    }



async def _process_and_broadcast_tx(tx: dict):
    result = run_pipeline(tx, data_store)
    transaction = result.get("transaction") or {}
    case = result.get("case")

    policy_decision, execution_record = await _process_policy_and_action(transaction, case, repo=None)

    if "transactions" not in data_store:
        data_store["transactions"] = {}
    data_store["transactions"][transaction.get("tx_id")] = transaction

    tx_event = {
        "event": "tx_scored",
        "tx_id": transaction.get("tx_id", ""),
        "timestamp": transaction.get("timestamp") or _now_iso(),
        "case_id": transaction.get("case_id", ""),
        "risk_score": float(transaction.get("risk_score", 0.0)),
        "amount": float(transaction.get("amount", 0.0)),
        "sender_account": transaction.get("sender_account", "UNKNOWN"),
        "receiver_account": transaction.get("receiver_account", "UNKNOWN"),
        "channel": transaction.get("channel", "UPI"),
        "risk_factors": transaction.get("risk_factors", []),
        "threshold": transaction.get("threshold", "LOW"),
        "reason": transaction.get("reason", "Low risk pattern"),
        "full_reason": transaction.get("full_reason", ""),
        "confidence": transaction.get("confidence", "LOW"),
        "ml_score": transaction.get("ml_score", 0),
        "rule_score": transaction.get("rule_score", 0),
        "ml_feature_importance": transaction.get("ml_feature_importance", {}),
        "account_status": execution_record.get("resulting_account_state", "ACTIVE"),
        "execution_record": execution_record,
        "policy_decision": policy_decision,
        "response_decision": policy_decision
    }
    await manager.broadcast(tx_event)

    exec_status = execution_record.get("execution_status", "NOT_EXECUTED")
    is_operator_req = (exec_status == "REQUIRES_OPERATOR_ACTION")

    await manager.broadcast({
        "event": "transaction.action",
        "transaction_id": transaction.get("tx_id", ""),
        "tx_id": transaction.get("tx_id", ""),
        "risk_score": float(transaction.get("risk_score", 0.0)),
        "risk_level": policy_decision.get("risk_level", "LOW"),
        "action": policy_decision.get("action", "MONITOR"),
        "action_status": exec_status,
        "reason": policy_decision.get("reason", transaction.get("reason", "")),
        "automated": bool(execution_record.get("automation_mode") == "AUTOMATE_ON" and not is_operator_req),
        "mode": execution_record.get("automation_mode", "AUTOMATE_OFF"),
        "requires_human_approval": bool(exec_status == "REJECTED" or is_operator_req),
        "financial_action_status": "HUMAN AUTHORIZATION REQUIRED" if (exec_status == "REJECTED" or is_operator_req) else "NOT_APPLICABLE",
        "case_id": case.get("case_id") if case else transaction.get("case_id", ""),
        "timestamp": execution_record.get("timestamp") or _now_iso(),
        "execution_record": execution_record,
        "policy_decision": policy_decision
    })

    if case:
        if execution_record.get("execution_status") == "SUCCESS":
            act_code = policy_decision.get("action", "MONITOR")
            case.setdefault("actions_taken", []).insert(0, {
                "action_id": f"ACT-{uuid4().hex[:10].upper()}",
                "case_id": case.get("case_id"),
                "action_type": act_code,
                "action": act_code,
                "target_id": transaction.get("sender_account", "ACC-UNKNOWN"),
                "status": "SUCCESS",
                "timestamp": execution_record.get("timestamp") or _now_iso(),
                "reason": policy_decision.get("reason", "Automated policy execution")
            })
            if act_code in ["FREEZE", "BLOCK", "FILE_STR", "MONITOR", "ENHANCED_MONITORING"]:
                case["status"] = "ACTIONED"
        await manager.broadcast({"event": "case_updated", **_case_payload(case)})


async def _baseline_loop():
    """
    Launches a continuous background simulation loop on backend startup.
    Generates genuine, structurally diverse transactions (direct transfers, linear multi-hop chains,
    fan-in pooling, and fan-out dispersion) so different transactions produce distinct investigation graphs.
    """
    await asyncio.sleep(0.5)
    while True:
        try:
            pattern = random.choices(["DIRECT", "LINEAR", "FAN_IN", "FAN_OUT"], weights=[40, 20, 20, 20])[0]

            if pattern == "DIRECT":
                tier = random.choices(["LOW", "MEDIUM", "HIGH"], weights=[65, 25, 10])[0]
                channel = random.choice(["UPI", "IMPS", "NEFT", "CARD"])
                s_id = f"ACC-USR-{random.randint(1000, 9999)}"
                r_id = f"ACC-MERCH-{random.randint(1000, 9999)}"
                amt = round(random.uniform(500, 15000), 2) if tier == "LOW" else round(random.uniform(25000, 85000), 2)
                tx = {
                    "tx_id": f"TX-{uuid4().hex[:8].upper()}",
                    "timestamp": _now_iso(),
                    "sender_account": s_id,
                    "receiver_account": r_id,
                    "amount": amt,
                    "currency": "INR",
                    "channel": channel,
                    "risk_score": 15 if tier == "LOW" else 55
                }
                await _process_and_broadcast_tx(tx)

            elif pattern == "LINEAR":
                # 3 entities: Victim -> Mule -> Exit
                chain_id = f"CHAIN-{uuid4().hex[:8].upper()}"
                case_id = f"CASE-{chain_id[6:]}"
                root_tx_id = f"TX-{uuid4().hex[:8].upper()}"
                v_id = f"ACC-USR-{random.randint(1000, 9999)}"
                m_id = f"ACC-MULE-{random.randint(1000, 9999)}"
                d_id = f"ACC-MERCH-{random.randint(1000, 9999)}"
                amt1 = round(random.uniform(120000, 280000), 2)
                amt2 = round(amt1 * 0.94, 2)

                tx1 = {
                    "tx_id": root_tx_id,
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": v_id,
                    "receiver_account": m_id,
                    "amount": amt1,
                    "currency": "INR",
                    "channel": "IMPS",
                    "hop_number": 1,
                    "total_hops": 2,
                    "root_transaction_id": root_tx_id,
                    "risk_score": 75
                }
                await _process_and_broadcast_tx(tx1)
                await asyncio.sleep(0.4)

                tx2 = {
                    "tx_id": f"TX-{uuid4().hex[:8].upper()}",
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": m_id,
                    "receiver_account": d_id,
                    "amount": amt2,
                    "currency": "INR",
                    "channel": "UPI",
                    "hop_number": 2,
                    "total_hops": 2,
                    "parent_transaction_id": root_tx_id,
                    "root_transaction_id": root_tx_id,
                    "risk_score": 85
                }
                await _process_and_broadcast_tx(tx2)

            elif pattern == "FAN_IN":
                # 4 entities: 2 Victims -> 1 Aggregator Collector -> Exit
                chain_id = f"CHAIN-{uuid4().hex[:8].upper()}"
                case_id = f"CASE-{chain_id[6:]}"
                root_tx_id = f"TX-{uuid4().hex[:8].upper()}"
                v1_id = f"ACC-USR-{random.randint(1000, 9999)}"
                v2_id = f"ACC-USR-{random.randint(1000, 9999)}"
                agg_id = f"ACC-HUB-{random.randint(1000, 9999)}"
                exit_id = f"ACC-MERCH-{random.randint(1000, 9999)}"
                amt1 = round(random.uniform(70000, 150000), 2)
                amt2 = round(random.uniform(60000, 140000), 2)
                amt3 = round((amt1 + amt2) * 0.96, 2)

                tx1 = {
                    "tx_id": root_tx_id,
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": v1_id,
                    "receiver_account": agg_id,
                    "amount": amt1,
                    "currency": "INR",
                    "channel": "UPI",
                    "hop_number": 1,
                    "total_hops": 2,
                    "risk_score": 70
                }
                await _process_and_broadcast_tx(tx1)
                await asyncio.sleep(0.3)

                tx2 = {
                    "tx_id": f"TX-{uuid4().hex[:8].upper()}",
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": v2_id,
                    "receiver_account": agg_id,
                    "amount": amt2,
                    "currency": "INR",
                    "channel": "IMPS",
                    "hop_number": 1,
                    "total_hops": 2,
                    "risk_score": 72
                }
                await _process_and_broadcast_tx(tx2)
                await asyncio.sleep(0.3)

                tx3 = {
                    "tx_id": f"TX-{uuid4().hex[:8].upper()}",
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": agg_id,
                    "receiver_account": exit_id,
                    "amount": amt3,
                    "currency": "INR",
                    "channel": "NEFT",
                    "hop_number": 2,
                    "total_hops": 2,
                    "risk_score": 92
                }
                await _process_and_broadcast_tx(tx3)

            else: # FAN_OUT
                # 4 entities: 1 Origin -> 1 Mule Hub -> 2 Endpoints
                chain_id = f"CHAIN-{uuid4().hex[:8].upper()}"
                case_id = f"CASE-{chain_id[6:]}"
                root_tx_id = f"TX-{uuid4().hex[:8].upper()}"
                v_id = f"ACC-USR-{random.randint(1000, 9999)}"
                hub_id = f"ACC-MULE-{random.randint(1000, 9999)}"
                out1_id = f"ACC-MERCH-{random.randint(1000, 9999)}"
                out2_id = f"ACC-MERCH-{random.randint(1000, 9999)}"
                total_amt = round(random.uniform(180000, 360000), 2)
                amt1 = round(total_amt * 0.48, 2)
                amt2 = round(total_amt * 0.48, 2)

                tx1 = {
                    "tx_id": root_tx_id,
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": v_id,
                    "receiver_account": hub_id,
                    "amount": total_amt,
                    "currency": "INR",
                    "channel": "NEFT",
                    "hop_number": 1,
                    "total_hops": 2,
                    "risk_score": 80
                }
                await _process_and_broadcast_tx(tx1)
                await asyncio.sleep(0.3)

                tx2 = {
                    "tx_id": f"TX-{uuid4().hex[:8].upper()}",
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": hub_id,
                    "receiver_account": out1_id,
                    "amount": amt1,
                    "currency": "INR",
                    "channel": "UPI",
                    "hop_number": 2,
                    "total_hops": 2,
                    "risk_score": 88
                }
                await _process_and_broadcast_tx(tx2)
                await asyncio.sleep(0.3)

                tx3 = {
                    "tx_id": f"TX-{uuid4().hex[:8].upper()}",
                    "timestamp": _now_iso(),
                    "case_id": case_id,
                    "chain_id": chain_id,
                    "sender_account": hub_id,
                    "receiver_account": out2_id,
                    "amount": amt2,
                    "currency": "INR",
                    "channel": "IMPS",
                    "hop_number": 2,
                    "total_hops": 2,
                    "risk_score": 88
                }
                await _process_and_broadcast_tx(tx3)


        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[SENTINEL Simulator] Background loop error: {e}")
        
        await asyncio.sleep(random.uniform(5.0, 8.0))



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json({"event": "connected", "status": "LIVE"})

        # Hydrate newly connected WS client with recent transactions using short-lived DB session
        recent_txs = []
        try:
            async for session in get_db_session():
                repo = get_repository(session=session)
                recent_txs = await repo.get_recent_transactions(limit=20)
                break
        except Exception:
            recent_txs = list(data_store.get("transactions", {}).values())[-20:]

        for transaction in recent_txs:
            tx_event = {
                "event": "tx_scored",
                "tx_id": transaction.get("tx_id", ""),
                "timestamp": transaction.get("timestamp") or _now_iso(),
                "case_id": transaction.get("case_id", ""),
                "risk_score": float(transaction.get("risk_score", 0.0)),
                "amount": float(transaction.get("amount", 0.0)),
                "sender_account": transaction.get("sender_account") or transaction.get("sender_account_id") or "UNKNOWN",
                "receiver_account": transaction.get("receiver_account") or transaction.get("receiver_account_id") or "UNKNOWN",
                "channel": transaction.get("channel", "UPI"),
                "risk_factors": transaction.get("risk_factors", []),
                "threshold": transaction.get("threshold", "LOW"),
                "reason": transaction.get("reason", "Low risk pattern"),
                "full_reason": transaction.get("full_reason", ""),
                "confidence": transaction.get("confidence", "LOW"),
                "ml_score": transaction.get("ml_score", 0),
                "rule_score": transaction.get("rule_score", 0),
                "ml_feature_importance": transaction.get("ml_feature_importance", {}),
                "account_status": (transaction.get("execution_record") or {}).get("resulting_account_state", "ACTIVE"),
                "execution_record": transaction.get("execution_record"),
                "policy_decision": transaction.get("response_decision"),
                "response_decision": transaction.get("response_decision")
            }
            await websocket.send_json(tx_event)


        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
