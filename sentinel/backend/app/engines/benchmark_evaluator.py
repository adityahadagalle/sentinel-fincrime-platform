"""
SENTINEL Benchmark Lab — Pure, Deterministic, and Side-Effect Free Risk Evaluator.

Enforces strict architectural separation between:
1. Live/Production processing (stateful, mutates accounts/cases/graphs/actions)
2. Benchmark/Risk evaluation (pure function of an immutable evaluation snapshot)

Guarantees that repeated evaluation of the identical transaction input produces
exact identical scores, factor values, ML noise, and policy decisions without mutating
global store state.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import copy
import logging
import math
from typing import Any, Dict, List, Optional

from app.engines.scoring_engine import score_transaction
from app.services.ml_risk_engine import predict_ml_score, feature_names
from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
from app.services.reasoning_engine import generate_reasoning

logger = logging.getLogger("sentinel.benchmark.evaluator")

EVALUATION_VERSION = "2.0.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class EvaluationInputSnapshot:
    """
    Immutable evaluation snapshot containing every normalized value required for scoring.
    Acts as the single source of truth for benchmark evaluations.
    """
    tx_id: str
    benchmark_run_id: str
    benchmark_profile: str
    amount: float
    currency: str
    timestamp: str
    channel: str
    sender_account: str
    receiver_account: str
    avg_monthly_tx_amount: float
    is_new_receiver: bool
    on_active_call: bool
    hop_number: int
    origin_score: Optional[float]
    velocity_flag: bool = False
    is_cross_border: bool = False
    device_changed: bool = False
    location_changed: bool = False
    bulk_transfer_flag: bool = False
    is_crypto_related: bool = False
    is_remote_access_active: bool = False
    is_scripted: bool = False
    new_payee_added: bool = False
    is_first_time_payee: bool = False
    chain_id: Optional[str] = None
    total_hops: Optional[int] = None
    simulator_meta: Dict[str, Any] = field(default_factory=dict)
    seed: str = ""
    evaluation_version: str = EVALUATION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Ensure simulator_meta is deep-copied
        d["simulator_meta"] = copy.deepcopy(self.simulator_meta)
        return d


def build_evaluation_snapshot(
    tx: Dict[str, Any],
    run_id: Optional[str] = None,
    seed: Optional[str] = None,
    account_baseline: Optional[Dict[str, Any]] = None,
) -> EvaluationInputSnapshot:
    """
    Constructs a normalized, immutable evaluation snapshot from a transaction payload.
    
    Derives 'is_new_receiver' once at snapshot construction time:
    - If simulator_meta contains 'is_new_receiver', respects it.
    - Else if tx contains 'is_new_receiver', respects it.
    - Else if account_baseline contains 'is_new_receiver', respects it.
    - Else falls back to False.
    
    The derived value is permanently frozen into the snapshot so mutable account
    state can never alter subsequent evaluations.
    """
    effective_run_id = (
        run_id
        or tx.get("benchmark_run_id")
        or "BM-DEFAULT"
    )
    effective_tx_id = str(tx.get("tx_id") or f"TX-{effective_run_id}-0001")

    # ML seed derivation: stable run_id + tx_id identifier
    if seed:
        effective_seed = seed
    elif tx.get("benchmark_seed"):
        effective_seed = str(tx["benchmark_seed"])
    elif tx.get("seed"):
        effective_seed = str(tx["seed"])
    else:
        effective_seed = f"{effective_run_id}:{effective_tx_id}"

    # Determine is_new_receiver strictly once
    sim_meta = copy.deepcopy(tx.get("simulator_meta") or {})
    if "is_new_receiver" in sim_meta:
        is_new_receiver = bool(sim_meta["is_new_receiver"])
    elif "is_new_receiver" in tx:
        is_new_receiver = bool(tx["is_new_receiver"])
    elif account_baseline and "is_new_receiver" in account_baseline:
        is_new_receiver = bool(account_baseline["is_new_receiver"])
    else:
        is_new_receiver = False

    # Freeze is_new_receiver into simulator_meta as well
    sim_meta["is_new_receiver"] = is_new_receiver

    # Sender account baseline monthly average
    avg_monthly = 25000.0
    if account_baseline and "avg_monthly_tx_amount" in account_baseline:
        avg_monthly = float(account_baseline["avg_monthly_tx_amount"])
    elif "avg_monthly_tx_amount" in tx:
        avg_monthly = float(tx["avg_monthly_tx_amount"])

    # Origin score for multi-hop
    origin_score_raw = tx.get("origin_score")
    origin_score = float(origin_score_raw) if origin_score_raw is not None else None

    return EvaluationInputSnapshot(
        tx_id=effective_tx_id,
        benchmark_run_id=effective_run_id,
        benchmark_profile=str(tx.get("benchmark_profile") or "BASELINE"),
        amount=float(tx.get("amount", 2500.0)),
        currency=str(tx.get("currency") or "INR"),
        timestamp=str(tx.get("timestamp") or _now_iso()),
        channel=str(tx.get("channel") or "UPI"),
        sender_account=str(tx.get("sender_account") or "ACC-BM-SENDER"),
        receiver_account=str(tx.get("receiver_account") or "ACC-BM-RECEIVER"),
        avg_monthly_tx_amount=avg_monthly,
        is_new_receiver=is_new_receiver,
        on_active_call=bool(tx.get("on_active_call", False)),
        hop_number=int(tx.get("hop_number", 0)),
        origin_score=origin_score,
        velocity_flag=bool(tx.get("velocity_flag", False)),
        is_cross_border=bool(tx.get("is_cross_border", False)),
        device_changed=bool(tx.get("device_changed", False)),
        location_changed=bool(tx.get("location_changed", False)),
        bulk_transfer_flag=bool(tx.get("bulk_transfer_flag", False)),
        is_crypto_related=bool(tx.get("is_crypto_related", False)),
        is_remote_access_active=bool(tx.get("is_remote_access_active", False)),
        is_scripted=bool(tx.get("is_scripted", False)),
        new_payee_added=bool(tx.get("new_payee_added", False)),
        is_first_time_payee=bool(tx.get("is_first_time_payee", False)),
        chain_id=tx.get("chain_id"),
        total_hops=tx.get("total_hops"),
        simulator_meta=sim_meta,
        seed=effective_seed,
        evaluation_version=EVALUATION_VERSION,
    )


def evaluate_benchmark_transaction_pure(
    snapshot: EvaluationInputSnapshot,
) -> Dict[str, Any]:
    """
    Pure, deterministic evaluation of a benchmark transaction.
    
    Guarantees:
    - Pure function: snapshot -> result
    - ZERO global state mutation (no data_store accounts, transactions, cases, graphs, actions modified)
    - Deterministic ML emulator using snapshot.seed
    - Formula: final_score = floor(0.60 * ml_score + 0.40 * rule_score)
    - Tiers: LOW < 40, MEDIUM = 40-69, HIGH = 70-84, CRITICAL >= 85
    - Policy isolation: Autonomous policy engine evaluates actions without executing them
    - FREEZE human operator boundary preserved (requires_operator_action = True)
    """
    # 1. Build completely isolated evaluation payloads
    eval_tx: Dict[str, Any] = {
        "tx_id": snapshot.tx_id,
        "benchmark_run_id": snapshot.benchmark_run_id,
        "benchmark_profile": snapshot.benchmark_profile,
        "amount": snapshot.amount,
        "currency": snapshot.currency,
        "timestamp": snapshot.timestamp,
        "channel": snapshot.channel,
        "sender_account": snapshot.sender_account,
        "receiver_account": snapshot.receiver_account,
        "hop_number": snapshot.hop_number,
        "on_active_call": snapshot.on_active_call,
        "velocity_flag": snapshot.velocity_flag,
        "is_cross_border": snapshot.is_cross_border,
        "device_changed": snapshot.device_changed,
        "location_changed": snapshot.location_changed,
        "bulk_transfer_flag": snapshot.bulk_transfer_flag,
        "is_crypto_related": snapshot.is_crypto_related,
        "is_remote_access_active": snapshot.is_remote_access_active,
        "is_scripted": snapshot.is_scripted,
        "new_payee_added": snapshot.new_payee_added,
        "is_first_time_payee": snapshot.is_first_time_payee,
        "chain_id": snapshot.chain_id,
        "total_hops": snapshot.total_hops,
        "simulator_meta": copy.deepcopy(snapshot.simulator_meta),
    }

    if snapshot.origin_score is not None:
        eval_tx["origin_score"] = snapshot.origin_score

    eval_account: Dict[str, Any] = {
        "account_id": snapshot.sender_account,
        "avg_monthly_tx_amount": snapshot.avg_monthly_tx_amount,
        "is_new_receiver": snapshot.is_new_receiver,
        "status": "active",
        "kyc_status": "VERIFIED",
    }

    # 2. Rule-Based Scoring Engine
    score_output = score_transaction(eval_tx, eval_account)
    rule_score = float(score_output.get("risk_score", 0.0))

    # 3. Deterministic ML Emulator
    ml_score = predict_ml_score(rule_score, seed=snapshot.seed)

    # 4. Hybrid Fusion: final_score = floor(0.60 * ml_score + 0.40 * rule_score)
    final_score = int(math.floor(0.60 * ml_score + 0.40 * rule_score))

    # 5. Risk Tier Classification
    # LOW < 40, MEDIUM = 40-69, HIGH = 70-84, CRITICAL >= 85
    if final_score >= 85:
        risk_level = "CRITICAL"
        threshold = "CRITICAL"
    elif final_score >= 70:
        risk_level = "HIGH"
        threshold = "HIGH_RISK"
    elif final_score >= 40:
        risk_level = "MEDIUM"
        threshold = "MEDIUM"
    else:
        risk_level = "LOW"
        threshold = "LOW"

    # 6. Dynamic Feature Importance & Explainability (Deterministic)
    risk_factors = score_output.get("risk_factors", [])
    name_map = {
        "new_receiver": "is_new_receiver",
        "amount_deviation": "amount",
        "time_anomaly": "hour",
        "call_flag": "call_flag",
        "velocity_spike": "velocity",
        "bulk_transfer": "chain_depth",
        "cross_border_risk": "amount",
        "device_anomaly": "is_new_receiver",
        "crypto_risk": "call_flag",
        "remote_access": "call_flag",
        "scripted_behavior": "call_flag",
        "first_time_payee": "is_new_receiver",
    }

    raw = {fn: 0.0 for fn in feature_names}
    for f in risk_factors:
        mapped = name_map.get(f.get("name"), None)
        if mapped and mapped in raw:
            raw[mapped] += float(f.get("contribution", 0.0))

    # Normalized input signal component
    try:
        from datetime import datetime as _dt
        ts = snapshot.timestamp
        try:
            dt = _dt.fromisoformat(ts.replace("Z", "+00:00"))
            hour_val = dt.hour / 23.0
        except Exception:
            hour_val = 0.5

        amount_val = min(snapshot.amount / 500000.0, 1.0)
        velocity_val = 1.0 if snapshot.velocity_flag else 0.08
        is_new_val = 1.0 if snapshot.is_new_receiver else 0.08
        call_val = 1.0 if snapshot.on_active_call else 0.04
        hop_val = min(float(snapshot.hop_number) / 5.0, 1.0)

        SIGNAL_SCALE = 5.0
        raw["amount"] += amount_val * SIGNAL_SCALE
        raw["hour"] += hour_val * SIGNAL_SCALE
        raw["is_new_receiver"] += is_new_val * SIGNAL_SCALE
        raw["velocity"] += velocity_val * SIGNAL_SCALE
        raw["call_flag"] += call_val * SIGNAL_SCALE
        raw["chain_depth"] += hop_val * SIGNAL_SCALE
    except Exception:
        pass

    total_raw = sum(raw.values())
    if total_raw > 0:
        importance = {k: round(v / total_raw, 4) for k, v in raw.items()}
    else:
        importance = {fn: round(1.0 / len(feature_names), 4) for fn in feature_names}

    ml_feature_importance = dict(
        sorted(importance.items(), key=lambda x: x[1], reverse=True)
    )

    reason_data = generate_reasoning(risk_factors)
    short_reason = reason_data.get("short_reason", "")
    full_reason = reason_data.get("full_reason", "")

    # 7. Autonomous Policy Engine (Isolated Evaluation, NO Execution)
    eval_tx_for_policy = copy.deepcopy(eval_tx)
    eval_tx_for_policy["risk_score"] = final_score
    eval_tx_for_policy["risk_level"] = risk_level
    eval_tx_for_policy["threshold"] = threshold

    policy_decision = evaluate_autonomous_policy(
        tx=eval_tx_for_policy,
        case=None,
        automate_mode=True,
    )

    policy_action = policy_decision.get("action", "MONITOR")
    policy_rule_id = policy_decision.get("policy_rule_id", "POL-DEFAULT")
    policy_decision_val = policy_decision.get("decision", "EXECUTE")

    # Action Isolation: Benchmark evaluation NEVER executes real state changes
    # Preserve Human Operator Sign-Off Boundary for FREEZE
    if policy_action == "FREEZE":
        execution_status = "REQUIRES_OPERATOR_ACTION"
        requires_operator_action = True
    else:
        execution_status = "SIMULATED_SUCCESS"
        requires_operator_action = False

    simulated_execution_record = {
        "execution_status": execution_status,
        "actor_type": "HUMAN_OPERATOR" if requires_operator_action else "AUTOMATION_ENGINE",
        "action_code": policy_action,
        "policy_decision": policy_decision,
        "simulated": True,
        "boundary_enforced": True,
    }

    eval_timestamp = _now_iso()

    # 8. Structured Diagnostic Debug Logging
    logger.debug(
        "Benchmark Eval | run_id=%s tx_id=%s version=%s rule_score=%.1f ml_score=%.1f "
        "final_score=%d risk_level=%s is_new_receiver=%s on_active_call=%s hop_number=%d seed=%s",
        snapshot.benchmark_run_id,
        snapshot.tx_id,
        snapshot.evaluation_version,
        rule_score,
        ml_score,
        final_score,
        risk_level,
        snapshot.is_new_receiver,
        snapshot.on_active_call,
        snapshot.hop_number,
        snapshot.seed,
    )

    # 9. Return Complete Structured Result
    return {
        "rule_score": rule_score,
        "ml_score": ml_score,
        "final_score": final_score,
        "risk_score": float(final_score),
        "risk_level": risk_level,
        "threshold": threshold,
        "factor_breakdown": {
            "risk_factors": risk_factors,
            "ml_feature_importance": ml_feature_importance,
            "top_reason": score_output.get("top_reason", ""),
        },
        "risk_factors": risk_factors,
        "ml_feature_importance": ml_feature_importance,
        "policy_action": policy_action,
        "policy_decision": policy_decision_val,
        "policy_rule_id": policy_rule_id,
        "policy_decision_details": policy_decision,
        "execution_status": execution_status,
        "requires_operator_action": requires_operator_action,
        "execution_record": simulated_execution_record,
        "reason": short_reason or score_output.get("top_reason", ""),
        "full_reason": full_reason,
        "confidence": "HIGH" if final_score >= 70 else "MEDIUM" if final_score >= 40 else "LOW",
        "evaluation_inputs": snapshot.to_dict(),
        "evaluation_version": snapshot.evaluation_version,
        "deterministic_seed": snapshot.seed,
        "timestamp": eval_timestamp,
    }
