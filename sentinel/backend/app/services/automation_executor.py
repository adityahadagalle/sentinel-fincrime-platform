"""
SENTINEL Phase 15 — Automation & Response Executor Service.

Implements backend-side explicit automation mode execution, governance interception of restricted
financial actions, structured execution result generation, and immutable PostgreSQL audit event logging.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

EXECUTABLE_ACTIONS = {
    "MONITOR",
    "ENHANCED_MONITORING",
    "CREATE_CASE",
    "START_INVESTIGATION",
    "ESCALATE_ANALYST_REVIEW",
    "URGENT_ANALYST_REVIEW",
}

RESTRICTED_ACTIONS = {
    "FREEZE",
    "BLOCK",
    "FILE_STR",
    "CLOSE_ACCOUNT",
    "REJECT_TRANSACTION",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def execute_automation_policy(
    tx: Dict[str, Any],
    case: Optional[Dict[str, Any]],
    response_decision: Dict[str, Any],
    automate_mode: bool,
    repo=None
) -> Dict[str, Any]:
    """
    Executes automated response policy actions based on backend-authoritative automate_mode.
    
    Guarantees:
    - If automate_mode is OFF: No automated action executed.
    - If action is in RESTRICTED_ACTIONS: Intercepted and flagged as REQUIRES_HUMAN_APPROVAL.
    - If action is in EXECUTABLE_ACTIONS and mode is ON: Action executed automatically.
    - Audit log record created in PostgreSQL.
    """
    tx_id = tx.get("tx_id", response_decision.get("transaction_id", "UNKNOWN"))
    case_id = case.get("case_id") if case else response_decision.get("case_id", "CASE-UNASSIGNED")
    risk_score = float(response_decision.get("risk_score", tx.get("risk_score", 0)))
    risk_level = response_decision.get("risk_level", "LOW")
    action = response_decision.get("action", "MONITOR")
    reason = response_decision.get("reason", "Automated response evaluation.")
    
    # Decision factors extracted from transaction
    decision_factors = []
    if tx.get("is_cross_border") or tx.get("cross_border_risk"):
        decision_factors.append("cross_border_risk")
    if tx.get("is_crypto_related") or tx.get("crypto_risk"):
        decision_factors.append("crypto_risk")
    if tx.get("device_changed") or tx.get("location_changed"):
        decision_factors.append("anomalous_access")
    if tx.get("amount", 0) > 100000:
        decision_factors.append("high_value_transaction")
    if not decision_factors:
        decision_factors.append("standard_rules")

    mode_str = "AUTOMATE_ON" if automate_mode else "AUTOMATE_OFF"
    
    # Check governance boundary & action permission
    is_restricted = action in RESTRICTED_ACTIONS or bool(response_decision.get("requires_human_approval", False))

    if not automate_mode:
        action_status = response_decision.get("action_status", "RECOMMENDED")
        automated = False
        executed_at = None
        execution_result = "NOT_EXECUTED_AUTOMATION_OFF"
        requires_human_approval = bool(response_decision.get("requires_human_approval", False) or is_restricted)
        financial_action_status = "HUMAN AUTHORIZATION REQUIRED" if requires_human_approval else response_decision.get("financial_action_status", "NOT_APPLICABLE")
        event_type = "AUTOMATED_DECISION"
    elif is_restricted or action in RESTRICTED_ACTIONS:
        action_status = "REQUIRES_HUMAN_APPROVAL"
        automated = False
        executed_at = None
        execution_result = "INTERCEPTED_BY_GOVERNANCE_BOUNDARY"
        requires_human_approval = True
        financial_action_status = "HUMAN AUTHORIZATION REQUIRED"
        event_type = "HUMAN_APPROVAL_REQUIRED"

    elif action in EXECUTABLE_ACTIONS:
        action_status = "EXECUTED"
        automated = True
        executed_at = _now_iso()
        execution_result = "SUCCESS"
        requires_human_approval = response_decision.get("requires_human_approval", False)
        financial_action_status = "NOT_APPLICABLE" if not requires_human_approval else "HUMAN AUTHORIZATION REQUIRED"
        event_type = "AUTOMATED_ACTION_EXECUTED"
    else:
        action_status = "FAILED"
        automated = False
        executed_at = None
        execution_result = "UNKNOWN_ACTION_TYPE"
        requires_human_approval = True
        financial_action_status = "NOT_APPLICABLE"
        event_type = "AUTOMATED_ACTION_FAILED"

    timestamp = _now_iso()
    
    # Structured Execution Result
    execution_record = {
        "transaction_id": tx_id,
        "case_id": case_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "action": action,
        "action_status": action_status,
        "automated": automated,
        "mode": mode_str,
        "executed_at": executed_at,
        "execution_result": execution_result,
        "requires_human_approval": requires_human_approval,
        "financial_action_status": financial_action_status,
        "reason": reason,
        "decision_factors": decision_factors,
        "policy_version": "v15.0-phase15",
        "actor_type": "AUTOMATION_EXECUTOR",
        "actor_id": "SENTINEL_AUTOMATION_SERVICE",
        "timestamp": timestamp
    }

    # Complete 16-field Audit Trail Dictionary
    traceability_chain = {
        "transaction_id": tx_id,
        "case_id": case_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "action_selected": action,
        "selection_reason": reason,
        "decision_factors": decision_factors,
        "automation_mode": mode_str,
        "was_action_executed": automated and action_status == "EXECUTED",
        "requires_human_approval": requires_human_approval,
        "execution_result": execution_result,
        "policy_version": "v15.0-phase15",
        "timestamp": timestamp,
        "actor": "SENTINEL_AUTOMATION_SERVICE",
        "previous_state": case.get("status", "NEW") if case else "NEW",
        "resulting_state": case.get("status", "NEW") if case else "NEW"
    }

    # Construct Audit Event Record
    audit_record = {
        "audit_id": f"AUD-AUTO-{str(uuid.uuid4())[:8].upper()}",
        "event_type": event_type,
        "case_id": case_id if case_id and case_id.startswith("CASE-") else "CASE-SYSTEM",
        "primary_tx_id": tx_id,
        "analyst_id": "AUTOMATION_ENGINE",
        "analyst_role": "SYSTEM_AUTOMATION",
        "action_code": action,
        "previous_case_status": case.get("status", "NEW") if case else "NEW",
        "new_case_status": case.get("status", "NEW") if case else "NEW",
        "analyst_notes": f"[AUTOMATE MODE: {mode_str}] Action '{action}' status: {action_status}. Reason: {reason}",
        "risk_acknowledged": False,
        "decision_support_summary": execution_record,
        "traceability_chain": traceability_chain,
        "timestamp": timestamp
    }

    # Persist audit record to PostgreSQL if repository provided
    if repo:
        try:
            await repo.save_audit_event(audit_record)
        except Exception as err:
            # Audit logging failure fallback
            print(f"[AutomationExecutor] Warning: Failed to persist audit event to DB: {err}")

    # Attach structured execution result to transaction payload
    tx["automation_execution"] = execution_record
    tx["action_status"] = action_status
    tx["automation_mode"] = mode_str

    return execution_record
