"""
SENTINEL Phase 16 — Deterministic Autonomous Policy Engine.

Enforces non-negotiable safety rules and produces structured policy decisions.
The LLM / Hybrid Scoring Engine recommendation is NEVER the final authorization authority.
The policy engine deterministically evaluates transaction risk score, risk level, case state,
action eligibility, and automation mode state.
"""

from typing import Dict, Any, Optional, Set

SUPPORTED_ACTIONS: Set[str] = {
    "MONITOR",
    "ENHANCED_MONITORING",
    "ESCALATE_ANALYST_REVIEW",
    "FREEZE",
    "BLOCK",
    "FILE_STR",
    "CLOSE_ACCOUNT",
    "REJECT_TRANSACTION"
}

VALID_RISK_LEVELS: Set[str] = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
INVALID_CASE_STATUSES: Set[str] = {"CLOSED_CONFIRMED_FRAUD", "CLOSED_FALSE_POSITIVE"}


def evaluate_autonomous_policy(
    tx: Optional[Dict[str, Any]],
    case: Optional[Dict[str, Any]],
    automate_mode: bool
) -> Dict[str, Any]:
    """
    Evaluates transaction risk signals and produces a deterministic policy decision.
    
    Returns structured decision:
    {
      "decision": "EXECUTE" | "DO_NOT_EXECUTE" | "REJECT",
      "action": str,
      "risk_score": float,
      "risk_level": str,
      "reason": str,
      "policy_rule_id": str,
      "automation_enabled": bool
    }
    """
    # Rule 1: Fail Closed on missing or invalid transaction payload
    if not tx or not isinstance(tx, dict):
        return {
            "decision": "REJECT",
            "action": "NONE",
            "risk_score": 0.0,
            "risk_level": "UNKNOWN",
            "reason": "Missing or invalid transaction payload",
            "policy_rule_id": "POL-ERR-NO-TX",
            "automation_enabled": automate_mode
        }

    # Rule 2: Fail Closed on missing risk score
    risk_score_raw = tx.get("risk_score")
    if risk_score_raw is None or not isinstance(risk_score_raw, (int, float)):
        return {
            "decision": "REJECT",
            "action": "NONE",
            "risk_score": 0.0,
            "risk_level": "UNKNOWN",
            "reason": "Missing or invalid risk score",
            "policy_rule_id": "POL-ERR-NO-SCORE",
            "automation_enabled": automate_mode
        }
    
    try:
        risk_score = float(risk_score_raw)
    except (ValueError, TypeError):
        return {
            "decision": "REJECT",
            "action": "NONE",
            "risk_score": 0.0,
            "risk_level": "UNKNOWN",
            "reason": "Risk score conversion error",
            "policy_rule_id": "POL-ERR-SCORE-CONV",
            "automation_enabled": automate_mode
        }

    # Determine risk level
    if risk_score >= 85:
        risk_level = "CRITICAL"
    elif risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    elif risk_score >= 0:
        risk_level = "LOW"
    else:
        risk_level = "UNKNOWN"

    # Rule 3: Fail Closed on invalid risk level
    if risk_level not in VALID_RISK_LEVELS:
        return {
            "decision": "REJECT",
            "action": "NONE",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reason": f"Invalid risk level '{risk_level}'",
            "policy_rule_id": "POL-ERR-INVALID-LEVEL",
            "automation_enabled": automate_mode
        }

    # Extract proposed action
    requested_action = tx.get("requested_action") or tx.get("action")
    if not requested_action:
        if risk_level == "CRITICAL":
            requested_action = "FREEZE"
        elif risk_level == "HIGH":
            requested_action = "ESCALATE_ANALYST_REVIEW"
        elif risk_level == "MEDIUM":
            requested_action = "ENHANCED_MONITORING"
        else:
            requested_action = "MONITOR"

    # Rule 4: Fail Closed on unknown action code
    if requested_action not in SUPPORTED_ACTIONS:
        return {
            "decision": "REJECT",
            "action": requested_action,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reason": f"Unknown or unsupported action code '{requested_action}'",
            "policy_rule_id": "POL-ERR-UNKNOWN-ACTION",
            "automation_enabled": automate_mode
        }

    # Rule 5: Fail Closed on closed/invalid case state
    if case and case.get("status") in INVALID_CASE_STATUSES:
        return {
            "decision": "REJECT",
            "action": requested_action,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reason": f"Case state '{case.get('status')}' is closed and invalid for new autonomous actions",
            "policy_rule_id": "POL-ERR-INVALID-CASE-STATE",
            "automation_enabled": automate_mode
        }

    # Rule 6: Mode OFF -> DO_NOT_EXECUTE (for autonomous actions)
    if not automate_mode and requested_action != "FREEZE":
        return {
            "decision": "DO_NOT_EXECUTE",
            "execution_status": "NOT_EXECUTED",
            "action": requested_action,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reason": "Automate Mode is OFF. Autonomous execution disabled by policy.",
            "policy_rule_id": "POL-MODE-OFF",
            "automation_enabled": False
        }

    # Rule 7: Deterministic Policy Rule Mapping
    if risk_level == "CRITICAL":
        policy_rule_id = "POL-CRITICAL-001"
        reason = f"Critical risk score {risk_score:.1f} >= 85 triggers deterministic simulated action '{requested_action}'."
    elif risk_level == "HIGH":
        policy_rule_id = "POL-HIGH-001"
        reason = f"High risk score {risk_score:.1f} >= 70 triggers deterministic simulated escalation."
    elif risk_level == "MEDIUM":
        policy_rule_id = "POL-MEDIUM-001"
        reason = f"Medium risk score {risk_score:.1f} >= 40 triggers deterministic enhanced monitoring."
    else:
        policy_rule_id = "POL-MONITOR-001"
        reason = f"Low risk score {risk_score:.1f} < 40 triggers deterministic standard monitoring."

    # FREEZE requires explicit operator interaction even when policy authorizes it
    if requested_action == "FREEZE":
        return {
            "decision": "EXECUTE",
            "execution_status": "REQUIRES_OPERATOR_ACTION",
            "action": "FREEZE",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reason": reason,
            "policy_rule_id": policy_rule_id,
            "automation_enabled": automate_mode
        }

    return {
        "decision": "EXECUTE",
        "execution_status": "EXECUTE",
        "action": requested_action,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason": reason,
        "policy_rule_id": policy_rule_id,
        "automation_enabled": True
    }

