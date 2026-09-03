"""
SENTINEL Intelligence API Routes (Phases 3 & 9)

Endpoints:
  POST /intelligence/analyze   — run Qwen investigation analysis
  GET  /intelligence/health    — Ollama reachability check

Architecture constraint:
  Qwen output NEVER flows into policy engine or action executor.
  AI analysis is advisory only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.ollama_service import ollama_service, IntelligenceResult, OLLAMA_MODEL
from app.core.data_store import data_store
from app.engines.graph_engine import build_investigation_graph
from app.repositories.base import AbstractCaseRepository
from app.repositories.dependencies import get_repository
from app.services.evidence_agent import collect_evidence_for_case

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── INVESTIGATION CONTEXT BUILDER (Phase 10 data boundary & 5-Agent Synthesis) ─
async def _build_investigation_context(
    case_id: str,
    store: dict[str, Any],
    repo: Optional[AbstractCaseRepository] = None,
) -> dict[str, Any]:
    """
    Construct a clean, sanitized investigation context dict for Qwen.
    Incorporates the actual persisted outputs of the 5-stage deterministic pipeline:
      1. EVIDENCE (Evidence Collection)
      2. CONTEXTUAL (Contextual Investigation)
      3. REGULATORY (Regulatory Risk Assessment)
      4. AUDIT_EXPLANATION (Audit Explanation)
      5. DECISION_SUPPORT (Analyst Decision Support)

    SECURITY: Only investigation-relevant data is included.
    Never includes: passwords, tokens, secrets, DATABASE_URL, env vars,
    or any unrelated internal state.
    """
    from app.services.investigation_orchestrator import investigation_orchestrator

    case = None
    if repo is not None:
        try:
            case = await repo.get_case(case_id)
        except Exception:
            case = None

    if not case:
        cases = store.get("cases", {})
        case = cases.get(case_id)

    if not case:
        return {}

    # ── Graph / network data ──────────────────────────────────────────────────
    graph = build_investigation_graph(case_id, store)
    nodes: list[dict] = graph.get("nodes", [])
    edges: list[dict] = graph.get("edges", [])

    # ── Network summary ───────────────────────────────────────────────────────
    mule_nodes = [n for n in nodes if n.get("node_type") == "mule" or n.get("account_type") == "MULE"]
    exit_nodes = [
        n for n in nodes
        if n.get("node_type") in ("cashout", "crypto", "merchant") or n.get("account_type") == "DESTINATION"
    ]
    suspicious_edges = [e for e in edges if e.get("suspicious")]
    total_value = sum(float(e.get("amount", 0)) for e in edges)
    max_hop = max((int(e.get("hop_number", 1)) for e in edges), default=1)

    # ── Primary transaction (safe fields only) ────────────────────────────────
    primary_tx_id = case.get("primary_tx_id", "")
    tx_store = store.get("transactions", {})
    primary_tx = tx_store.get(primary_tx_id, {})

    safe_tx: dict[str, Any] = {}
    if primary_tx:
        safe_tx = {
            "tx_id": primary_tx.get("tx_id", ""),
            "amount": primary_tx.get("amount", 0),
            "channel": primary_tx.get("channel", ""),
            "risk_score": primary_tx.get("risk_score", 0),
            "reason": primary_tx.get("reason", ""),
            "timestamp": primary_tx.get("timestamp", ""),
        }

    # ── Detected patterns (from case context) ─────────────────────────────────
    detected_patterns: list[str] = []
    topology = case.get("topology_type", "UNKNOWN")
    if topology != "UNKNOWN":
        detected_patterns.append(f"Network topology: {topology}")
    if len(mule_nodes) > 0:
        detected_patterns.append(f"Mule cascade: {len(mule_nodes)} mule account(s) detected")
    if suspicious_edges:
        detected_patterns.append(f"Suspicious flows: {len(suspicious_edges)} flagged transaction(s)")
    if max_hop >= 3:
        detected_patterns.append(f"Multi-hop layering: {max_hop} hops detected")
    chain_ids = {e.get("chain_id") for e in edges if e.get("chain_id")}
    if len(chain_ids) > 1:
        detected_patterns.append(f"Multiple transaction chains: {len(chain_ids)} chains identified")

    # ── Entity list (IDs only, no balance/PII) ────────────────────────────────
    entity_lines: list[str] = []
    for n in nodes:
        nid = n.get("account_id") or n.get("id", "")
        ntype = n.get("node_type") or n.get("account_type") or "UNKNOWN"
        layer = n.get("layer", 0)
        entity_lines.append(f"{nid} [{ntype.upper()}] — Layer {layer}")

    # ── Transaction flow descriptions ─────────────────────────────────────────
    flow_lines: list[str] = []
    for e in edges[:20]:  # Cap at 20 to avoid bloating the prompt
        src = e.get("source") or e.get("from", "?")
        tgt = e.get("target") or e.get("to", "?")
        amt = float(e.get("amount", 0))
        hop = e.get("hop_number", "?")
        ch = e.get("channel", "")
        susp = " [SUSPICIOUS]" if e.get("suspicious") else ""
        flow_lines.append(f"{src} → {tgt}  ₹{amt:,.0f}  {ch}  Hop {hop}{susp}")

    # ── Policy decision summary (context only, already executed) ──────────────
    policy_summary: str | None = None
    last_action = None
    action_log = case.get("actionLog") or case.get("actions_taken") or []
    if action_log:
        last_action = action_log[-1] if isinstance(action_log, list) else None
    if last_action and isinstance(last_action, dict):
        policy_summary = (
            f"Last autonomous action: {last_action.get('action_type', '')} "
            f"on {last_action.get('target_id', '')} "
            f"at {last_action.get('timestamp', '')}"
        )

    # ── 5-Stage Deterministic Investigation Status & Reports ──────────────────
    stage_names = ["EVIDENCE", "CONTEXTUAL", "REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"]
    inv_status: dict[str, str] = {s.lower(): "NOT_STARTED" for s in stage_names}
    inv_reports: dict[str, Any] = {}

    # 1. Check repo if provided
    if repo is not None:
        try:
            run = await repo.get_active_investigation_run(case_id) or await repo.get_latest_investigation_run(case_id)
            if run and isinstance(run, dict):
                stage_states = run.get("stages", {})
                for stg in stage_names:
                    s_info = stage_states.get(stg, {})
                    if s_info.get("status"):
                        inv_status[stg.lower()] = s_info["status"]

            for stg in stage_names:
                rpt_obj = await repo.get_investigation_report(case_id, stg)
                if rpt_obj and isinstance(rpt_obj.get("report_data"), dict):
                    inv_reports[stg.lower()] = rpt_obj["report_data"]
                    inv_status[stg.lower()] = "COMPLETED"
        except Exception:
            pass

    # 2. Check active in-memory or persisted investigation runs in store
    active_run = None
    try:
        active_run = investigation_orchestrator._active_investigations.get(case_id)
    except Exception:
        pass

    if not active_run:
        for r in store.get("investigation_runs", {}).values():
            if isinstance(r, dict) and r.get("case_id") == case_id:
                active_run = r
                break

    if active_run and isinstance(active_run, dict):
        stages_dict = active_run.get("stages", {})
        for stg in stage_names:
            stg_info = stages_dict.get(stg, {})
            status = stg_info.get("status")
            if status and inv_status.get(stg.lower()) == "NOT_STARTED":
                inv_status[stg.lower()] = status
            if status == "COMPLETED" and stg_info.get("output") and stg.lower() not in inv_reports:
                inv_reports[stg.lower()] = stg_info["output"]
                inv_status[stg.lower()] = "COMPLETED"

    # 3. Check store for persisted investigation reports
    store_reports = store.get("investigation_reports", {})
    if isinstance(store_reports, dict):
        for stg in stage_names:
            stg_lower = stg.lower()
            if stg_lower in inv_reports:
                continue

            # Check key format: f"{case_id}::{stg}"
            key = f"{case_id}::{stg}"
            rpt_rec = store_reports.get(key)
            if rpt_rec and isinstance(rpt_rec, dict) and rpt_rec.get("report_data"):
                inv_reports[stg_lower] = rpt_rec["report_data"]
                inv_status[stg_lower] = "COMPLETED"
            else:
                for r in store_reports.values():
                    if isinstance(r, dict) and r.get("case_id") == case_id and r.get("report_type") == stg:
                        if r.get("report_data"):
                            inv_reports[stg_lower] = r["report_data"]
                            inv_status[stg_lower] = "COMPLETED"
                            break

    # 4. Check case object for attached reports or stages
    case_stages = case.get("stages") or case.get("investigation_stages") or []
    if isinstance(case_stages, list):
        for s in case_stages:
            if isinstance(s, dict):
                stg_name = str(s.get("stage", "")).lower()
                if stg_name in inv_status:
                    if s.get("status") and inv_status[stg_name] == "NOT_STARTED":
                        inv_status[stg_name] = s["status"]
                    if s.get("output") and stg_name not in inv_reports:
                        inv_reports[stg_name] = s["output"]
                        inv_status[stg_name] = "COMPLETED"

    # 5. Deterministic fallback for EVIDENCE collection stage if report is missing
    if "evidence" not in inv_reports:
        if case.get("evidence") and isinstance(case["evidence"], dict) and case["evidence"].get("evidence"):
            inv_reports["evidence"] = case["evidence"]
            inv_status["evidence"] = "COMPLETED"
        else:
            try:
                ev_pkg = collect_evidence_for_case(case_id, store)
                if ev_pkg and ev_pkg.get("found") and ev_pkg.get("evidence"):
                    inv_reports["evidence"] = ev_pkg
                    inv_status["evidence"] = "COMPLETED"
            except Exception:
                pass

    # Ensure consistency between loaded reports and status
    for stg_lower in inv_status:
        if stg_lower in inv_reports and inv_status[stg_lower] in ("NOT_STARTED", "PENDING"):
            inv_status[stg_lower] = "COMPLETED"

    # Stage synthesis tracking
    synthesized_stages = [
        s.upper() for s in stage_names
        if s.lower() in inv_reports and inv_status.get(s.lower()) == "COMPLETED"
    ]
    missing_stages = [
        s.upper() for s in stage_names
        if s.upper() not in synthesized_stages
    ]

    return {
        "case_id": case_id,
        "risk_level": str(case.get("risk_level", "UNKNOWN")),
        "risk_score": float(case.get("risk_score", case.get("risk_level", 0)) or 0),
        "topology_type": topology,
        "primary_transaction": safe_tx or None,
        "network_summary": {
            "total_nodes": len(nodes),
            "total_flows": len(edges),
            "mule_count": len(mule_nodes),
            "exit_count": len(exit_nodes),
            "suspicious_flows": len(suspicious_edges),
            "total_value_inr": round(total_value, 2),
            "max_hops": max_hop,
        },
        "entities": entity_lines,
        "transaction_flows": flow_lines,
        "detected_patterns": detected_patterns,
        "policy_decision_summary": policy_summary,
        "investigation_status": inv_status,
        "investigation_reports": inv_reports,
        "synthesized_stages": synthesized_stages,
        "missing_stages": missing_stages,
    }


# ── REQUEST / RESPONSE MODELS ─────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    case_id: str = Field(..., min_length=1, max_length=128)


class HealthResponse(BaseModel):
    available: bool
    provider: str = "ollama"
    model: str = OLLAMA_MODEL


# ── ROUTES ────────────────────────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
async def intelligence_health() -> HealthResponse:
    """
    Phase 9: Lightweight Ollama reachability check.
    Application startup is NOT blocked if Ollama is unavailable.
    """
    available = ollama_service.is_available()
    return HealthResponse(available=available)


@router.post("/analyze", response_model=IntelligenceResult)
async def analyze_case(
    req: AnalyzeRequest,
    repo: AbstractCaseRepository = Depends(get_repository),
) -> IntelligenceResult:
    """
    Phase 3 & 9: Run Qwen advisory investigation analysis for the given case.

    Data flow:
      Case store / DB → Context builder (5-Agent Reports) → Qwen → Structured advisory output

    NEVER flows into:
      Policy engine / Action executor / Freeze logic / Audit mutation

    Returns IntelligenceResult with status:
      ready       — analysis available
      unavailable — Ollama not running
      timeout     — model took too long
      error       — unexpected failure
      no_data     — case not found or no graph data
    """
    case_id = req.case_id

    # Validate case exists in repo or store
    case_exists = False
    if repo is not None:
        try:
            case_obj = await repo.get_case(case_id)
            if case_obj:
                case_exists = True
        except Exception:
            pass

    if not case_exists:
        case_exists = case_id in data_store.get("cases", {})

    if not case_exists:
        return IntelligenceResult(
            status="no_data",
            case_id=case_id,
            error_detail=f"Case {case_id!r} not found in SENTINEL data store.",
        )

    # Build sanitized context with the 5 deterministic investigation reports
    ctx = await _build_investigation_context(case_id, data_store, repo=repo)
    if not ctx:
        return IntelligenceResult(
            status="no_data",
            case_id=case_id,
            error_detail="Insufficient investigation data to build context.",
        )

    # Delegate to Ollama service (advisory only)
    result = ollama_service.analyze(ctx, case_id=case_id)
    return result
