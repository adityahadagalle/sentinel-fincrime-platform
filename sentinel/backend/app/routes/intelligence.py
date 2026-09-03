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
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ollama_service import ollama_service, IntelligenceResult, OLLAMA_MODEL
from app.core.data_store import data_store
from app.engines.graph_engine import build_investigation_graph

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── INVESTIGATION CONTEXT BUILDER (Phase 10 data boundary) ───────────────────
def _build_investigation_context(
    case_id: str,
    store: dict[str, Any],
) -> dict[str, Any]:
    """
    Construct a clean, sanitized investigation context dict for Qwen.

    SECURITY: Only investigation-relevant data is included.
    Never includes: passwords, tokens, secrets, DATABASE_URL, env vars,
    or any unrelated internal state.
    """
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
async def analyze_case(req: AnalyzeRequest) -> IntelligenceResult:
    """
    Phase 3: Run Qwen advisory investigation analysis for the given case.

    Data flow:
      Case store → Context builder → Qwen → Structured advisory output

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

    # Validate case exists
    if case_id not in data_store.get("cases", {}):
        return IntelligenceResult(
            status="no_data",
            case_id=case_id,
            error_detail=f"Case {case_id!r} not found in SENTINEL data store.",
        )

    # Build sanitized context (Phase 10 data boundary)
    ctx = _build_investigation_context(case_id, data_store)
    if not ctx:
        return IntelligenceResult(
            status="no_data",
            case_id=case_id,
            error_detail="Insufficient investigation data to build context.",
        )

    # Delegate to Ollama service (advisory only)
    result = ollama_service.analyze(ctx, case_id=case_id)
    return result
