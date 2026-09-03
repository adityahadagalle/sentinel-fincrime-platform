"""
Evidence Collection Agent for SENTINEL.

Fulfills Phase 1 of Autonomous Financial Crime Investigation Agent framework.

Responsibility:
- Collects and normalizes factual, evidence-based data already available in SENTINEL memory store.
- Does NOT make final fraud decisions.
- Does NOT assess regulatory liability.
- Does NOT generate final recommendations.
- Does NOT hallucinate external data (sanctions, criminal records, device intelligence, geolocations, external KYC).
- Strictly distinguishes between FACT (empirical data) and INTERPRETATION (conclusions).
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.data_store import data_store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def collect_evidence_for_transaction(tx_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if store is None:
        store = data_store

    tx_store = store.get("transactions", {})
    account_store = store.get("accounts", {})
    case_store = store.get("cases", {})
    graph_store = store.get("graphs", {})

    tx = tx_store.get(tx_id)
    if not tx:
        return {
            "found": False,
            "target_id": tx_id,
            "target_type": "transaction",
            "collected_at": _now_iso(),
            "summary": {
                "total_evidence_items": 0,
                "high_severity_items": 0,
                "medium_severity_items": 0,
                "low_severity_items": 0,
                "info_severity_items": 0,
            },
            "evidence": [
                {
                    "id": "EV-000",
                    "type": "system",
                    "category": "Data Store Status",
                    "severity": "INFO",
                    "finding": f"Transaction ID '{tx_id}' was not found in active SENTINEL memory store.",
                    "data": {"tx_id": tx_id},
                    "source": "transaction_store"
                }
            ]
        }

    evidence_items: List[Dict[str, Any]] = []
    item_counter = 1

    def _add_evidence(ev_type: str, category: str, severity: str, finding: str, data: Dict[str, Any], source: str):
        nonlocal item_counter
        evidence_items.append({
            "id": f"EV-{item_counter:03d}",
            "type": ev_type,
            "category": category,
            "severity": severity,  # HIGH, MEDIUM, LOW, INFO
            "finding": finding,
            "data": data,
            "source": source
        })
        item_counter += 1

    # 1. Transaction Core Evidence
    amount = float(tx.get("amount", 0.0))
    currency = tx.get("currency", "INR")
    sender = tx.get("sender_account", "UNKNOWN")
    receiver = tx.get("receiver_account", "UNKNOWN")
    channel = tx.get("channel", "UNKNOWN")
    timestamp = tx.get("timestamp", "")
    hop_number = int(tx.get("hop_number", 0))

    tx_sev = "HIGH" if amount >= 100000 else "MEDIUM" if amount >= 25000 else "INFO"
    _add_evidence(
        ev_type="transaction",
        category="Transaction Core",
        severity=tx_sev,
        finding=f"Primary transaction {tx_id}: transfer of {currency} {amount:,.2f} via {channel} from sender {sender} to receiver {receiver} at {timestamp}.",
        data={
            "tx_id": tx_id,
            "timestamp": timestamp,
            "amount": amount,
            "currency": currency,
            "channel": channel,
            "sender_account": sender,
            "receiver_account": receiver,
            "hop_number": hop_number
        },
        source="transaction_store"
    )

    # 2. Risk Assessment Evidence
    risk_score = float(tx.get("risk_score", 0.0))
    rule_score = float(tx.get("rule_score", risk_score))
    ml_score = float(tx.get("ml_score", risk_score))
    threshold = tx.get("threshold", "LOW")
    confidence = tx.get("confidence", "LOW")
    risk_factors = tx.get("risk_factors", [])
    ml_feature_importance = tx.get("ml_feature_importance", {})
    reason = tx.get("reason", "")
    full_reason = tx.get("full_reason", "")

    risk_sev = "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 40 else "LOW"

    factor_summary_parts = []
    if isinstance(risk_factors, list):
        for f in risk_factors:
            if isinstance(f, dict) and f.get("contribution", 0) > 0:
                factor_summary_parts.append(f"{f.get('name')}: +{f.get('contribution')}")

    factor_str = ", ".join(factor_summary_parts) if factor_summary_parts else "No specific risk factors fired"

    _add_evidence(
        ev_type="risk_assessment",
        category="Risk Engine Output",
        severity=risk_sev,
        finding=f"Risk engine calculated hybrid risk score of {risk_score:.0f}/100 (Rule score: {rule_score:.0f}, ML score: {ml_score:.0f}, Threshold: {threshold}, Confidence: {confidence}). Fired factors: {factor_str}.",
        data={
            "risk_score": risk_score,
            "rule_score": rule_score,
            "ml_score": ml_score,
            "threshold": threshold,
            "confidence": confidence,
            "risk_factors": risk_factors,
            "ml_feature_importance": ml_feature_importance,
            "top_reason": tx.get("top_reason", ""),
            "reason": reason,
            "full_reason": full_reason
        },
        source="risk_engine"
    )

    # 3. Historical Account Evidence
    sender_acc = account_store.get(sender, {})
    receiver_acc = account_store.get(receiver, {})

    avg_monthly = float(sender_acc.get("avg_monthly_tx_amount", 0.0))
    sender_balance = float(sender_acc.get("current_balance_sim", 0.0))
    sender_status = sender_acc.get("status", "active")

    if avg_monthly > 0:
        ratio = round(amount / avg_monthly, 2)
        dev_sev = "HIGH" if ratio >= 5.0 else "MEDIUM" if ratio >= 1.5 else "INFO"
        _add_evidence(
            ev_type="historical_behavior",
            category="Historical Account Baseline",
            severity=dev_sev,
            finding=f"Transaction amount of {currency} {amount:,.2f} is {ratio}x the sender's average monthly transaction baseline of {currency} {avg_monthly:,.2f}.",
            data={
                "sender_account": sender,
                "transaction_amount": amount,
                "avg_monthly_tx_amount": avg_monthly,
                "deviation_ratio": ratio,
                "sender_current_balance": sender_balance,
                "sender_status": sender_status
            },
            source="account_store"
        )
    else:
        _add_evidence(
            ev_type="historical_behavior",
            category="Historical Account Baseline",
            severity="INFO",
            finding=f"Sender account {sender} has no established historical monthly transaction baseline in record.",
            data={
                "sender_account": sender,
                "transaction_amount": amount,
                "avg_monthly_tx_amount": 0.0,
                "sender_current_balance": sender_balance,
                "sender_status": sender_status
            },
            source="account_store"
        )

    # Check sender-receiver prior transaction history across tx_store
    prior_txs_between = [
        t for t in tx_store.values()
        if t.get("sender_account") == sender and t.get("receiver_account") == receiver and t.get("tx_id") != tx_id
    ]

    is_first_interaction = len(prior_txs_between) == 0
    rel_sev = "MEDIUM" if is_first_interaction else "INFO"
    rcvr_finding = (
        f"Receiver {receiver} is a first-time recipient for sender {sender} in recorded transaction history (0 prior transfers)."
        if is_first_interaction
        else f"Sender {sender} has {len(prior_txs_between)} prior recorded transaction(s) with receiver {receiver}."
    )

    _add_evidence(
        ev_type="historical_behavior",
        category="Counterparty Relationship",
        severity=rel_sev,
        finding=rcvr_finding,
        data={
            "sender_account": sender,
            "receiver_account": receiver,
            "prior_transactions_count": len(prior_txs_between),
            "is_first_interaction": is_first_interaction
        },
        source="transaction_store"
    )

    # 4. Telemetry Signals (Factual flags directly attached to tx)
    telemetry_flags = {
        "on_active_call": "Active voice call in progress during transaction",
        "is_cross_border": "Cross-border international transfer",
        "is_crypto_related": "Transaction directed to suspected crypto entity",
        "is_remote_access_active": "Active remote desktop/screen-sharing session detected",
        "bulk_transfer_flag": "High-velocity bulk transfer flag set",
        "device_changed": "Transaction originated from new unverified device",
        "location_changed": "Geographic location anomaly recorded",
        "is_scripted": "Automated/scripted interaction signature recorded",
        "velocity_flag": "Rapid transaction velocity burst detected",
        "is_round_number": "Round number payment structure",
        "is_first_time_payee": "First-time payee registration flag",
    }

    active_telemetry = []
    for flag_key, flag_desc in telemetry_flags.items():
        if tx.get(flag_key):
            active_telemetry.append({"flag": flag_key, "description": flag_desc})

    if active_telemetry:
        high_risk_flags = {"on_active_call", "is_remote_access_active", "is_crypto_related", "is_cross_border", "is_scripted"}
        has_high_telemetry = any(item["flag"] in high_risk_flags for item in active_telemetry)
        tel_sev = "HIGH" if has_high_telemetry else "MEDIUM"
        flag_descs = "; ".join([item["description"] for item in active_telemetry])

        _add_evidence(
            ev_type="behavioral_telemetry",
            category="System Telemetry Signals",
            severity=tel_sev,
            finding=f"Observed telemetry flags on transaction: {flag_descs}.",
            data={
                "active_flags": active_telemetry,
                "total_flags_count": len(active_telemetry)
            },
            source="transaction_store"
        )

    # 5. Related Activity & Case Context
    case_id = tx.get("case_id")
    if case_id and case_id in case_store:
        case = case_store[case_id]
        case_txs = case.get("transactions", [])
        total_fraud = float(case.get("total_fraud_amount", 0.0))
        case_status = case.get("status", "NEW")
        actions_taken = case.get("actions_taken", [])

        _add_evidence(
            ev_type="related_activity",
            category="Case Context",
            severity="HIGH" if len(case_txs) > 1 else "MEDIUM",
            finding=f"Transaction is linked to case {case_id} (Status: {case_status}, Total Linked Fraud: {currency} {total_fraud:,.2f}, Total Linked Transactions: {len(case_txs)}).",
            data={
                "case_id": case_id,
                "case_status": case_status,
                "linked_transactions_count": len(case_txs),
                "total_fraud_amount": total_fraud,
                "recoverable_amount": float(case.get("recoverable_amount", 0.0)),
                "actions_count": len(actions_taken)
            },
            source="case_store"
        )

        if case_id in graph_store:
            graph = graph_store[case_id]
            nodes = graph.get("nodes", [])
            edges = graph.get("edges", [])
            frozen_nodes = [n.get("account_id") for n in nodes if n.get("status") == "frozen"]
            withdrawn_nodes = [n.get("account_id") for n in nodes if n.get("status") == "withdrawn"]

            graph_sev = "HIGH" if (frozen_nodes or withdrawn_nodes) else "INFO"
            _add_evidence(
                ev_type="graph_network",
                category="Graph Network Topology",
                severity=graph_sev,
                finding=f"Case graph contains {len(nodes)} account nodes and {len(edges)} transaction edges. Nodes with special status: {len(frozen_nodes)} frozen, {len(withdrawn_nodes)} withdrawn.",
                data={
                    "case_id": case_id,
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "frozen_nodes": frozen_nodes,
                    "withdrawn_nodes": withdrawn_nodes,
                    "chain_depth": case.get("chain_depth", 0)
                },
                source="graph_engine"
            )

    # Calculate severity counts
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for item in evidence_items:
        sev = item["severity"]
        counts[sev] = counts.get(sev, 0) + 1

    return {
        "found": True,
        "target_id": tx_id,
        "target_type": "transaction",
        "case_id": tx.get("case_id"),
        "primary_tx_id": tx_id,
        "collected_at": _now_iso(),
        "summary": {
            "total_evidence_items": len(evidence_items),
            "high_severity_items": counts["HIGH"],
            "medium_severity_items": counts["MEDIUM"],
            "low_severity_items": counts["LOW"],
            "info_severity_items": counts["INFO"],
        },
        "evidence": evidence_items
    }


def collect_evidence_for_case(case_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if store is None:
        store = data_store

    case_store = store.get("cases", {})
    tx_store = store.get("transactions", {})
    account_store = store.get("accounts", {})
    graph_store = store.get("graphs", {})

    case = case_store.get(case_id)
    if not case:
        return {
            "found": False,
            "target_id": case_id,
            "target_type": "case",
            "collected_at": _now_iso(),
            "summary": {
                "total_evidence_items": 0,
                "high_severity_items": 0,
                "medium_severity_items": 0,
                "low_severity_items": 0,
                "info_severity_items": 0,
            },
            "evidence": [
                {
                    "id": "EV-000",
                    "type": "system",
                    "category": "Data Store Status",
                    "severity": "INFO",
                    "finding": f"Case ID '{case_id}' was not found in active SENTINEL memory store.",
                    "data": {"case_id": case_id},
                    "source": "case_store"
                }
            ]
        }

    evidence_items: List[Dict[str, Any]] = []
    item_counter = 1

    def _add_evidence(ev_type: str, category: str, severity: str, finding: str, data: Dict[str, Any], source: str):
        nonlocal item_counter
        evidence_items.append({
            "id": f"EV-{item_counter:03d}",
            "type": ev_type,
            "category": category,
            "severity": severity,
            "finding": finding,
            "data": data,
            "source": source
        })
        item_counter += 1

    # 1. Case Core Metadata
    status = case.get("status", "NEW")
    risk_level = float(case.get("risk_level", 0.0))
    primary_tx_id = case.get("primary_tx_id", "")
    total_fraud_amount = float(case.get("total_fraud_amount", 0.0))
    recoverable_amount = float(case.get("recoverable_amount", 0.0))
    golden_window = int(case.get("golden_window_minutes", 0))
    origin_account = case.get("origin_account", "UNKNOWN")
    chain = case.get("chain", [])
    tx_ids = case.get("transactions", [])

    case_sev = "HIGH" if risk_level >= 70 or status == "HIGH_RISK" else "MEDIUM" if risk_level >= 40 else "LOW"
    _add_evidence(
        ev_type="case_overview",
        category="Case Overview",
        severity=case_sev,
        finding=f"Case {case_id} established with status '{status}' and maximum risk level {risk_level:.0f}/100. Primary transaction: {primary_tx_id}. Origin account: {origin_account}.",
        data={
            "case_id": case_id,
            "created_at": case.get("created_at", ""),
            "status": status,
            "risk_level": risk_level,
            "primary_tx_id": primary_tx_id,
            "origin_account": origin_account,
            "golden_window_minutes": golden_window,
            "urgency_score": float(case.get("urgency_score", 0.0))
        },
        source="case_store"
    )

    # 2. Financial Loss & Recovery Evidence
    rec_pct = (recoverable_amount / total_fraud_amount * 100) if total_fraud_amount > 0 else 0.0
    _add_evidence(
        ev_type="financial",
        category="Financial Metrics",
        severity="HIGH" if total_fraud_amount >= 100000 else "MEDIUM",
        finding=f"Total fraud exposure in case is INR {total_fraud_amount:,.2f}, with estimated recoverable amount of INR {recoverable_amount:,.2f} ({rec_pct:.1f}% recovery potential).",
        data={
            "total_fraud_amount": total_fraud_amount,
            "recoverable_amount": recoverable_amount,
            "recovery_percentage": round(rec_pct, 1)
        },
        source="recovery_engine"
    )

    # 3. Primary Transaction Evidence (if exists)
    primary_tx = tx_store.get(primary_tx_id) if primary_tx_id else None
    if primary_tx:
        p_amount = float(primary_tx.get("amount", 0.0))
        p_sender = primary_tx.get("sender_account", "")
        p_rcvr = primary_tx.get("receiver_account", "")
        p_channel = primary_tx.get("channel", "")
        p_risk = float(primary_tx.get("risk_score", 0.0))

        _add_evidence(
            ev_type="transaction",
            category="Primary Transaction Evidence",
            severity="HIGH" if p_risk >= 70 else "MEDIUM",
            finding=f"Primary trigger transaction {primary_tx_id}: amount INR {p_amount:,.2f} via {p_channel} from {p_sender} to {p_rcvr} (Risk Score: {p_risk:.0f}).",
            data={
                "tx_id": primary_tx_id,
                "amount": p_amount,
                "channel": p_channel,
                "sender_account": p_sender,
                "receiver_account": p_rcvr,
                "timestamp": primary_tx.get("timestamp", ""),
                "risk_score": p_risk,
                "rule_score": primary_tx.get("rule_score"),
                "ml_score": primary_tx.get("ml_score"),
                "risk_factors": primary_tx.get("risk_factors", [])
            },
            source="transaction_store"
        )

        # Historical account deviation for primary sender
        sender_acc = account_store.get(p_sender, {})
        avg_mth = float(sender_acc.get("avg_monthly_tx_amount", 0.0))
        if avg_mth > 0:
            dev_ratio = round(p_amount / avg_mth, 2)
            _add_evidence(
                ev_type="historical_behavior",
                category="Origin Account Baseline",
                severity="HIGH" if dev_ratio >= 5.0 else "MEDIUM" if dev_ratio >= 1.5 else "INFO",
                finding=f"Primary transaction amount of INR {p_amount:,.2f} is {dev_ratio}x the origin account's ({p_sender}) monthly average of INR {avg_mth:,.2f}.",
                data={
                    "origin_account": p_sender,
                    "primary_amount": p_amount,
                    "avg_monthly_tx_amount": avg_mth,
                    "deviation_ratio": dev_ratio,
                    "origin_balance": float(sender_acc.get("current_balance_sim", 0.0))
                },
                source="account_store"
            )

    # 4. Multi-hop Transaction Chain Evidence
    if len(tx_ids) > 1:
        tx_details = []
        for tid in tx_ids:
            if tid in tx_store:
                t = tx_store[tid]
                tx_details.append({
                    "tx_id": tid,
                    "sender": t.get("sender_account"),
                    "receiver": t.get("receiver_account"),
                    "amount": float(t.get("amount", 0.0)),
                    "hop_number": t.get("hop_number", 0)
                })

        _add_evidence(
            ev_type="related_activity",
            category="Transaction Flow Chain",
            severity="HIGH",
            finding=f"Case contains {len(tx_ids)} distinct transactions propagating funds across accounts: {', '.join(chain)}.",
            data={
                "total_transactions": len(tx_ids),
                "account_chain": chain,
                "chain_depth": case.get("chain_depth", 0),
                "transactions": tx_details
            },
            source="case_store"
        )

    # 5. Graph Topology & Node Status Evidence
    graph = graph_store.get(case_id, {"nodes": [], "edges": []})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    frozen_accounts = [n.get("account_id") for n in nodes if n.get("status") == "frozen"]
    withdrawn_accounts = [n.get("account_id") for n in nodes if n.get("status") == "withdrawn"]

    _add_evidence(
        ev_type="graph_network",
        category="Graph Topology",
        severity="HIGH" if frozen_accounts or withdrawn_accounts else "MEDIUM",
        finding=f"Graph analysis identifies {len(nodes)} account nodes and {len(edges)} transfer edges. Identified status states: {len(frozen_accounts)} frozen account(s), {len(withdrawn_accounts)} withdrawn account(s).",
        data={
            "case_id": case_id,
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "frozen_accounts": frozen_accounts,
            "withdrawn_accounts": withdrawn_accounts,
            "account_nodes": nodes
        },
        source="graph_engine"
    )

    # 6. Action Log & Audit History
    actions_taken = case.get("actions_taken", [])
    if actions_taken:
        action_summaries = [
            f"{a.get('action_type')} on target {a.get('target', 'GLOBAL')} ({a.get('status')})"
            for a in actions_taken
        ]
        _add_evidence(
            ev_type="action_audit",
            category="Investigative Action Record",
            severity="INFO",
            finding=f"Recorded {len(actions_taken)} investigative action(s) on case: {'; '.join(action_summaries)}.",
            data={
                "actions_count": len(actions_taken),
                "actions": actions_taken
            },
            source="case_store"
        )
    else:
        _add_evidence(
            ev_type="action_audit",
            category="Investigative Action Record",
            severity="INFO",
            finding="No investigative actions have been executed on this case yet.",
            data={"actions_count": 0, "actions": []},
            source="case_store"
        )

    # Calculate severity counts
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for item in evidence_items:
        sev = item["severity"]
        counts[sev] = counts.get(sev, 0) + 1

    return {
        "found": True,
        "target_id": case_id,
        "target_type": "case",
        "case_id": case_id,
        "primary_tx_id": primary_tx_id,
        "collected_at": _now_iso(),
        "summary": {
            "total_evidence_items": len(evidence_items),
            "high_severity_items": counts["HIGH"],
            "medium_severity_items": counts["MEDIUM"],
            "low_severity_items": counts["LOW"],
            "info_severity_items": counts["INFO"],
        },
        "evidence": evidence_items
    }


def collect_evidence(target_id: str, store: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entrypoint for Evidence Collection Agent.
    Dynamically resolves target_id as either a case_id or a transaction_id.
    """
    if store is None:
        store = data_store

    if not target_id:
        return {
            "found": False,
            "target_id": "",
            "target_type": "unknown",
            "collected_at": _now_iso(),
            "summary": {"total_evidence_items": 0, "high_severity_items": 0, "medium_severity_items": 0, "low_severity_items": 0, "info_severity_items": 0},
            "evidence": []
        }

    if target_id in store.get("cases", {}) or target_id.startswith("CASE-"):
        return collect_evidence_for_case(target_id, store)

    if target_id in store.get("transactions", {}) or target_id.startswith("TX-"):
        return collect_evidence_for_transaction(target_id, store)

    return collect_evidence_for_case(target_id, store)
