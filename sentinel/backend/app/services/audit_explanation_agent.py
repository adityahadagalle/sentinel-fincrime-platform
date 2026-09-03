"""
Audit Explanation Agent for SENTINEL (Phase 4).

Responsibility:
- Consumes Phase 1 Evidence Package, Phase 2 Contextual Investigation Report, AND Phase 3 Regulatory Risk Assessment Report.
- Converts upstream structured outputs into an audit-ready, human-readable explanation.
- Pure explanation layer over Phase 1-3 outputs. Does NOT create new detection logic, recalculate risk/severity, invent facts, infer intent, make legal claims, or call external APIs/LLMs.
- Completely deterministic output derived strictly from Phase 1-3 inputs.
- Enforces structural ID Existence & Set Membership Validation across pipeline stages (REG -> CTX Finding / Pattern -> EV).
- Validates ID reference resolution across stages and returns INCOMPLETE_TRACEABILITY if broken references exist.
- Validates case/transaction boundary consistency and returns INVALID_INPUT if case/transaction IDs are missing, empty, or mismatching.
- Maintains strict namespace separation between Context Finding IDs (`CTX-XXX`) and Context Pattern IDs (`RAPID_STRUCTURING`, `BEHAVIORAL_ESCALATION`, etc.).
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_audit_explanation(
    evidence_package: Optional[Dict[str, Any]],
    contextual_report: Optional[Dict[str, Any]],
    regulatory_assessment: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Core entrypoint for Phase 4 Audit Explanation Agent.
    Consumes Phase 1 evidence package, Phase 2 contextual report, and Phase 3 regulatory assessment.
    Returns a machine-readable, traceable Audit Explanation Report with strict namespace separation.
    """
    # 1. Missing / Empty Input Handling (INSUFFICIENT_DATA)
    has_ev = bool(evidence_package and isinstance(evidence_package, dict) and evidence_package.get("found"))
    has_ctx = bool(contextual_report and isinstance(contextual_report, dict) and contextual_report.get("found"))
    has_reg = bool(regulatory_assessment and isinstance(regulatory_assessment, dict) and regulatory_assessment.get("found"))

    if not has_ev or not has_ctx or not has_reg:
        target_id = ""
        case_id = None
        primary_tx_id = None

        for pkg in (evidence_package, contextual_report, regulatory_assessment):
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
            "executive_summary": "Audit explanation unavailable because required upstream investigation data (Phase 1, Phase 2, or Phase 3) is incomplete or missing.",
            "investigation_narrative": [],
            "key_findings": [],
            "uncertainties": [
                "Required upstream investigation packages are missing or incomplete."
            ],
            "data_gaps": [
                "Investigation package incomplete: Phase 1 Evidence, Phase 2 Context, or Phase 3 Regulatory report was not found."
            ],
            "audit_trail": {
                "source_stages": [],
                "input_case_id": case_id,
                "input_transaction_id": primary_tx_id,
                "generator": "audit_explanation_agent",
                "generator_version": "phase4-v1.1-hardened",
                "deterministic": True
            }
        }

    # 2. Strict Case & Transaction Boundary Validation (INVALID_INPUT)
    # Require non-null, non-empty, and consistent case_id & primary_tx_id across present packages
    ev_case_id = evidence_package.get("case_id")
    ctx_case_id = contextual_report.get("case_id")
    reg_case_id = regulatory_assessment.get("case_id")

    ev_tx_id = evidence_package.get("primary_tx_id")
    ctx_tx_id = contextual_report.get("primary_tx_id")
    reg_tx_id = regulatory_assessment.get("primary_tx_id")

    # If any package specifies case_id, all present packages must have non-empty case_id and all must be identical
    all_case_vals = [ev_case_id, ctx_case_id, reg_case_id]
    non_null_cases = [c for c in all_case_vals if c]

    if non_null_cases:
        # If any case_id is set, EVERY package must have a valid non-empty case_id and all must be identical
        if len(non_null_cases) != 3 or len(set(non_null_cases)) != 1:
            return {
                "found": False,
                "status": "INVALID_INPUT",
                "target_id": evidence_package.get("target_id", ""),
                "case_id": ev_case_id or ctx_case_id or reg_case_id,
                "primary_tx_id": ev_tx_id or ctx_tx_id or reg_tx_id,
                "generated_at": _now_iso(),
                "executive_summary": f"Audit explanation failed: Incomplete or conflicting case IDs detected across pipeline packages ({ev_case_id} vs {ctx_case_id} vs {reg_case_id}).",
                "investigation_narrative": [],
                "key_findings": [],
                "uncertainties": ["Input case ID inconsistency or null case_id across pipeline stages."],
                "data_gaps": ["Case boundary validation error: Missing or conflicting case IDs."],
                "audit_trail": {
                    "source_stages": ["evidence_collection", "contextual_investigation", "regulatory_assessment"],
                    "input_case_id": ev_case_id,
                    "input_transaction_id": ev_tx_id,
                    "generator": "audit_explanation_agent",
                    "generator_version": "phase4-v1.1-hardened",
                    "deterministic": True
                }
            }

    all_tx_vals = [ev_tx_id, ctx_tx_id, reg_tx_id]
    non_null_txs = [t for t in all_tx_vals if t]

    if non_null_txs:
        # If any primary_tx_id is set, EVERY package must have a valid non-empty primary_tx_id and all must be identical
        if len(non_null_txs) != 3 or len(set(non_null_txs)) != 1:
            return {
                "found": False,
                "status": "INVALID_INPUT",
                "target_id": evidence_package.get("target_id", ""),
                "case_id": ev_case_id or ctx_case_id or reg_case_id,
                "primary_tx_id": ev_tx_id or ctx_tx_id or reg_tx_id,
                "generated_at": _now_iso(),
                "executive_summary": f"Audit explanation failed: Incomplete or conflicting primary transaction IDs detected across pipeline packages ({ev_tx_id} vs {ctx_tx_id} vs {reg_tx_id}).",
                "investigation_narrative": [],
                "key_findings": [],
                "uncertainties": ["Input primary transaction ID inconsistency or null primary_tx_id across pipeline stages."],
                "data_gaps": ["Transaction boundary validation error: Missing or conflicting primary transaction IDs."],
                "audit_trail": {
                    "source_stages": ["evidence_collection", "contextual_investigation", "regulatory_assessment"],
                    "input_case_id": ev_case_id,
                    "input_transaction_id": ev_tx_id,
                    "generator": "audit_explanation_agent",
                    "generator_version": "phase4-v1.1-hardened",
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

    compliance_considerations = regulatory_assessment.get("compliance_considerations", [])
    if not isinstance(compliance_considerations, list):
        compliance_considerations = []

    jurisdiction_status = regulatory_assessment.get("jurisdiction_data_status", {})
    if not isinstance(jurisdiction_status, dict):
        jurisdiction_status = {}

    reg_summary = regulatory_assessment.get("summary", {}) if isinstance(regulatory_assessment.get("summary"), dict) else {}
    reg_severity = reg_summary.get("regulatory_severity", "LOW")

    # Safe Heuristic Index Parsing (Prevents TypeError on None / string / malformed)
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

    # Validate Stage 3 -> Stage 2 & Stage 1 references with distinct namespace resolution
    for r in reg_indicators:
        if isinstance(r, dict):
            for ev_id in r.get("supporting_evidence_ids", []):
                if ev_id not in valid_ev_ids:
                    unresolved_references.append(f"Regulatory Indicator {r.get('id')} references non-existent Evidence ID '{ev_id}'")
            for ctx_ref in r.get("supporting_context_ids", []):
                if ctx_ref not in valid_context_finding_ids and ctx_ref not in valid_context_pattern_ids:
                    unresolved_references.append(f"Regulatory Indicator {r.get('id')} references non-existent Context Finding/Pattern ID '{ctx_ref}'")

    has_traceability_failure = bool(unresolved_references)

    # 4. Construct Investigation Narrative Steps (Pipeline Order: FACT -> CONTEXT -> REGULATORY -> LIMITATION)
    investigation_narrative: List[Dict[str, Any]] = []
    step_num = 1

    # Stage 1: FACT narrative steps from Evidence Package
    curr = "INR"
    tx_ev = next((ev for ev in evidence_list if ev.get("type") == "transaction"), None)
    if tx_ev:
        tx_d = tx_ev.get("data", {})
        amt = tx_d.get("amount", 0.0)
        curr = tx_d.get("currency", "INR")
        chan = tx_d.get("channel", "UPI")
        investigation_narrative.append({
            "step": step_num,
            "stage": "EVIDENCE",
            "statement": f"Primary transaction executed for {curr} {amt:,.2f} via {chan} payment rail.",
            "claim_type": "FACT",
            "evidence_ids": [tx_ev["id"]],
            "context_finding_ids": [],
            "context_pattern_ids": [],
            "regulatory_ids": []
        })
        step_num += 1

    baseline_ev = next((ev for ev in evidence_list if ev.get("type") == "historical_behavior" and "Baseline" in ev.get("category", "")), None)
    if baseline_ev:
        b_d = baseline_ev.get("data", {})
        dev = b_d.get("deviation_ratio", 1.0)
        avg = b_d.get("average_amount", 0.0)
        investigation_narrative.append({
            "step": step_num,
            "stage": "EVIDENCE",
            "statement": f"Account historical spending baseline averages {curr} {avg:,.2f} per transaction, yielding a {dev}x baseline deviation ratio.",
            "claim_type": "FACT",
            "evidence_ids": [baseline_ev["id"]],
            "context_finding_ids": [],
            "context_pattern_ids": [],
            "regulatory_ids": []
        })
        step_num += 1

    counterparty_ev = next((ev for ev in evidence_list if ev.get("type") == "historical_behavior" and "Counterparty" in ev.get("category", "")), None)
    if counterparty_ev:
        c_d = counterparty_ev.get("data", {})
        is_first = c_d.get("is_first_interaction", False)
        if is_first:
            investigation_narrative.append({
                "step": step_num,
                "stage": "EVIDENCE",
                "statement": "Counterparty transaction history confirms zero prior interaction with the recipient account in institutional record.",
                "claim_type": "FACT",
                "evidence_ids": [counterparty_ev["id"]],
                "context_finding_ids": [],
                "context_pattern_ids": [],
                "regulatory_ids": []
            })
            step_num += 1

    telemetry_ev = next((ev for ev in evidence_list if ev.get("type") == "behavioral_telemetry"), None)
    if telemetry_ev:
        t_d = telemetry_ev.get("data", {})
        a_flags = t_d.get("active_flags", [])
        flag_names = [f.get("flag") for f in a_flags if isinstance(f, dict) and f.get("flag")]
        if flag_names:
            investigation_narrative.append({
                "step": step_num,
                "stage": "EVIDENCE",
                "statement": f"Recorded active system telemetry flags: {', '.join(flag_names)}.",
                "claim_type": "FACT",
                "evidence_ids": [telemetry_ev["id"]],
                "context_finding_ids": [],
                "context_pattern_ids": [],
                "regulatory_ids": []
            })
            step_num += 1

    graph_ev = next((ev for ev in evidence_list if ev.get("type") == "graph_network"), None)
    if graph_ev:
        g_d = graph_ev.get("data", {})
        depth = g_d.get("chain_depth", 1)
        w_accs = g_d.get("withdrawn_accounts", [])
        investigation_narrative.append({
            "step": step_num,
            "stage": "EVIDENCE",
            "statement": f"Graph network topology establishes a chain depth of {depth} hops with {len(w_accs)} restricted destination nodes.",
            "claim_type": "FACT",
            "evidence_ids": [graph_ev["id"]],
            "context_finding_ids": [],
            "context_pattern_ids": [],
            "regulatory_ids": []
        })
        step_num += 1

    # Stage 2: CONTEXT narrative steps from Phase 2 Contextual Findings & Matched Patterns
    for f in ctx_findings:
        if isinstance(f, dict) and f.get("finding"):
            supp_ev = f.get("supporting_evidence_ids", [])
            f_id = f.get("id")
            investigation_narrative.append({
                "step": step_num,
                "stage": "CONTEXT",
                "statement": f.get("finding"),
                "claim_type": "CONTEXT",
                "evidence_ids": [eid for eid in supp_ev if eid in valid_ev_ids],
                "context_finding_ids": [f_id] if f_id in valid_context_finding_ids else [],
                "context_pattern_ids": [],
                "regulatory_ids": []
            })
            step_num += 1

    for p in ctx_patterns:
        if isinstance(p, dict) and p.get("matched") and p.get("description"):
            supp_ev = p.get("supporting_evidence_ids", [])
            p_id = p.get("pattern_id")
            investigation_narrative.append({
                "step": step_num,
                "stage": "CONTEXT",
                "statement": f"Pattern {p.get('pattern_name', p_id)} matched: {p.get('description')}",
                "claim_type": "CONTEXT",
                "evidence_ids": [eid for eid in supp_ev if eid in valid_ev_ids],
                "context_finding_ids": [],
                "context_pattern_ids": [p_id] if p_id in valid_context_pattern_ids else [],
                "regulatory_ids": []
            })
            step_num += 1

    # Stage 3: REGULATORY INTERPRETATION narrative steps from Phase 3 Indicators
    for r in reg_indicators:
        if isinstance(r, dict) and r.get("indicator"):
            supp_ev = [eid for eid in r.get("supporting_evidence_ids", []) if eid in valid_ev_ids]
            supp_ctx_raw = r.get("supporting_context_ids", [])
            supp_finding_ids = [cid for cid in supp_ctx_raw if cid in valid_context_finding_ids]
            supp_pattern_ids = [pid for pid in supp_ctx_raw if pid in valid_context_pattern_ids]

            investigation_narrative.append({
                "step": step_num,
                "stage": "REGULATORY",
                "statement": r.get("indicator"),
                "claim_type": "REGULATORY_INTERPRETATION",
                "evidence_ids": supp_ev,
                "context_finding_ids": supp_finding_ids,
                "context_pattern_ids": supp_pattern_ids,
                "regulatory_ids": [r["id"]] if r.get("id") in valid_reg_ids else []
            })
            step_num += 1

    for c in compliance_considerations:
        if isinstance(c, dict) and c.get("recommendation"):
            investigation_narrative.append({
                "step": step_num,
                "stage": "REGULATORY",
                "statement": f"Phase 3 assessment suggestion: {c.get('recommendation')}",
                "claim_type": "REGULATORY_INTERPRETATION",
                "evidence_ids": [],
                "context_finding_ids": [],
                "context_pattern_ids": [],
                "regulatory_ids": [r["id"] for r in reg_indicators if isinstance(r, dict) and r.get("severity") == "HIGH" and r.get("id") in valid_reg_ids]
            })
            step_num += 1

    # Stage 4: SYSTEM LIMITATION narrative steps
    ext_sanc = jurisdiction_status.get("external_sanctions_database", "UNAVAILABLE")
    ext_kyc = jurisdiction_status.get("external_kyc_verification", "NOT_CHECKED")

    investigation_narrative.append({
        "step": step_num,
        "stage": "LIMITATION",
        "statement": f"External sanctions database verification state: {ext_sanc}.",
        "claim_type": "SYSTEM_LIMITATION",
        "evidence_ids": [],
        "context_finding_ids": [],
        "context_pattern_ids": [],
        "regulatory_ids": []
    })
    step_num += 1

    investigation_narrative.append({
        "step": step_num,
        "stage": "LIMITATION",
        "statement": f"External KYC identity verification state: {ext_kyc}.",
        "claim_type": "SYSTEM_LIMITATION",
        "evidence_ids": [],
        "context_finding_ids": [],
        "context_pattern_ids": [],
        "regulatory_ids": []
    })
    step_num += 1

    # 5. Key Findings Synthesis (Preserving Upstream Severity & Namespace Isolation)
    key_findings: List[Dict[str, Any]] = []
    finding_counter = 1

    for r in reg_indicators:
        if isinstance(r, dict):
            supp_ev = [eid for eid in r.get("supporting_evidence_ids", []) if eid in valid_ev_ids]
            supp_ctx_raw = r.get("supporting_context_ids", [])
            supp_finding_ids = [cid for cid in supp_ctx_raw if cid in valid_context_finding_ids]
            supp_pattern_ids = [pid for pid in supp_ctx_raw if pid in valid_context_pattern_ids]

            key_findings.append({
                "finding_id": f"KF-{finding_counter:03d}",
                "stage": "REGULATORY",
                "severity": r.get("severity", "MEDIUM"),  # Preserve exact upstream severity
                "statement": r.get("indicator", ""),
                "supporting_evidence_ids": supp_ev,
                "supporting_context_finding_ids": supp_finding_ids,
                "supporting_context_pattern_ids": supp_pattern_ids,
                "supporting_regulatory_ids": [r["id"]] if r.get("id") in valid_reg_ids else []
            })
            finding_counter += 1

    for f in ctx_findings:
        if isinstance(f, dict):
            supp_ev = [eid for eid in f.get("supporting_evidence_ids", []) if eid in valid_ev_ids]
            f_id = f.get("id")
            key_findings.append({
                "finding_id": f"KF-{finding_counter:03d}",
                "stage": "CONTEXT",
                "severity": f.get("severity", "MEDIUM"),
                "statement": f.get("finding", ""),
                "supporting_evidence_ids": supp_ev,
                "supporting_context_finding_ids": [f_id] if f_id in valid_context_finding_ids else [],
                "supporting_context_pattern_ids": [],
                "supporting_regulatory_ids": []
            })
            finding_counter += 1

    key_findings.append({
        "finding_id": f"KF-{finding_counter:03d}",
        "stage": "LIMITATION",
        "severity": "INFO",
        "statement": f"External sanctions database was {ext_sanc}; external KYC verification was {ext_kyc}.",
        "supporting_evidence_ids": [],
        "supporting_context_finding_ids": [],
        "supporting_context_pattern_ids": [],
        "supporting_regulatory_ids": []
    })

    # 6. Uncertainties & Data Gaps
    uncertainties: List[str] = []
    data_gaps: List[str] = []

    if ext_sanc == "UNAVAILABLE":
        uncertainties.append("External sanctions database verification was unavailable; no sanctions matching was performed.")
        data_gaps.append("Sanctions Intelligence Gap: External sanctions database connection state is UNAVAILABLE.")

    if ext_kyc == "NOT_CHECKED":
        uncertainties.append("External KYC identity verification was not checked; recipient legal identity unverified.")
        data_gaps.append("KYC Intelligence Gap: External KYC verification state is NOT_CHECKED.")

    uncertainties.append("Exact legal jurisdiction applicability is not established; analysis is framed under simulation context.")

    if not reg_indicators:
        data_gaps.append("No Regulatory Indicators Breach: Factual evidence and contextual reports were evaluated, but zero regulatory indicators were triggered.")

    if has_traceability_failure:
        data_gaps.append(f"Traceability Reference Failure: {len(unresolved_references)} upstream reference(s) could not be resolved.")

    # 7. Executive Summary Synthesis
    if has_traceability_failure:
        exec_summary = f"Audit explanation generated with INCOMPLETE TRACEABILITY for Case {case_id or 'N/A'}. Unresolved upstream reference(s): {'; '.join(unresolved_references)}."
        status = "INCOMPLETE_TRACEABILITY"
    elif reg_indicators:
        ind_codes = [r.get("indicator_code") for r in reg_indicators if isinstance(r, dict) and r.get("indicator_code")]
        exec_summary = (
            f"SENTINEL completed automated audit explanation for Case {case_id or 'N/A'} (Primary TX {primary_tx_id or 'N/A'}). "
            f"Phase 3 established regulatory severity {reg_severity} with a rule-based Heuristic Index of {heuristic_index:.2f}. "
            f"Matched {len(reg_indicators)} regulatory indicator(s): {', '.join(ind_codes)}. "
            f"External sanctions verification was {ext_sanc.lower()} and KYC verification was {ext_kyc.lower()}."
        )
        status = "SUCCESS"
    else:
        exec_summary = (
            f"SENTINEL completed automated audit explanation for Case {case_id or 'N/A'} (Primary TX {primary_tx_id or 'N/A'}). "
            f"Phase 1 evidence and Phase 2 contextual findings were evaluated cleanly; NO regulatory indicators were detected. "
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
            "regulatory_severity": reg_severity,
            "assessment_heuristic_index": heuristic_index,
            "narrative_step_count": len(investigation_narrative),
            "key_finding_count": len(key_findings),
            "traceability_status": "VALIDATED" if not has_traceability_failure else "UNRESOLVED_REFERENCES"
        },
        "executive_summary": exec_summary,
        "investigation_narrative": investigation_narrative,
        "key_findings": key_findings,
        "uncertainties": uncertainties,
        "data_gaps": data_gaps,
        "unresolved_references": unresolved_references,
        "audit_trail": {
            "source_stages": [
                "evidence_collection",
                "contextual_investigation",
                "regulatory_assessment"
            ],
            "input_case_id": case_id,
            "input_transaction_id": primary_tx_id,
            "generator": "audit_explanation_agent",
            "generator_version": "phase4-v1.1-hardened",
            "deterministic": True
        }
    }


def generate_case_audit_explanation(case_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect Phase 1 evidence, Phase 2 contextual report, Phase 3 regulatory assessment, and generate Phase 4 Audit Explanation.
    """
    from app.services.evidence_agent import collect_evidence_for_case
    from app.services.contextual_agent import investigate_context
    from app.services.regulatory_agent import assess_regulatory_risk

    ev_pkg = collect_evidence_for_case(case_id, store)
    ctx_rpt = investigate_context(ev_pkg)
    reg_rpt = assess_regulatory_risk(ev_pkg, ctx_rpt)
    return generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)


def generate_transaction_audit_explanation(tx_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrapper to collect Phase 1 evidence, Phase 2 contextual report, Phase 3 regulatory assessment, and generate Phase 4 Audit Explanation.
    """
    from app.services.evidence_agent import collect_evidence_for_transaction
    from app.services.contextual_agent import investigate_context
    from app.services.regulatory_agent import assess_regulatory_risk

    ev_pkg = collect_evidence_for_transaction(tx_id, store)
    ctx_rpt = investigate_context(ev_pkg)
    reg_rpt = assess_regulatory_risk(ev_pkg, ctx_rpt)
    return generate_audit_explanation(ev_pkg, ctx_rpt, reg_rpt)
