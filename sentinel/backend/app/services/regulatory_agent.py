"""
Regulatory Risk Assessment Agent for SENTINEL (Phase 3).

Responsibility:
- Consumes Phase 1 structured Evidence Packages (`collect_evidence`) AND Phase 2 Contextual Reports (`investigate_context`).
- Does NOT query underlying database stores or recalculate Phase 1/Phase 2 metrics directly.
- Evaluates factual evidence and contextual behavioral patterns to produce structured compliance indicators (REG-001, REG-002, etc.).
- Translates risk, evidence, and context into decision-support intelligence for human compliance analysts.
- Does NOT make autonomous legal declarations, claim criminal guilt, or invent nonexistent external KYC/sanctions lookups.
- Maintains multi-tier traceability (every regulatory indicator references Phase 1 `EV-XXX` IDs and Phase 2 `CTX-XXX` / Pattern IDs).
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def assess_regulatory_risk(
    evidence_package: Optional[Dict[str, Any]],
    contextual_report: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Core entrypoint for Phase 3 Regulatory Risk Assessment Agent.
    Consumes Phase 1 evidence package AND Phase 2 contextual investigation report.
    Returns a machine-readable Regulatory Risk Assessment Report.
    """
    # Check for missing input packages (INSUFFICIENT_DATA status)
    has_ev = bool(evidence_package and isinstance(evidence_package, dict) and evidence_package.get("found"))
    has_ctx = bool(contextual_report and isinstance(contextual_report, dict) and contextual_report.get("found"))

    if not has_ev or not has_ctx:
        target_id = ""
        case_id = None
        primary_tx_id = None

        if isinstance(evidence_package, dict):
            target_id = evidence_package.get("target_id", "")
            case_id = evidence_package.get("case_id")
            primary_tx_id = evidence_package.get("primary_tx_id")
        elif isinstance(contextual_report, dict):
            target_id = contextual_report.get("target_id", "")
            case_id = contextual_report.get("case_id")
            primary_tx_id = contextual_report.get("primary_tx_id")

        return {
            "found": False,
            "status": "INSUFFICIENT_DATA",
            "target_id": target_id,
            "case_id": case_id,
            "primary_tx_id": primary_tx_id,
            "assessed_at": _now_iso(),
            "summary": {
                "regulatory_severity": "UNKNOWN",
                "assessment_heuristic_index": 0.0,
                "indicator_count": 0,
                "jurisdiction_context": "INDIAN_FINANCIAL_SYSTEM_SIMULATION"
            },
            "jurisdiction_data_status": {
                "payment_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
                "currency": "INR",
                "external_sanctions_database": "UNAVAILABLE",
                "external_kyc_verification": "NOT_CHECKED"
            },
            "regulatory_indicators": [],
            "compliance_considerations": [
                {
                    "code": "INSUFFICIENT_DATA_REVIEW",
                    "recommendation": "Insufficient factual or contextual data available to perform regulatory risk assessment."
                }
            ]
        }

    target_id = evidence_package.get("target_id", "")
    case_id = evidence_package.get("case_id")
    primary_tx_id = evidence_package.get("primary_tx_id")
    evidence_list = evidence_package.get("evidence", [])
    if not isinstance(evidence_list, list):
        evidence_list = []

    ctx_patterns = contextual_report.get("patterns", [])
    if not isinstance(ctx_patterns, list):
        ctx_patterns = []

    ctx_findings = contextual_report.get("contextual_findings", [])
    if not isinstance(ctx_findings, list):
        ctx_findings = []

    ctx_summary = contextual_report.get("summary", {}) if isinstance(contextual_report.get("summary"), dict) else {}
    ctx_severity = ctx_summary.get("contextual_severity", "LOW")

    # Map matched Phase 2 pattern IDs & findings by type for category-specific traceability
    matched_pattern_ids = {p.get("pattern_id") for p in ctx_patterns if isinstance(p, dict) and p.get("matched")}
    finding_ids_by_type: Dict[str, List[str]] = {}
    for f in ctx_findings:
        if isinstance(f, dict) and "id" in f and f.get("type"):
            finding_ids_by_type.setdefault(f["type"], []).append(f["id"])

    # Helper to collect evidence IDs by type
    def _ev_ids_by_type(ev_types: List[str]) -> List[str]:
        return [ev["id"] for ev in evidence_list if isinstance(ev, dict) and ev.get("type") in ev_types and "id" in ev]

    # Helper to collect category-specific context IDs (strictly matched patterns & matching finding types)
    def _get_supporting_context_ids(pattern_names: List[str], finding_types: List[str]) -> List[str]:
        res = []
        for p in pattern_names:
            if p in matched_pattern_ids:
                res.append(p)
        for ft in finding_types:
            if ft in finding_ids_by_type:
                res.extend(finding_ids_by_type[ft])
        return list(set(res))

    # Extract Key Facts from Phase 1 Evidence (Zero Recalculation)
    tx_ev = next((ev for ev in evidence_list if ev.get("type") == "transaction"), {})
    tx_data = tx_ev.get("data", {}) if isinstance(tx_ev, dict) else {}
    amount = float(tx_data.get("amount", 0.0))
    risk_score = float(tx_data.get("risk_score", 0.0))

    baseline_ev = next((ev for ev in evidence_list if ev.get("type") == "historical_behavior" and "Baseline" in ev.get("category", "")), {})
    baseline_data = baseline_ev.get("data", {}) if isinstance(baseline_ev, dict) else {}
    deviation_ratio = float(baseline_data.get("deviation_ratio", 0.0))

    counterparty_ev = next((ev for ev in evidence_list if ev.get("type") == "historical_behavior" and "Counterparty" in ev.get("category", "")), {})
    counterparty_data = counterparty_ev.get("data", {}) if isinstance(counterparty_ev, dict) else {}
    is_first_interaction = bool(counterparty_data.get("is_first_interaction", False))

    telemetry_ev = next((ev for ev in evidence_list if ev.get("type") == "behavioral_telemetry"), {})
    telemetry_data = telemetry_ev.get("data", {}) if isinstance(telemetry_ev, dict) else {}
    active_flags = telemetry_data.get("active_flags", []) if isinstance(telemetry_data.get("active_flags"), list) else []
    active_flag_keys = {item.get("flag") for item in active_flags if isinstance(item, dict)}

    graph_ev = next((ev for ev in evidence_list if ev.get("type") == "graph_network"), {})
    graph_data = graph_ev.get("data", {}) if isinstance(graph_ev, dict) else {}
    withdrawn_accounts = graph_data.get("withdrawn_accounts", [])

    chain_ev = next((ev for ev in evidence_list if ev.get("type") == "related_activity"), {})
    chain_data = chain_ev.get("data", {}) if isinstance(chain_ev, dict) else {}
    total_chain_txs = int(chain_data.get("total_transactions", 1))

    # --- Deterministic Regulatory Taxonomy Evaluation ---
    regulatory_indicators: List[Dict[str, Any]] = []
    reg_counter = 1

    def _add_reg_indicator(
        code: str,
        category: str,
        severity: str,
        indicator: str,
        basis: str,
        supp_ev_ids: List[str],
        supp_ctx_ids: List[str]
    ):
        nonlocal reg_counter
        regulatory_indicators.append({
            "id": f"REG-{reg_counter:03d}",
            "indicator_code": code,
            "category": category,
            "severity": severity,
            "indicator": indicator,
            "basis": basis,
            "supporting_evidence_ids": list(set(supp_ev_ids)),
            "supporting_context_ids": list(set(supp_ctx_ids))
        })
        reg_counter += 1

    # 1. POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING (Fix 3: Velocity & Baseline Deviation instead of arbitrary amount)
    if "RAPID_STRUCTURING" in matched_pattern_ids or (total_chain_txs >= 3 and deviation_ratio >= 2.0):
        ev_ids = _ev_ids_by_type(["transaction", "related_activity", "behavioral_telemetry"])
        ctx_ids = _get_supporting_context_ids(["RAPID_STRUCTURING"], ["velocity", "structuring"])
        _add_reg_indicator(
            code="POTENTIAL_CURRENCY_THRESHOLD_STRUCTURING",
            category="Anti-Money Laundering & Structuring",
            severity="HIGH",
            indicator="Transaction activity exhibits patterns consistent with potential threshold-related structuring across multi-account transfers within short golden window.",
            basis="Multi-transaction velocity pattern matched in Phase 2 combined with account baseline deviation.",
            supp_ev_ids=ev_ids,
            supp_ctx_ids=ctx_ids
        )

    # 2. SUSPICIOUS_CROSS_BORDER_TELEMETRY (Fix 2: Require active threat or high-risk counterparty, NOT generic ctx_severity)
    is_cross_border = ("is_cross_border" in active_flag_keys) or ("CROSS_BORDER_HIGH_RISK_ACTIVITY" in matched_pattern_ids)
    has_telemetry_threat = len(active_flag_keys.intersection({"on_active_call", "is_remote_access_active", "is_crypto_related", "is_scripted"})) > 0
    has_high_risk_counterparty = ("FIRST_TIME_HIGH_VALUE_COUNTERPARTY" in matched_pattern_ids) or (is_first_interaction and amount >= 100000.0)

    if is_cross_border and ("CROSS_BORDER_HIGH_RISK_ACTIVITY" in matched_pattern_ids or has_telemetry_threat or has_high_risk_counterparty):
        ev_ids = _ev_ids_by_type(["behavioral_telemetry", "transaction"])
        ctx_ids = _get_supporting_context_ids(["CROSS_BORDER_HIGH_RISK_ACTIVITY"], ["telemetry", "cross_border"])
        _add_reg_indicator(
            code="SUSPICIOUS_CROSS_BORDER_TELEMETRY",
            category="Cross-Border & Foreign Exchange Anomaly",
            severity="HIGH",
            indicator="Cross-border payment execution accompanied by active telemetric threat signals or high-risk counterparty interaction warrants foreign exchange compliance review.",
            basis="Empirical cross-border telemetry flag paired with contextual threat indicators.",
            supp_ev_ids=ev_ids,
            supp_ctx_ids=ctx_ids
        )

    # 3. MULE_LAYERED_DRAINAGE_INDICATOR (Fix 1: Category-specific context IDs)
    if "MULE_ACCOUNT_DRAINAGE" in matched_pattern_ids or len(withdrawn_accounts) > 0:
        ev_ids = _ev_ids_by_type(["graph_network", "related_activity", "transaction"])
        ctx_ids = _get_supporting_context_ids(["MULE_ACCOUNT_DRAINAGE"], ["graph", "mule"])
        _add_reg_indicator(
            code="MULE_LAYERED_DRAINAGE_INDICATOR",
            category="Mule Network & Cashout Drainage",
            severity="HIGH",
            indicator="Fund flow propagating into restricted mule account nodes for rapid off-platform cashout or balance drainage.",
            basis="Phase 2 mule account drainage pattern matched or restricted account status verified in Phase 1 graph topology.",
            supp_ev_ids=ev_ids,
            supp_ctx_ids=ctx_ids
        )

    # 4. UNUSUAL_HIGH_VALUE_FIRST_TIME_PAYEE (Fix 1: Category-specific context IDs)
    if "FIRST_TIME_HIGH_VALUE_COUNTERPARTY" in matched_pattern_ids or (is_first_interaction and amount >= 50000.0):
        ev_ids = _ev_ids_by_type(["historical_behavior", "transaction"])
        ctx_ids = _get_supporting_context_ids(["FIRST_TIME_HIGH_VALUE_COUNTERPARTY"], ["counterparty"])
        _add_reg_indicator(
            code="UNUSUAL_HIGH_VALUE_FIRST_TIME_PAYEE",
            category="Counterparty & KYC Due Diligence",
            severity="MEDIUM",
            indicator="Substantial monetary transfer directed to an unverified recipient with zero prior transaction history in institutional record.",
            basis="Phase 1 counterparty baseline confirms first-time payee interaction combined with high transaction value.",
            supp_ev_ids=ev_ids,
            supp_ctx_ids=ctx_ids
        )

    # 5. ABNORMAL_BASELINE_BEHAVIORAL_ESCALATION (Fix 1: Category-specific context IDs)
    if "BEHAVIORAL_ESCALATION" in matched_pattern_ids:
        ev_ids = _ev_ids_by_type(["historical_behavior"])
        ctx_ids = _get_supporting_context_ids(["BEHAVIORAL_ESCALATION"], ["behavioral"])
        _add_reg_indicator(
            code="ABNORMAL_BASELINE_BEHAVIORAL_ESCALATION",
            category="Customer Behavioral Baseline Anomaly",
            severity="MEDIUM",
            indicator=f"Transaction value severely deviates by {deviation_ratio}x from the customer's established monthly spending baseline.",
            basis="Phase 2 behavioral escalation pattern matched from Phase 1 account baseline metrics.",
            supp_ev_ids=ev_ids,
            supp_ctx_ids=ctx_ids
        )

    # 6. MULTI_HOP_ENTITY_PROPAGATION_INDICATOR (Fix 1: Category-specific context IDs)
    if "MULTI_HOP_PROPAGATION" in matched_pattern_ids or "PASS_THROUGH_ACTIVITY" in matched_pattern_ids:
        ev_ids = _ev_ids_by_type(["graph_network", "related_activity"])
        ctx_ids = _get_supporting_context_ids(["MULTI_HOP_PROPAGATION", "PASS_THROUGH_ACTIVITY"], ["graph", "multi_hop"])
        _add_reg_indicator(
            code="MULTI_HOP_ENTITY_PROPAGATION_INDICATOR",
            category="Multi-Hop Entity Layering",
            severity="MEDIUM",
            indicator="Fund flow propagating through a multi-hop account network presents a layering-related compliance review indicator.",
            basis="Phase 2 multi-hop propagation or pass-through layering pattern matched from graph topology.",
            supp_ev_ids=ev_ids,
            supp_ctx_ids=ctx_ids
        )

    # --- Compliance Considerations (Human Decision-Support Review Suggestions) ---
    compliance_considerations: List[Dict[str, Any]] = []

    high_reg_indicators = [r for r in regulatory_indicators if r["severity"] == "HIGH"]

    if high_reg_indicators:
        compliance_considerations.append({
            "code": "STR_INTERNAL_REVIEW_RECOMMENDED",
            "recommendation": "Internal Suspicious Transaction Report (STR) review by a certified compliance officer is recommended based on high-severity regulatory indicators."
        })

    if "UNUSUAL_HIGH_VALUE_FIRST_TIME_PAYEE" in [r["indicator_code"] for r in regulatory_indicators]:
        compliance_considerations.append({
            "code": "ENHANCED_DUE_DILIGENCE_RECOMMENDED",
            "recommendation": "Enhanced Due Diligence (EDD) verification of recipient account ownership may be appropriate prior to releasing held funds."
        })

    if "SUSPICIOUS_CROSS_BORDER_TELEMETRY" in [r["indicator_code"] for r in regulatory_indicators]:
        compliance_considerations.append({
            "code": "FOREIGN_EXCHANGE_ANOMALY_REVIEW",
            "recommendation": "Review transaction against institutional cross-border foreign exchange compliance guidelines."
        })

    if not compliance_considerations:
        compliance_considerations.append({
            "code": "STANDARD_MONITORING",
            "recommendation": "Maintain standard transaction monitoring; no immediate high-priority regulatory escalation required."
        })

    # Determine status if no indicators were matched
    status = "SUCCESS" if regulatory_indicators else "NO_INDICATORS_DETECTED"

    # --- Deterministic Severity & Heuristic Index Synthesis ---
    if high_reg_indicators and (ctx_severity in ("CRITICAL", "HIGH") or risk_score >= 80):
        reg_severity = "CRITICAL" if (len(high_reg_indicators) >= 2 or risk_score >= 90) else "HIGH"
    elif high_reg_indicators:
        reg_severity = "HIGH"
    elif regulatory_indicators:
        reg_severity = "MEDIUM"
    else:
        reg_severity = "LOW"

    # Deterministic Heuristic Index Calculation
    ctx_conf = float(ctx_summary.get("confidence", 0.70))
    if regulatory_indicators:
        reg_index = round(min(0.99, max(0.50, (ctx_conf * 0.6) + (len(regulatory_indicators) * 0.1) + (0.1 if high_reg_indicators else 0.0))), 2)
    else:
        reg_index = 0.40 if has_ev else 0.0

    return {
        "found": True,
        "status": status,
        "target_id": target_id,
        "case_id": case_id,
        "primary_tx_id": primary_tx_id,
        "assessed_at": _now_iso(),
        "summary": {
            "regulatory_severity": reg_severity,
            "assessment_heuristic_index": reg_index,
            "indicator_count": len(regulatory_indicators),
            "jurisdiction_context": "INDIAN_FINANCIAL_SYSTEM_SIMULATION"
        },
        "jurisdiction_data_status": {
            "payment_rails": ["UPI", "IMPS", "NEFT", "RTGS"],
            "currency": "INR",
            "external_sanctions_database": "UNAVAILABLE",
            "external_kyc_verification": "NOT_CHECKED"
        },
        "regulatory_indicators": regulatory_indicators,
        "compliance_considerations": compliance_considerations
    }


def assess_case_regulatory_risk(case_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect case evidence from Phase 1, run Phase 2 contextual investigation, and execute Phase 3 Regulatory Risk Assessment.
    """
    from app.services.evidence_agent import collect_evidence_for_case
    from app.services.contextual_agent import investigate_context
    ev_pkg = collect_evidence_for_case(case_id, store)
    ctx_rpt = investigate_context(ev_pkg)
    return assess_regulatory_risk(ev_pkg, ctx_rpt)


def assess_transaction_regulatory_risk(tx_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect transaction evidence from Phase 1, run Phase 2 contextual investigation, and execute Phase 3 Regulatory Risk Assessment.
    """
    from app.services.evidence_agent import collect_evidence_for_transaction
    from app.services.contextual_agent import investigate_context
    ev_pkg = collect_evidence_for_transaction(tx_id, store)
    ctx_rpt = investigate_context(ev_pkg)
    return assess_regulatory_risk(ev_pkg, ctx_rpt)
