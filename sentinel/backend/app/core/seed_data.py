"""
SENTINEL Pre-Seeded Demonstration Data Engine
Provides authentic multi-tier forensic scenarios on backend startup:
1. SAFE / SIMPLE: Exactly 2 nodes, 1 flow (Customer -> Merchant, Low Risk)
2. NORMAL MULTI-STEP: 3 nodes, 2 flows (Customer -> Intermediary Mule -> Merchant, Medium Risk)
3. SUSPICIOUS BRANCHING: 5 nodes, 4 flows (Victim -> Hub -> (Branch A / Branch B) -> Cashout / Merchant)
4. FRAUD LAYERED CHAIN: 6 nodes, 5 sequential flows (Victim -> Mule 1 -> Mule 2 -> UPI -> Cashout -> Final Destination)
"""

from datetime import datetime, timezone
from typing import Dict, Any


def _iso_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def seed_initial_demonstration_data(store: Dict[str, Any]) -> None:
    """
    Populates data_store with distinct, authentic forensic topologies.
    Idempotent: only seeds if store does not already have these demonstration cases.
    """
    if "accounts" not in store:
        store["accounts"] = {}
    if "transactions" not in store:
        store["transactions"] = {}
    if "cases" not in store:
        store["cases"] = {}
    if "graphs" not in store:
        store["graphs"] = {}
    if "actions" not in store:
        store["actions"] = []

    now = _iso_now()

    # =========================================================================
    # SCENARIO 1: SAFE / SIMPLE RETAIL (2 Nodes · 1 Edge · DIRECT_TRANSFER)
    # =========================================================================
    case_1_id = "CASE-SAFE-01"
    tx_1_id = "TX-SAFE-1001"
    s1 = "ACC-USR-1001"
    r1 = "ACC-MERCH-5001"

    store["accounts"][s1] = {
        "account_id": s1,
        "account_type": "SOURCE",
        "node_type": "victim",
        "status": "active",
        "current_balance_sim": 185000.0,
        "risk_score": 12.0,
        "kyc_status": "VERIFIED"
    }
    store["accounts"][r1] = {
        "account_id": r1,
        "account_type": "DESTINATION",
        "node_type": "merchant",
        "status": "active",
        "current_balance_sim": 94000.0,
        "risk_score": 10.0,
        "kyc_status": "VERIFIED"
    }

    tx_1 = {
        "tx_id": tx_1_id,
        "timestamp": now,
        "case_id": case_1_id,
        "sender_account": s1,
        "receiver_account": r1,
        "amount": 3450.0,
        "currency": "INR",
        "channel": "UPI",
        "risk_score": 12,
        "rule_score": 10,
        "ml_score": 14,
        "threshold": "LOW",
        "reason": "Routine retail merchant settlement",
        "full_reason": "Low risk payment to verified merchant category code",
        "confidence": "HIGH",
        "hop_number": 1,
        "total_hops": 1,
        "pattern_type": "DIRECT_TRANSFER",
        "status": "APPROVED"
    }
    store["transactions"][tx_1_id] = tx_1

    store["cases"][case_1_id] = {
        "case_id": case_1_id,
        "status": "NEW",
        "risk_level": 12.0,
        "primary_tx_id": tx_1_id,
        "total_fraud_amount": 3450.0,
        "recoverable_amount": 3450.0,
        "origin_account": s1,
        "chain": [s1, r1],
        "transactions": [tx_1_id],
        "actions_taken": [],
        "timeline": [{"at": now, "event": "case_created", "actor": "system"}]
    }

    # =========================================================================
    # SCENARIO 2: NORMAL MULTI-STEP RELAY (3 Nodes · 2 Edges · LINEAR_CHAIN)
    # =========================================================================
    case_2_id = "CASE-NORM-02"
    chain_2_id = "CHAIN-NORM-02"
    s2 = "ACC-USR-1002"
    m2 = "ACC-MULE-2010"
    d2 = "ACC-MERCH-5002"
    tx_2a_id = "TX-NORM-2001"
    tx_2b_id = "TX-NORM-2002"

    store["accounts"][s2] = {
        "account_id": s2,
        "account_type": "SOURCE",
        "node_type": "victim",
        "status": "active",
        "current_balance_sim": 140000.0,
        "risk_score": 25.0,
        "kyc_status": "VERIFIED"
    }
    store["accounts"][m2] = {
        "account_id": m2,
        "account_type": "MULE",
        "node_type": "mule",
        "status": "active",
        "current_balance_sim": 48000.0,
        "risk_score": 45.0,
        "kyc_status": "PENDING"
    }
    store["accounts"][d2] = {
        "account_id": d2,
        "account_type": "DESTINATION",
        "node_type": "merchant",
        "status": "active",
        "current_balance_sim": 46500.0,
        "risk_score": 30.0,
        "kyc_status": "VERIFIED"
    }

    tx_2a = {
        "tx_id": tx_2a_id,
        "timestamp": now,
        "case_id": case_2_id,
        "chain_id": chain_2_id,
        "root_transaction_id": tx_2a_id,
        "sender_account": s2,
        "receiver_account": m2,
        "amount": 48000.0,
        "currency": "INR",
        "channel": "IMPS",
        "risk_score": 42,
        "rule_score": 40,
        "ml_score": 44,
        "threshold": "MEDIUM",
        "reason": "Intermediate relay transfer detected",
        "full_reason": "Rapid pass-through to intermediary individual account",
        "confidence": "MEDIUM",
        "hop_number": 1,
        "total_hops": 2,
        "pattern_type": "LINEAR_CHAIN"
    }
    tx_2b = {
        "tx_id": tx_2b_id,
        "timestamp": now,
        "case_id": case_2_id,
        "chain_id": chain_2_id,
        "root_transaction_id": tx_2a_id,
        "parent_transaction_id": tx_2a_id,
        "sender_account": m2,
        "receiver_account": d2,
        "amount": 46500.0,
        "currency": "INR",
        "channel": "UPI",
        "risk_score": 48,
        "rule_score": 46,
        "ml_score": 50,
        "threshold": "MEDIUM",
        "reason": "Disbursement to merchant endpoint",
        "full_reason": "Sequential fund movement from intermediary to merchant",
        "confidence": "MEDIUM",
        "hop_number": 2,
        "total_hops": 2,
        "pattern_type": "LINEAR_CHAIN"
    }
    store["transactions"][tx_2a_id] = tx_2a
    store["transactions"][tx_2b_id] = tx_2b

    store["cases"][case_2_id] = {
        "case_id": case_2_id,
        "chain_id": chain_2_id,
        "status": "NEW",
        "risk_level": 48.0,
        "primary_tx_id": tx_2a_id,
        "total_fraud_amount": 94500.0,
        "recoverable_amount": 46500.0,
        "origin_account": s2,
        "chain": [s2, m2, d2],
        "transactions": [tx_2a_id, tx_2b_id],
        "actions_taken": [],
        "timeline": [{"at": now, "event": "case_created", "actor": "system"}]
    }

    # =========================================================================
    # SCENARIO 3: SUSPICIOUS BRANCHING FLOW (5 Nodes · 4 Edges · FAN_OUT)
    # =========================================================================
    case_3_id = "CASE-BRANCH-03"
    chain_3_id = "CHAIN-BRANCH-03"
    s3 = "ACC-USR-1003"
    hub3 = "ACC-HUB-3010"
    m3a = "ACC-MULE-3020"
    m3b = "ACC-MULE-3030"
    exit3a = "CASHOUT-ATM-3040"
    exit3b = "ACC-MERCH-3050"

    tx_3a_id = "TX-BRANCH-3001"
    tx_3b_id = "TX-BRANCH-3002"
    tx_3c_id = "TX-BRANCH-3003"
    tx_3d_id = "TX-BRANCH-3004"
    tx_3e_id = "TX-BRANCH-3005"

    store["accounts"][s3] = {
        "account_id": s3,
        "account_type": "SOURCE",
        "node_type": "victim",
        "status": "active",
        "current_balance_sim": 290000.0,
        "risk_score": 20.0
    }
    store["accounts"][hub3] = {
        "account_id": hub3,
        "account_type": "INTERMEDIARY",
        "node_type": "collector",
        "status": "active",
        "current_balance_sim": 180000.0,
        "risk_score": 75.0
    }
    store["accounts"][m3a] = {
        "account_id": m3a,
        "account_type": "MULE",
        "node_type": "mule",
        "status": "active",
        "current_balance_sim": 88000.0,
        "risk_score": 80.0
    }
    store["accounts"][m3b] = {
        "account_id": m3b,
        "account_type": "MULE",
        "node_type": "mule",
        "status": "active",
        "current_balance_sim": 88000.0,
        "risk_score": 80.0
    }
    store["accounts"][exit3a] = {
        "account_id": exit3a,
        "account_type": "DESTINATION",
        "node_type": "cashout",
        "status": "flagged",
        "current_balance_sim": 85000.0,
        "risk_score": 88.0
    }
    store["accounts"][exit3b] = {
        "account_id": exit3b,
        "account_type": "DESTINATION",
        "node_type": "merchant",
        "status": "active",
        "current_balance_sim": 85000.0,
        "risk_score": 70.0
    }

    tx_3a = {
        "tx_id": tx_3a_id,
        "timestamp": now,
        "case_id": case_3_id,
        "chain_id": chain_3_id,
        "root_transaction_id": tx_3a_id,
        "sender_account": s3,
        "receiver_account": hub3,
        "amount": 180000.0,
        "currency": "INR",
        "channel": "NEFT",
        "risk_score": 72,
        "hop_number": 1,
        "total_hops": 3,
        "pattern_type": "FAN_OUT"
    }
    tx_3b = {
        "tx_id": tx_3b_id,
        "timestamp": now,
        "case_id": case_3_id,
        "chain_id": chain_3_id,
        "root_transaction_id": tx_3a_id,
        "parent_transaction_id": tx_3a_id,
        "sender_account": hub3,
        "receiver_account": m3a,
        "amount": 88000.0,
        "currency": "INR",
        "channel": "UPI",
        "risk_score": 78,
        "hop_number": 2,
        "total_hops": 3,
        "pattern_type": "FAN_OUT"
    }
    tx_3c = {
        "tx_id": tx_3c_id,
        "timestamp": now,
        "case_id": case_3_id,
        "chain_id": chain_3_id,
        "root_transaction_id": tx_3a_id,
        "parent_transaction_id": tx_3a_id,
        "sender_account": hub3,
        "receiver_account": m3b,
        "amount": 88000.0,
        "currency": "INR",
        "channel": "IMPS",
        "risk_score": 78,
        "hop_number": 2,
        "total_hops": 3,
        "pattern_type": "FAN_OUT"
    }
    tx_3d = {
        "tx_id": tx_3d_id,
        "timestamp": now,
        "case_id": case_3_id,
        "chain_id": chain_3_id,
        "root_transaction_id": tx_3a_id,
        "parent_transaction_id": tx_3b_id,
        "sender_account": m3a,
        "receiver_account": exit3a,
        "amount": 85000.0,
        "currency": "INR",
        "channel": "CARD",
        "risk_score": 85,
        "hop_number": 3,
        "total_hops": 3,
        "pattern_type": "FAN_OUT"
    }
    tx_3e = {
        "tx_id": tx_3e_id,
        "timestamp": now,
        "case_id": case_3_id,
        "chain_id": chain_3_id,
        "root_transaction_id": tx_3a_id,
        "parent_transaction_id": tx_3c_id,
        "sender_account": m3b,
        "receiver_account": exit3b,
        "amount": 85000.0,
        "currency": "INR",
        "channel": "UPI",
        "risk_score": 82,
        "hop_number": 3,
        "total_hops": 3,
        "pattern_type": "FAN_OUT"
    }

    for t in [tx_3a, tx_3b, tx_3c, tx_3d, tx_3e]:
        store["transactions"][t["tx_id"]] = t

    store["cases"][case_3_id] = {
        "case_id": case_3_id,
        "chain_id": chain_3_id,
        "status": "HIGH_RISK",
        "risk_level": 85.0,
        "primary_tx_id": tx_3a_id,
        "total_fraud_amount": 526000.0,
        "recoverable_amount": 170000.0,
        "origin_account": s3,
        "chain": [s3, hub3, m3a, m3b, exit3a, exit3b],
        "transactions": [tx_3a_id, tx_3b_id, tx_3c_id, tx_3d_id, tx_3e_id],
        "actions_taken": [],
        "timeline": [{"at": now, "event": "case_created", "actor": "system"}]
    }

    # =========================================================================
    # SCENARIO 4: HIGH-RISK 6-NODE LAYERED FRAUD CHAIN (6 Nodes · 5 Flows)
    # =========================================================================
    case_4_id = "CASE-FRAUD-600"
    chain_4_id = "CHAIN-FRAUD-600"
    v4 = "ACC-USR-1004"
    m4_1 = "ACC-MULE-6001"
    m4_2 = "ACC-MULE-6002"
    upi4 = "UPI-HANDLE-6003"
    cash4 = "CASHOUT-TERM-6004"
    merch4 = "ACC-MERCH-6005"

    tx_4a_id = "TX-FRAUD-6001"
    tx_4b_id = "TX-FRAUD-6002"
    tx_4c_id = "TX-FRAUD-6003"
    tx_4d_id = "TX-FRAUD-6004"
    tx_4e_id = "TX-FRAUD-6005"

    store["accounts"][v4] = {
        "account_id": v4,
        "account_type": "SOURCE",
        "node_type": "victim",
        "status": "active",
        "current_balance_sim": 450000.0,
        "risk_score": 15.0
    }
    store["accounts"][m4_1] = {
        "account_id": m4_1,
        "account_type": "MULE",
        "node_type": "mule",
        "status": "active",
        "current_balance_sim": 280000.0,
        "risk_score": 82.0
    }
    store["accounts"][m4_2] = {
        "account_id": m4_2,
        "account_type": "MULE",
        "node_type": "mule",
        "status": "active",
        "current_balance_sim": 270000.0,
        "risk_score": 86.0
    }
    store["accounts"][upi4] = {
        "account_id": upi4,
        "account_type": "INTERMEDIARY",
        "node_type": "UPI",
        "status": "active",
        "current_balance_sim": 260000.0,
        "risk_score": 90.0
    }
    store["accounts"][cash4] = {
        "account_id": cash4,
        "account_type": "DESTINATION",
        "node_type": "cashout",
        "status": "flagged",
        "current_balance_sim": 250000.0,
        "risk_score": 95.0
    }
    store["accounts"][merch4] = {
        "account_id": merch4,
        "account_type": "DESTINATION",
        "node_type": "merchant",
        "status": "flagged",
        "current_balance_sim": 240000.0,
        "risk_score": 98.0
    }

    tx_4a = {
        "tx_id": tx_4a_id,
        "timestamp": now,
        "case_id": case_4_id,
        "chain_id": chain_4_id,
        "root_transaction_id": tx_4a_id,
        "sender_account": v4,
        "receiver_account": m4_1,
        "amount": 280000.0,
        "currency": "INR",
        "channel": "NEFT",
        "risk_score": 82,
        "hop_number": 1,
        "total_hops": 5,
        "pattern_type": "MULE_CHAIN"
    }
    tx_4b = {
        "tx_id": tx_4b_id,
        "timestamp": now,
        "case_id": case_4_id,
        "chain_id": chain_4_id,
        "root_transaction_id": tx_4a_id,
        "parent_transaction_id": tx_4a_id,
        "sender_account": m4_1,
        "receiver_account": m4_2,
        "amount": 270000.0,
        "currency": "INR",
        "channel": "IMPS",
        "risk_score": 86,
        "hop_number": 2,
        "total_hops": 5,
        "pattern_type": "MULE_CHAIN"
    }
    tx_4c = {
        "tx_id": tx_4c_id,
        "timestamp": now,
        "case_id": case_4_id,
        "chain_id": chain_4_id,
        "root_transaction_id": tx_4a_id,
        "parent_transaction_id": tx_4b_id,
        "sender_account": m4_2,
        "receiver_account": upi4,
        "amount": 260000.0,
        "currency": "INR",
        "channel": "UPI",
        "risk_score": 90,
        "hop_number": 3,
        "total_hops": 5,
        "pattern_type": "MULE_CHAIN"
    }
    tx_4d = {
        "tx_id": tx_4d_id,
        "timestamp": now,
        "case_id": case_4_id,
        "chain_id": chain_4_id,
        "root_transaction_id": tx_4a_id,
        "parent_transaction_id": tx_4c_id,
        "sender_account": upi4,
        "receiver_account": cash4,
        "amount": 250000.0,
        "currency": "INR",
        "channel": "CARD",
        "risk_score": 95,
        "hop_number": 4,
        "total_hops": 5,
        "pattern_type": "MULE_CHAIN"
    }
    tx_4e = {
        "tx_id": tx_4e_id,
        "timestamp": now,
        "case_id": case_4_id,
        "chain_id": chain_4_id,
        "root_transaction_id": tx_4a_id,
        "parent_transaction_id": tx_4d_id,
        "sender_account": cash4,
        "receiver_account": merch4,
        "amount": 240000.0,
        "currency": "INR",
        "channel": "NEFT",
        "risk_score": 98,
        "hop_number": 5,
        "total_hops": 5,
        "pattern_type": "MULE_CHAIN"
    }

    for t in [tx_4a, tx_4b, tx_4c, tx_4d, tx_4e]:
        store["transactions"][t["tx_id"]] = t

    store["cases"][case_4_id] = {
        "case_id": case_4_id,
        "chain_id": chain_4_id,
        "status": "HIGH_RISK",
        "risk_level": 98.0,
        "primary_tx_id": tx_4a_id,
        "total_fraud_amount": 1300000.0,
        "recoverable_amount": 240000.0,
        "origin_account": v4,
        "chain": [v4, m4_1, m4_2, upi4, cash4, merch4],
        "transactions": [tx_4a_id, tx_4b_id, tx_4c_id, tx_4d_id, tx_4e_id],
        "actions_taken": [],
        "timeline": [{"at": now, "event": "case_created", "actor": "system"}]
    }
