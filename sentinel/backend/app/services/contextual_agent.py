"""
Contextual Investigation Agent for SENTINEL (Phase 2).

Responsibility:
- Consumes Phase 1 structured Evidence Packages (`collect_evidence`).
- Does NOT recollect evidence or query underlying stores directly.
- Evaluates transaction, account, counterparty, behavioral baseline, velocity, and graph topology evidence together.
- Identifies multi-signal contextual fraud patterns (Rapid Structuring, Mule Account Drainage, Pass-Through Activity, Multi-Hop Propagation, First-Time High-Value Counterparty, Behavioral Escalation, Cross-Border/Telemetry Risk).
- Produces deterministic, machine-readable contextual investigation reports.
- Maintains strict evidence traceability (every finding references supporting Evidence IDs: `EV-XXX`).
- Does NOT invent non-existent KYC, sanctions, criminal databases, or fictitious external intelligence.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def investigate_context(evidence_package: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Core entrypoint for Phase 2 Contextual Investigation Agent.
    Consumes a Phase 1 evidence package dictionary and returns a Contextual Investigation Report.
    """
    if not evidence_package or not isinstance(evidence_package, dict) or not evidence_package.get("found"):
        target_id = evidence_package.get("target_id", "") if isinstance(evidence_package, dict) else ""
        return {
            "found": False,
            "status": "INSUFFICIENT_DATA",
            "target_id": target_id,
            "case_id": evidence_package.get("case_id") if isinstance(evidence_package, dict) else None,
            "primary_tx_id": evidence_package.get("primary_tx_id") if isinstance(evidence_package, dict) else None,
            "investigated_at": _now_iso(),
            "summary": {
                "contextual_severity": "UNKNOWN",
                "confidence": 0.0,
                "pattern_count": 0
            },
            "behavioral_analysis": {},
            "counterparty_analysis": {},
            "graph_analysis": {},
            "patterns": [],
            "contextual_findings": [
                {
                    "id": "CTX-000",
                    "type": "system",
                    "severity": "INFO",
                    "finding": "Insufficient evidence available in Phase 1 evidence package to perform contextual investigation.",
                    "supporting_evidence_ids": []
                }
            ]
        }

    target_id = evidence_package.get("target_id", "")
    case_id = evidence_package.get("case_id")
    primary_tx_id = evidence_package.get("primary_tx_id")
    evidence_list = evidence_package.get("evidence", [])

    if not isinstance(evidence_list, list):
        evidence_list = []

    # Map evidence items by type and category for clean lookup
    evidence_by_id = {ev["id"]: ev for ev in evidence_list if isinstance(ev, dict) and "id" in ev}
    evidence_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for ev in evidence_list:
        if isinstance(ev, dict) and "type" in ev:
            evidence_by_type.setdefault(ev["type"], []).append(ev)

    # Helper to extract evidence IDs of given types/categories
    def _find_evidence_ids(types: List[str]) -> List[str]:
        matched_ids = []
        for ev in evidence_list:
            if isinstance(ev, dict) and ev.get("type") in types and "id" in ev:
                matched_ids.append(ev["id"])
        return matched_ids

    # Extract Key Facts directly from Phase 1 Package (Zero Recalculation)
    tx_ev_list = evidence_by_type.get("transaction", [])
    tx_ev = tx_ev_list[0] if tx_ev_list else {}
    tx_data = tx_ev.get("data", {}) if isinstance(tx_ev, dict) else {}

    baseline_ev_list = [
        ev for ev in evidence_list
        if isinstance(ev, dict) and ev.get("type") == "historical_behavior" and "Baseline" in ev.get("category", "")
    ]
    baseline_ev = baseline_ev_list[0] if baseline_ev_list else {}
    baseline_data = baseline_ev.get("data", {}) if isinstance(baseline_ev, dict) else {}

    counterparty_ev_list = [
        ev for ev in evidence_list
        if isinstance(ev, dict) and ev.get("type") == "historical_behavior" and "Counterparty" in ev.get("category", "")
    ]
    counterparty_ev = counterparty_ev_list[0] if counterparty_ev_list else {}
    counterparty_data = counterparty_ev.get("data", {}) if isinstance(counterparty_ev, dict) else {}

    telemetry_ev_list = evidence_by_type.get("behavioral_telemetry", [])
    telemetry_ev = telemetry_ev_list[0] if telemetry_ev_list else {}
    telemetry_data = telemetry_ev.get("data", {}) if isinstance(telemetry_ev, dict) else {}

    graph_ev_list = evidence_by_type.get("graph_network", [])
    graph_ev = graph_ev_list[0] if graph_ev_list else {}
    graph_data = graph_ev.get("data", {}) if isinstance(graph_ev, dict) else {}

    chain_ev_list = evidence_by_type.get("related_activity", [])
    chain_ev = chain_ev_list[0] if chain_ev_list else {}
    chain_data = chain_ev.get("data", {}) if isinstance(chain_ev, dict) else {}

    case_overview_list = evidence_by_type.get("case_overview", [])
    case_overview_ev = case_overview_list[0] if case_overview_list else {}
    case_overview_data = case_overview_ev.get("data", {}) if isinstance(case_overview_ev, dict) else {}

    # Extract parsed metrics directly from Phase 1
    amount = float(tx_data.get("amount", case_overview_data.get("risk_level", 0.0)))
    deviation_ratio = float(baseline_data.get("deviation_ratio", 0.0))
    is_first_interaction = bool(counterparty_data.get("is_first_interaction", False))
    prior_tx_count = int(counterparty_data.get("prior_transactions_count", 0))
    active_flags = telemetry_data.get("active_flags", []) if isinstance(telemetry_data.get("active_flags"), list) else []
    active_flag_keys = {item.get("flag") for item in active_flags if isinstance(item, dict)}

    chain_depth = int(graph_data.get("chain_depth", chain_data.get("chain_depth", 0)))
    total_nodes = int(graph_data.get("nodes_count", len(chain_data.get("account_chain", []))))
    total_chain_txs = int(chain_data.get("total_transactions", 1))
    frozen_accounts = graph_data.get("frozen_accounts", [])
    withdrawn_accounts = graph_data.get("withdrawn_accounts", [])

    risk_score = float(tx_data.get("risk_score", case_overview_data.get("risk_level", 0.0)))

    # --- 1. Behavioral & Baseline Analysis ---
    behavioral_analysis = {
        "baseline_deviation": {
            "detected": deviation_ratio >= 1.5,
            "ratio": deviation_ratio,
            "monthly_average": float(baseline_data.get("avg_monthly_tx_amount", 0.0)),
            "evidence_ids": [baseline_ev["id"]] if baseline_ev.get("id") else []
        },
        "velocity": {
            "detected": ("velocity_flag" in active_flag_keys) or (total_chain_txs >= 3),
            "linked_transactions_count": total_chain_txs,
            "evidence_ids": [ev["id"] for ev in [chain_ev, telemetry_ev] if ev.get("id")]
        }
    }

    # --- 2. Counterparty Analysis ---
    counterparty_analysis = {
        "first_time_counterparty": is_first_interaction,
        "prior_transaction_count": prior_tx_count,
        "sender_account": counterparty_data.get("sender_account", tx_data.get("sender_account", "")),
        "receiver_account": counterparty_data.get("receiver_account", tx_data.get("receiver_account", "")),
        "evidence_ids": [counterparty_ev["id"]] if counterparty_ev.get("id") else []
    }

    # --- 3. Graph Analysis ---
    graph_analysis = {
        "propagation_depth": chain_depth,
        "connected_entities_count": total_nodes,
        "frozen_accounts_count": len(frozen_accounts),
        "withdrawn_accounts_count": len(withdrawn_accounts),
        "evidence_ids": [graph_ev["id"]] if graph_ev.get("id") else []
    }

    # --- 4. Deterministic Pattern Matching Layer ---
    patterns: List[Dict[str, Any]] = []

    def _eval_pattern(
        pattern_id: str,
        pattern_name: str,
        matched: bool,
        confidence: float,
        severity: str,
        description: str,
        supporting_ids: List[str]
    ):
        if matched:
            patterns.append({
                "pattern_id": pattern_id,
                "pattern_name": pattern_name,
                "matched": True,
                "confidence": round(confidence, 2),
                "severity": severity,
                "description": description,
                "supporting_evidence_ids": supporting_ids
            })

    # Pattern 1: RAPID_STRUCTURING
    is_rapid = ("velocity_flag" in active_flag_keys) or (total_chain_txs >= 3)
    _eval_pattern(
        pattern_id="RAPID_STRUCTURING",
        pattern_name="Rapid Structuring Pattern",
        matched=is_rapid,
        confidence=0.88 if total_chain_txs >= 3 else 0.75,
        severity="HIGH" if total_chain_txs >= 3 else "MEDIUM",
        description="Multiple transactions or fund transfers structured across linked accounts in short sequence.",
        supporting_ids=_find_evidence_ids(["related_activity", "behavioral_telemetry", "transaction"])
    )

    # Pattern 2: MULE_ACCOUNT_DRAINAGE
    is_mule_drain = len(withdrawn_accounts) > 0 or (chain_depth >= 2 and risk_score >= 70)
    _eval_pattern(
        pattern_id="MULE_ACCOUNT_DRAINAGE",
        pattern_name="Mule Account Drainage",
        matched=is_mule_drain,
        confidence=0.92 if len(withdrawn_accounts) > 0 else 0.82,
        severity="HIGH",
        description="Funds rapidly propagating into mule accounts for immediate off-platform withdrawal or drainage.",
        supporting_ids=_find_evidence_ids(["graph_network", "related_activity", "transaction"])
    )

    # Pattern 3: PASS_THROUGH_ACTIVITY
    is_pass_through = (chain_depth >= 2) or (total_chain_txs >= 2 and total_nodes >= 3)
    _eval_pattern(
        pattern_id="PASS_THROUGH_ACTIVITY",
        pattern_name="Pass-Through Account Layering",
        matched=is_pass_through,
        confidence=0.85,
        severity="HIGH" if chain_depth >= 2 else "MEDIUM",
        description="Layering pattern detected where funds pass through intermediary accounts without balance retention.",
        supporting_ids=_find_evidence_ids(["related_activity", "graph_network"])
    )

    # Pattern 4: MULTI_HOP_PROPAGATION
    is_multihop = chain_depth >= 1 and total_nodes >= 3
    _eval_pattern(
        pattern_id="MULTI_HOP_PROPAGATION",
        pattern_name="Multi-Hop Network Propagation",
        matched=is_multihop,
        confidence=0.89,
        severity="HIGH" if chain_depth >= 2 else "MEDIUM",
        description="Fund flow propagating through a multi-hop entity network involving 3 or more accounts.",
        supporting_ids=_find_evidence_ids(["graph_network", "related_activity"])
    )

    # Pattern 5: FIRST_TIME_HIGH_VALUE_COUNTERPARTY
    is_first_high_val = is_first_interaction and (amount >= 50000 or deviation_ratio >= 1.5 or risk_score >= 60)
    _eval_pattern(
        pattern_id="FIRST_TIME_HIGH_VALUE_COUNTERPARTY",
        pattern_name="First-Time High-Value Counterparty Transfer",
        matched=is_first_high_val,
        confidence=0.86,
        severity="HIGH" if amount >= 100000 else "MEDIUM",
        description="High-value transfer executed to a new counterparty with zero prior transaction history.",
        supporting_ids=_find_evidence_ids(["historical_behavior", "transaction"])
    )

    # Pattern 7: CROSS_BORDER_HIGH_RISK_ACTIVITY
    telemetry_risk_keys = {"is_cross_border", "is_crypto_related", "on_active_call", "is_remote_access_active", "is_scripted"}
    active_telemetry_risks = active_flag_keys.intersection(telemetry_risk_keys)
    is_telemetry_risk = len(active_telemetry_risks) > 0

    # Contextual support for behavioral escalation
    has_contextual_support = (
        is_first_interaction
        or is_telemetry_risk
        or is_rapid
        or is_pass_through
        or is_multihop
        or risk_score >= 70
    )

    # Pattern 6: BEHAVIORAL_ESCALATION
    is_escalated = deviation_ratio >= 2.0
    _eval_pattern(
        pattern_id="BEHAVIORAL_ESCALATION",
        pattern_name="Significant Baseline Behavioral Escalation",
        matched=is_escalated,
        confidence=0.90 if (deviation_ratio >= 5.0 and has_contextual_support) else 0.78,
        severity="HIGH" if (deviation_ratio >= 5.0 and has_contextual_support) else "MEDIUM",
        description=f"Transaction value deviates by {deviation_ratio}x from the sender's average monthly transaction baseline.",
        supporting_ids=_find_evidence_ids(["historical_behavior"])
    )

    _eval_pattern(
        pattern_id="CROSS_BORDER_HIGH_RISK_ACTIVITY",
        pattern_name="High-Risk Telemetry & Environmental Signals",
        matched=is_telemetry_risk,
        confidence=0.94,
        severity="HIGH",
        description=f"Critical telemetric threat flags detected during transaction execution ({', '.join(active_telemetry_risks)}).",
        supporting_ids=_find_evidence_ids(["behavioral_telemetry"])
    )

    # --- 5. Contextual Findings Traceability ---
    contextual_findings: List[Dict[str, Any]] = []
    finding_counter = 1

    def _add_finding(f_type: str, severity: str, finding_text: str, supporting_ids: List[str]):
        nonlocal finding_counter
        contextual_findings.append({
            "id": f"CTX-{finding_counter:03d}",
            "type": f_type,
            "severity": severity,
            "finding": finding_text,
            "supporting_evidence_ids": list(set(supporting_ids))
        })
        finding_counter += 1

    if deviation_ratio >= 1.5 and baseline_ev.get("id"):
        _add_finding(
            f_type="behavioral",
            severity="HIGH" if deviation_ratio >= 5.0 else "MEDIUM",
            finding_text=f"Transaction amount of INR {amount:,.2f} represents a {deviation_ratio}x deviation above historical monthly spending baseline.",
            supporting_ids=[baseline_ev["id"]]
        )

    if is_first_interaction and counterparty_ev.get("id"):
        _add_finding(
            f_type="counterparty",
            severity="HIGH" if amount >= 100000 else "MEDIUM",
            finding_text=f"Counterparty transaction represents a first-time interaction with 0 prior transfers recorded in system history.",
            supporting_ids=[counterparty_ev["id"]]
        )

    if (len(frozen_accounts) > 0 or len(withdrawn_accounts) > 0) and graph_ev.get("id"):
        _add_finding(
            f_type="graph",
            severity="HIGH",
            finding_text=f"Graph network topology indicates presence of restricted entity nodes ({len(frozen_accounts)} frozen, {len(withdrawn_accounts)} withdrawn).",
            supporting_ids=[graph_ev["id"]]
        )

    if active_flag_keys and telemetry_ev.get("id"):
        _add_finding(
            f_type="telemetry",
            severity="HIGH" if is_telemetry_risk else "MEDIUM",
            finding_text=f"Recorded active telemetric environment signals: {', '.join(active_flag_keys)}.",
            supporting_ids=[telemetry_ev["id"]]
        )

    if total_chain_txs > 1 and chain_ev.get("id"):
        _add_finding(
            f_type="velocity",
            severity="HIGH" if chain_depth >= 2 else "MEDIUM",
            finding_text=f"Fund movement spans {total_chain_txs} transactions across {chain_depth} hop depth(s) in multi-account chain.",
            supporting_ids=[chain_ev["id"]]
        )

    # Attach findings for matched patterns
    for p in patterns:
        _add_finding(
            f_type="pattern_match",
            severity=p["severity"],
            finding_text=f"Matched Contextual Pattern [{p['pattern_name']}]: {p['description']}",
            supporting_ids=p["supporting_evidence_ids"]
        )

    # --- 6. Contextual Risk & Severity Synthesis ---
    high_patterns_count = sum(1 for p in patterns if p["severity"] == "HIGH")
    
    if high_patterns_count >= 2 or risk_score >= 90 or len(frozen_accounts) > 0:
        ctx_severity = "CRITICAL"
    elif high_patterns_count >= 1 or risk_score >= 70:
        ctx_severity = "HIGH"
    elif len(patterns) >= 1 or risk_score >= 40:
        ctx_severity = "MEDIUM"
    else:
        ctx_severity = "LOW"

    # Deterministic Confidence Calculation
    if patterns:
        avg_conf = sum(p["confidence"] for p in patterns) / len(patterns)
        ctx_confidence = round(min(0.99, max(0.60, avg_conf)), 2)
    else:
        ctx_confidence = 0.70 if evidence_list else 0.50

    return {
        "found": True,
        "status": "SUCCESS",
        "target_id": target_id,
        "case_id": case_id,
        "primary_tx_id": primary_tx_id,
        "investigated_at": _now_iso(),
        "summary": {
            "contextual_severity": ctx_severity,
            "confidence": ctx_confidence,
            "pattern_count": len(patterns),
            "total_findings_count": len(contextual_findings)
        },
        "behavioral_analysis": behavioral_analysis,
        "counterparty_analysis": counterparty_analysis,
        "graph_analysis": graph_analysis,
        "patterns": patterns,
        "contextual_findings": contextual_findings
    }


def investigate_case(case_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect case evidence from Phase 1 and execute Phase 2 Contextual Investigation.
    """
    from app.services.evidence_agent import collect_evidence_for_case
    evidence_pkg = collect_evidence_for_case(case_id, store)
    return investigate_context(evidence_pkg)


def investigate_transaction(tx_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect transaction evidence from Phase 1 and execute Phase 2 Contextual Investigation.
    """
    from app.services.evidence_agent import collect_evidence_for_transaction
    evidence_pkg = collect_evidence_for_transaction(tx_id, store)
    return investigate_context(evidence_pkg)
