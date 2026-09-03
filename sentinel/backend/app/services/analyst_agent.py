"""
Analyst Decision Support Agent for SENTINEL (Phase 5).

Responsibility:
- Consumes Phase 1 Evidence Package, Phase 2 Contextual Investigation Report, Phase 3 Regulatory Risk Assessment Report, AND Phase 4 Audit Explanation Report.
- Generates structured, evidence-traceable Analyst Review Steps, Operational Review Priority, and Human-in-the-Loop Disposition Options.
- Enforces strict human-in-the-Loop boundary (autonomous_execution = False, required_role = "COMPLIANCE_ANALYST").
- Strictly separates Operational Review Priority (URGENT, HIGH, STANDARD, LOW) from Intrinsic Regulatory Severity.
- Completely deterministic output derived strictly from Phase 1-4 inputs.
- Preserves multi-tier ID traceability (REG -> CTX Finding / Pattern -> EV) for every recommended step.
- Validates ID reference resolution across stages and returns INCOMPLETE_TRACEABILITY if broken references exist.
- Validates case/transaction boundary consistency and returns INVALID_INPUT if case/transaction IDs are missing, empty, or mismatching.
- Maintains strict namespace separation between Context Finding IDs (`CTX-XXX`) and Context Pattern IDs (`RAPID_STRUCTURING`, `BEHAVIORAL_ESCALATION`, etc.).
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_analyst_decision_support(
    evidence_package: Optional[Dict[str, Any]],
    contextual_report: Optional[Dict[str, Any]],
    regulatory_assessment: Optional[Dict[str, Any]],
    audit_explanation: Optional[Dict[str, Any]],
    case_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Core entrypoint for Phase 5 Analyst Decision Support Agent.
    Consumes Phase 1-4 reports and optional case context.
    Returns a machine-readable, traceable Analyst Decision Support Report.
    """
    # 1. Missing / Empty Input Handling (INSUFFICIENT_DATA)
    has_ev = bool(evidence_package and isinstance(evidence_package, dict) and evidence_package.get("found"))
    has_ctx = bool(contextual_report and isinstance(contextual_report, dict) and contextual_report.get("found"))
    has_reg = bool(regulatory_assessment and isinstance(regulatory_assessment, dict) and regulatory_assessment.get("found"))
    has_aud = bool(audit_explanation and isinstance(audit_explanation, dict) and audit_explanation.get("found"))

    if not has_ev or not has_ctx or not has_reg or not has_aud:
        target_id = ""
        case_id = None
        primary_tx_id = None

        for pkg in (evidence_package, contextual_report, regulatory_assessment, audit_explanation):
            if isinstance(pkg, dict):
                if not target_id:
                    target_id = pkg.get("target_id", "")
                if not case_id:
                    case_id = pkg.get("case_id")
                if not primary_tx_id:
                    primary_tx_id = pkg.get("primary_tx_id")

        return {
            "found": False,
            "status": "INSUFFICIENT_DATA",
            "target_id": target_id,
            "case_id": case_id,
            "primary_tx_id": primary_tx_id,
            "generated_at": _now_iso(),
            "summary": {
                "review_priority": "UNKNOWN",
                "regulatory_severity": "UNKNOWN",
                "assessment_heuristic_index": 0.0,
                "recommended_step_count": 0,
                "requires_human_approval": True
            },
            "analyst_executive_brief": "Analyst decision support unavailable because required upstream investigation data (Phase 1, Phase 2, Phase 3, or Phase 4) is incomplete or missing.",
            "review_priority": "UNKNOWN",
            "priority_rationale": "Insufficient upstream pipeline data.",
            "recommended_review_steps": [],
            "disposition_options": [],
            "uncertainties": [
                "Required upstream investigation packages are missing or incomplete."
            ],
            "data_gaps": [
                "Pipeline incomplete: Phase 1 Evidence, Phase 2 Context, Phase 3 Regulatory, or Phase 4 Audit report was not found."
            ],
            "human_approval_boundary": {
                "autonomous_execution": False,
                "required_role": "COMPLIANCE_ANALYST"
            },
            "audit_trail": {
                "source_stages": [],
                "input_case_id": case_id,
                "input_transaction_id": primary_tx_id,
                "generator": "analyst_decision_support_agent",
                "generator_version": "phase5-v1",
                "deterministic": True
            }
        }

    # 2. Strict Case & Transaction Boundary Validation (INVALID_INPUT)
    # Require non-null, non-empty, and consistent case_id & primary_tx_id across present packages
    ev_case_id = evidence_package.get("case_id")
    ctx_case_id = contextual_report.get("case_id")
    reg_case_id = regulatory_assessment.get("case_id")
    aud_case_id = audit_explanation.get("case_id")

    ev_tx_id = evidence_package.get("primary_tx_id")
    ctx_tx_id = contextual_report.get("primary_tx_id")
    reg_tx_id = regulatory_assessment.get("primary_tx_id")
    aud_tx_id = audit_explanation.get("primary_tx_id")

    all_case_vals = [ev_case_id, ctx_case_id, reg_case_id, aud_case_id]
    non_null_cases = [c for c in all_case_vals if c]

    if non_null_cases:
        # If any case_id is set, EVERY package must have a valid non-empty case_id and all must be identical
        if len(non_null_cases) != 4 or len(set(non_null_cases)) != 1:
            return {
                "found": False,
                "status": "INVALID_INPUT",
                "target_id": evidence_package.get("target_id", ""),
                "case_id": ev_case_id or ctx_case_id or reg_case_id or aud_case_id,
                "primary_tx_id": ev_tx_id or ctx_tx_id or reg_tx_id or aud_tx_id,
                "generated_at": _now_iso(),
                "summary": {
                    "review_priority": "UNKNOWN",
                    "regulatory_severity": "UNKNOWN",
                    "assessment_heuristic_index": 0.0,
                    "recommended_step_count": 0,
                    "requires_human_approval": True
                },
                "analyst_executive_brief": f"Decision support failed: Incomplete or conflicting case IDs detected across pipeline packages ({ev_case_id} vs {ctx_case_id} vs {reg_case_id} vs {aud_case_id}).",
                "review_priority": "UNKNOWN",
                "priority_rationale": "Case ID boundary validation error.",
                "recommended_review_steps": [],
                "disposition_options": [],
                "uncertainties": ["Input case ID inconsistency or null case_id across pipeline stages."],
                "data_gaps": ["Case boundary validation error: Missing or conflicting case IDs."],
                "human_approval_boundary": {
                    "autonomous_execution": False,
                    "required_role": "COMPLIANCE_ANALYST"
                },
                "audit_trail": {
                    "source_stages": ["evidence_collection", "contextual_investigation", "regulatory_assessment", "audit_explanation"],
                    "input_case_id": ev_case_id,
                    "input_transaction_id": ev_tx_id,
                    "generator": "analyst_decision_support_agent",
                    "generator_version": "phase5-v1",
                    "deterministic": True
                }
            }

    all_tx_vals = [ev_tx_id, ctx_tx_id, reg_tx_id, aud_tx_id]
    non_null_txs = [t for t in all_tx_vals if t]

    if non_null_txs:
        # If any primary_tx_id is set, EVERY package must have a valid non-empty primary_tx_id and all must be identical
        if len(non_null_txs) != 4 or len(set(non_null_txs)) != 1:
            return {
                "found": False,
                "status": "INVALID_INPUT",
                "target_id": evidence_package.get("target_id", ""),
                "case_id": ev_case_id or ctx_case_id or reg_case_id or aud_case_id,
                "primary_tx_id": ev_tx_id or ctx_tx_id or reg_tx_id or aud_tx_id,
                "generated_at": _now_iso(),
                "summary": {
                    "review_priority": "UNKNOWN",
                    "regulatory_severity": "UNKNOWN",
                    "assessment_heuristic_index": 0.0,
                    "recommended_step_count": 0,
                    "requires_human_approval": True
                },
                "analyst_executive_brief": f"Decision support failed: Incomplete or conflicting primary transaction IDs detected across pipeline packages ({ev_tx_id} vs {ctx_tx_id} vs {reg_tx_id} vs {aud_tx_id}).",
                "review_priority": "UNKNOWN",
                "priority_rationale": "Transaction ID boundary validation error.",
                "recommended_review_steps": [],
                "disposition_options": [],
                "uncertainties": ["Input primary transaction ID inconsistency or null primary_tx_id across pipeline stages."],
                "data_gaps": ["Transaction boundary validation error: Missing or conflicting primary transaction IDs."],
                "human_approval_boundary": {
                    "autonomous_execution": False,
                    "required_role": "COMPLIANCE_ANALYST"
                },
                "audit_trail": {
                    "source_stages": ["evidence_collection", "contextual_investigation", "regulatory_assessment", "audit_explanation"],
                    "input_case_id": ev_case_id,
                    "input_transaction_id": ev_tx_id,
                    "generator": "analyst_decision_support_agent",
                    "generator_version": "phase5-v1",
                    "deterministic": True
                }
            }

    case_id = non_null_cases[0] if non_null_cases else None
    primary_tx_id = non_null_txs[0] if non_null_txs else None
    target_id = evidence_package.get("target_id", case_id or primary_tx_id or "")

    # Extract Upstream Collections
    evidence_list = evidence_package.get("evidence", [])
    if not isinstance(evidence_list, list):
        evidence_list = []

    ctx_patterns = contextual_report.get("patterns", [])
    if not isinstance(ctx_patterns, list):
        ctx_patterns = []

    ctx_findings = contextual_report.get("contextual_findings", [])
    if not isinstance(ctx_findings, list):
        ctx_findings = []

    reg_indicators = regulatory_assessment.get("regulatory_indicators", [])
    if not isinstance(reg_indicators, list):
        reg_indicators = []

    jurisdiction_status = regulatory_assessment.get("jurisdiction_data_status", {})
    if not isinstance(jurisdiction_status, dict):
        jurisdiction_status = {}

    reg_summary = regulatory_assessment.get("summary", {}) if isinstance(regulatory_assessment.get("summary"), dict) else {}
    reg_severity = reg_summary.get("regulatory_severity", "LOW")

    # Safe Heuristic Index Parsing
    raw_heuristic_idx = reg_summary.get("assessment_heuristic_index")
    if raw_heuristic_idx is None:
        heuristic_index = 0.0
    else:
        try:
            heuristic_index = float(raw_heuristic_idx)
        except (ValueError, TypeError):
            heuristic_index = 0.0

    # 3. Strict Namespace Separation & Traceability Indexing
    valid_ev_ids: Set[str] = {ev["id"] for ev in evidence_list if isinstance(ev, dict) and "id" in ev}
    valid_context_finding_ids: Set[str] = {f["id"] for f in ctx_findings if isinstance(f, dict) and "id" in f}
    valid_context_pattern_ids: Set[str] = {p["pattern_id"] for p in ctx_patterns if isinstance(p, dict) and p.get("matched") and "pattern_id" in p}
    valid_reg_ids: Set[str] = {r["id"] for r in reg_indicators if isinstance(r, dict) and "id" in r}

    unresolved_references: List[str] = []

    # Validate Stage 2 -> Stage 1 references
    for f in ctx_findings:
        if isinstance(f, dict):
            for ev_id in f.get("supporting_evidence_ids", []):
                if ev_id not in valid_ev_ids:
                    unresolved_references.append(f"Contextual Finding {f.get('id')} references non-existent Evidence ID '{ev_id}'")

    for p in ctx_patterns:
        if isinstance(p, dict) and p.get("matched"):
            for ev_id in p.get("supporting_evidence_ids", []):
                if ev_id not in valid_ev_ids:
                    unresolved_references.append(f"Contextual Pattern {p.get('pattern_id')} references non-existent Evidence ID '{ev_id}'")

    # Validate Stage 3 -> Stage 2 & Stage 1 references
    for r in reg_indicators:
        if isinstance(r, dict):
            for ev_id in r.get("supporting_evidence_ids", []):
                if ev_id not in valid_ev_ids:
                    unresolved_references.append(f"Regulatory Indicator {r.get('id')} references non-existent Evidence ID '{ev_id}'")
            for ctx_ref in r.get("supporting_context_ids", []):
                if ctx_ref not in valid_context_finding_ids and ctx_ref not in valid_context_pattern_ids:
                    unresolved_references.append(f"Regulatory Indicator {r.get('id')} references non-existent Context Finding/Pattern ID '{ctx_ref}'")

    has_traceability_failure = bool(unresolved_references)

    # 4. Review Priority Calculation (Strictly separate from Regulatory Severity)
    # Extract case context metrics if provided
    case_ctx = case_context if isinstance(case_context, dict) else {}
    golden_window_minutes = case_ctx.get("golden_window_minutes")
    if golden_window_minutes is not None:
        try:
            golden_window_minutes = int(golden_window_minutes)
        except (ValueError, TypeError):
            golden_window_minutes = None

    recoverable_amount = float(case_ctx.get("recoverable_amount", case_ctx.get("total_fraud_amount", 0.0)))
    if recoverable_amount <= 0.0:
        tx_ev = next((ev for ev in evidence_list if isinstance(ev, dict) and ev.get("type") == "transaction"), {})
        recoverable_amount = float(tx_ev.get("data", {}).get("amount", 0.0))

    if reg_severity == "CRITICAL" or (golden_window_minutes is not None and golden_window_minutes <= 15):
        review_priority = "URGENT"
        priority_rationale = f"Critical compliance severity ({reg_severity}) or urgent golden-window recovery timer ({golden_window_minutes} mins remaining)."
    elif reg_severity == "HIGH" or recoverable_amount >= 100000.0:
        review_priority = "HIGH"
        priority_rationale = f"Elevated compliance severity ({reg_severity}) or high recoverable amount (INR {recoverable_amount:,.2f})."
    elif reg_severity == "MEDIUM":
        review_priority = "STANDARD"
        priority_rationale = "Standard compliance review required for medium severity findings."
    else:
        review_priority = "LOW"
        priority_rationale = "Low priority review; no critical or high severity indicators detected."

    # 5. Deterministic Recommended Review Steps Generation
    recommended_review_steps: List[Dict[str, Any]] = []
    step_counter = 1

    # Rule 1: Steps from Regulatory Indicators
    for r in reg_indicators:
        if isinstance(r, dict) and r.get("indicator"):
            supp_ev = [eid for eid in r.get("supporting_evidence_ids", []) if eid in valid_ev_ids]
            supp_ctx_raw = r.get("supporting_context_ids", [])
            supp_finding_ids = [cid for cid in supp_ctx_raw if cid in valid_context_finding_ids]
            supp_pattern_ids = [pid for pid in supp_ctx_raw if pid in valid_context_pattern_ids]
            r_id = [r["id"]] if r.get("id") in valid_reg_ids else []

            # Require at least one valid supporting evidence or context reference
            if supp_ev or supp_finding_ids or supp_pattern_ids:
                code = r.get("indicator_code", "")
                if "STRUCTURING" in code:
                    action_label = "Request Source of Funds & Structuring Review"
                    cat = "DOCUMENTATION_REVIEW"
                elif "CROSS_BORDER" in code:
                    action_label = "Initiate Cross-Border Telemetry Threat Review"
                    cat = "COMPLIANCE_ESCALATION_REVIEW"
                elif "BEHAVIORAL" in code:
                    action_label = "Evaluate Spending Baseline Escalation"
                    cat = "BASELINE_REVIEW"
                else:
                    action_label = f"Review Compliance Indicator ({code})"
                    cat = "COMPLIANCE_ESCALATION_REVIEW"

                recommended_review_steps.append({
                    "step_id": f"RS-{step_counter:03d}",
                    "category": cat,
                    "priority": r.get("severity", "MEDIUM"),
                    "action_label": action_label,
                    "description": r.get("indicator"),
                    "supporting_evidence_ids": supp_ev,
                    "supporting_context_finding_ids": supp_finding_ids,
                    "supporting_context_pattern_ids": supp_pattern_ids,
                    "supporting_regulatory_ids": r_id
                })
                step_counter += 1

    # Rule 2: Steps from Context Findings & Patterns
    for f in ctx_findings:
        if isinstance(f, dict) and f.get("finding"):
            supp_ev = [eid for eid in f.get("supporting_evidence_ids", []) if eid in valid_ev_ids]
            f_id = [f["id"]] if f.get("id") in valid_context_finding_ids else []

            if supp_ev or f_id:
                f_type = f.get("type", "general")
                if f_type == "counterparty":
                    action_label = "Verify First-Time Counterparty Account History"
                    cat = "COUNTERPARTY_REVIEW"
                elif f_type == "behavioral":
                    action_label = "Review Account Monthly Spending Baseline"
                    cat = "BASELINE_REVIEW"
                elif f_type == "graph":
                    action_label = "Inspect Multi-Hop Graph Network Topology"
                    cat = "INFORMATION_REVIEW"
                else:
                    action_label = f"Inspect Contextual Signal ({f_type})"
                    cat = "INFORMATION_REVIEW"

                recommended_review_steps.append({
                    "step_id": f"RS-{step_counter:03d}",
                    "category": cat,
                    "priority": f.get("severity", "MEDIUM"),
                    "action_label": action_label,
                    "description": f.get("finding"),
                    "supporting_evidence_ids": supp_ev,
                    "supporting_context_finding_ids": f_id,
                    "supporting_context_pattern_ids": [],
                    "supporting_regulatory_ids": []
                })
                step_counter += 1

    # Rule 3: Manual Review Step for System Data Limitations
    ext_sanc = jurisdiction_status.get("external_sanctions_database", "UNAVAILABLE")
    ext_kyc = jurisdiction_status.get("external_kyc_verification", "NOT_CHECKED")
    tx_ev = next((ev for ev in evidence_list if isinstance(ev, dict) and ev.get("type") == "transaction"), None)
    tx_ev_ids = [tx_ev["id"]] if tx_ev and tx_ev.get("id") in valid_ev_ids else []

    if ext_kyc == "NOT_CHECKED" and tx_ev_ids:
        recommended_review_steps.append({
            "step_id": f"RS-{step_counter:03d}",
            "category": "DOCUMENTATION_REVIEW",
            "priority": "INFO",
            "action_label": "Verify Customer KYC Documentation Manually",
            "description": "External KYC identity verification status is NOT_CHECKED. Manual customer identity document verification is recommended.",
            "supporting_evidence_ids": tx_ev_ids,
            "supporting_context_finding_ids": [],
            "supporting_context_pattern_ids": [],
            "supporting_regulatory_ids": []
        })
        step_counter += 1

    # 6. Human-in-the-Loop Disposition Options
    disposition_options = [
        {
            "action_code": "DISMISS_CASE",
            "label": "Dismiss False Positive",
            "requires_reason_note": True,
            "requires_risk_acknowledgement": False
        },
        {
            "action_code": "REQUEST_CUSTOMER_CDD",
            "label": "Request Customer Proof of Funds / CDD",
            "requires_reason_note": True,
            "requires_risk_acknowledgement": False
        },
        {
            "action_code": "ESCALATE_SENIOR_COMPLIANCE",
            "label": "Escalate to Senior Compliance Officer / MLRO",
            "requires_reason_note": True,
            "requires_risk_acknowledgement": True
        },
        {
            "action_code": "APPROVE_TRANSACTION",
            "label": "Approve Transaction",
            "requires_reason_note": True,
            "requires_risk_acknowledgement": False
        }
    ]

    # 7. Uncertainties & Data Gaps
    uncertainties: List[str] = []
    data_gaps: List[str] = []

    if ext_sanc == "UNAVAILABLE":
        uncertainties.append("External sanctions database verification was unavailable; no sanctions matching was performed.")
        data_gaps.append("Sanctions Intelligence Gap: External sanctions database connection state is UNAVAILABLE.")

    if ext_kyc == "NOT_CHECKED":
        uncertainties.append("External KYC identity verification was not checked; recipient legal identity unverified.")
        data_gaps.append("KYC Intelligence Gap: External KYC verification state is NOT_CHECKED.")

    uncertainties.append("Exact legal jurisdiction applicability is not established; analysis is framed under simulation context.")

    if has_traceability_failure:
        data_gaps.append(f"Traceability Reference Failure: {len(unresolved_references)} upstream reference(s) could not be resolved.")

    # 8. Executive Brief Synthesis (Factual, Neutral, Zero Intent, Zero Legal Guilt)
    if has_traceability_failure:
        exec_brief = f"Analyst decision support generated with INCOMPLETE TRACEABILITY for Case {case_id or 'N/A'}. Unresolved upstream reference(s): {'; '.join(unresolved_references)}."
        status = "INCOMPLETE_TRACEABILITY"
    elif reg_indicators:
        ind_codes = [r.get("indicator_code") for r in reg_indicators if isinstance(r, dict) and r.get("indicator_code")]
        exec_brief = (
            f"Analyst review assigned priority {review_priority} for Case {case_id or 'N/A'} (Primary TX {primary_tx_id or 'N/A'}). "
            f"Regulatory severity is {reg_severity} with a rule-based Heuristic Index of {heuristic_index:.2f}. "
            f"Matched {len(reg_indicators)} regulatory review indicator(s): {', '.join(ind_codes)}. "
            f"Generated {len(recommended_review_steps)} recommended human review step(s). Human analyst authorization is required."
        )
        status = "SUCCESS"
    else:
        exec_brief = (
            f"Analyst review assigned priority {review_priority} for Case {case_id or 'N/A'} (Primary TX {primary_tx_id or 'N/A'}). "
            f"Phase 1 evidence and Phase 2 contextual findings were evaluated cleanly; zero regulatory indicators were detected. "
            f"Regulatory severity is LOW with a rule-based Heuristic Index of {heuristic_index:.2f}."
        )
        status = "SUCCESS"

    return {
        "found": True,
        "status": status,
        "target_id": target_id,
        "case_id": case_id,
        "primary_tx_id": primary_tx_id,
        "generated_at": _now_iso(),
        "summary": {
            "review_priority": review_priority,
            "regulatory_severity": reg_severity,
            "assessment_heuristic_index": heuristic_index,
            "recommended_step_count": len(recommended_review_steps),
            "requires_human_approval": True
        },
        "analyst_executive_brief": exec_brief,
        "review_priority": review_priority,
        "priority_rationale": priority_rationale,
        "recommended_review_steps": recommended_review_steps,
        "disposition_options": disposition_options,
        "uncertainties": uncertainties,
        "data_gaps": data_gaps,
        "unresolved_references": unresolved_references,
        "human_approval_boundary": {
            "autonomous_execution": False,
            "required_role": "COMPLIANCE_ANALYST"
        },
        "audit_trail": {
            "source_stages": [
                "evidence_collection",
                "contextual_investigation",
                "regulatory_assessment",
                "audit_explanation"
            ],
            "input_case_id": case_id,
            "input_transaction_id": primary_tx_id,
            "generator": "analyst_decision_support_agent",
            "generator_version": "phase5-v1",
            "deterministic": True
        }
    }


