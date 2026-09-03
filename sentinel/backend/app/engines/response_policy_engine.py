"""
SENTINEL Phase 14 — Automated Response Policy Engine.

Evaluates scored transactions and determines appropriate automated operational responses
while enforcing strict governance boundaries (forbidden autonomous financial actions).
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Governance Boundary: Actions strictly prohibited from autonomous execution
FORBIDDEN_AUTONOMOUS_ACTIONS = {
    "FREEZE",
    "BLOCK",
    "FILE_STR",
    "CLOSE_ACCOUNT",
    "REJECT_TRANSACTION"
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def evaluate_response_policy(
    tx: Dict[str, Any],
    case: Optional[Dict[str, Any]] = None,
    investigation_run: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates a scored transaction and computes a deterministic response decision.

    Idempotency: If the transaction already contains a valid response decision,
    reuses the existing decision unless updated by an active case/investigation.
    """
    # 1. Idempotency Check
    existing_decision = tx.get("response_decision")
    if existing_decision and isinstance(existing_decision, dict) and existing_decision.get("action"):
        # If existing decision is valid, preserve it while updating case/run links if available
        if case and not existing_decision.get("case_id"):
            existing_decision["case_id"] = case.get("case_id")
        if investigation_run and not existing_decision.get("investigation_run_id"):
            existing_decision["investigation_run_id"] = investigation_run.get("run_id")
        return existing_decision

    tx_id = tx.get("tx_id", "")
    score = float(tx.get("risk_score", 0.0))
    reason = tx.get("reason") or tx.get("top_reason") or "Standard risk evaluation"

    # 2. Risk Classification & Action Mapping
    if score >= 85:
        risk_level = "CRITICAL"
        action = "URGENT_ANALYST_REVIEW"
        action_status = "STARTED" if case else "QUEUED"
        requires_human_approval = True
        financial_action_status = "HUMAN AUTHORIZATION REQUIRED"
        default_reason = "Critical multi-vector fraud indicators detected. Urgent case creation and investigation started."
    elif score >= 70:
        risk_level = "HIGH"
        action = "ESCALATE_ANALYST_REVIEW"
        action_status = "STARTED" if case else "QUEUED"
        requires_human_approval = True
        financial_action_status = "HUMAN AUTHORIZATION REQUIRED"
        default_reason = "High-risk indicators detected. Case escalated for analyst review and investigation."
    elif score >= 40:
        risk_level = "MEDIUM"
        action = "ENHANCED_MONITORING"
        action_status = "STARTED" if case else "COMPLETED"
        requires_human_approval = False
        financial_action_status = "NOT_APPLICABLE"
        default_reason = "Moderate risk signals detected. Enhanced account and transaction monitoring initiated."
    else:
        risk_level = "LOW"
        action = "MONITOR"
        action_status = "COMPLETED"
        requires_human_approval = False
        financial_action_status = "NOT_APPLICABLE"
        default_reason = "Low risk pattern detected. Standard transaction monitoring active."

    # 3. Governance Boundary Intercept: Check for forbidden autonomous financial actions
    requested_action = (tx.get("requested_action") or tx.get("action") or "").upper()
    if requested_action in FORBIDDEN_AUTONOMOUS_ACTIONS:
        action = requested_action
        action_status = "REQUIRES_HUMAN_APPROVAL"
        requires_human_approval = True
        financial_action_status = "HUMAN AUTHORIZATION REQUIRED"
        default_reason = f"Action {requested_action} requires explicit human compliance analyst authorization."

    case_id = (case.get("case_id") if case else None) or tx.get("case_id")
    run_id = (investigation_run.get("run_id") if investigation_run else None) or tx.get("investigation_run_id")

    # 4. Construct Response Decision Object
    response_decision = {
        "transaction_id": tx_id,
        "tx_id": tx_id,
        "risk_score": score,
        "risk_level": risk_level,
        "action": action,
        "action_status": action_status,
        "reason": reason or default_reason,
        "automated": True,
        "requires_human_approval": requires_human_approval,
        "financial_action_status": financial_action_status,
        "case_id": case_id,
        "investigation_run_id": run_id,
        "timestamp": _now_iso()
    }

    # Attach response decision to transaction dictionary
    tx["response_decision"] = response_decision
    tx["action"] = action
    tx["action_status"] = action_status
    tx["requires_human_approval"] = requires_human_approval
    tx["financial_action_status"] = financial_action_status

    return response_decision