def generate_case_analyst_decision_support(case_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect Phase 1-4 reports and generate Phase 5 Analyst Decision Support Report.
    """
    from app.services.evidence_agent import collect_evidence_for_case
    from app.services.contextual_agent import investigate_context
    from app.services.regulatory_agent import assess_regulatory_risk
    from app.services.audit_explanation_agent import generate_audit_explanation

    s = store if store is not None else {}
    case_obj = s.get("cases", {}).get(case_id, {}) if isinstance(s.get("cases"), dict) else {}

    ev_pkg = collect_evidence_for_case(case_id, store)
    ctx_rpt = investigate_context(ev_pkg)
    reg_rpt = assess_regulatory_risk(ev_pkg, ctx_rpt)
    aud_exp = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

    return generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp, case_context=case_obj)


def generate_transaction_analyst_decision_support(tx_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect Phase 1-4 reports and generate Phase 5 Analyst Decision Support Report.
    """
    from app.services.evidence_agent import collect_evidence_for_transaction
    from app.services.contextual_agent import investigate_context
    from app.services.regulatory_agent import assess_regulatory_risk
    from app.services.audit_explanation_agent import generate_audit_explanation

    ev_pkg = collect_evidence_for_transaction(tx_id, store)
    ctx_rpt = investigate_context(ev_pkg)
    reg_rpt = assess_regulatory_risk(ev_pkg, ctx_rpt)
    aud_exp = generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)

    return generate_analyst_decision_support(ev_pkg, ctx_rpt, reg_rpt, aud_exp)
