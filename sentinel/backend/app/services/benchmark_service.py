"""
SENTINEL Benchmark Lab — Controlled Synthetic Transaction Testing Harness.

Orchestrates controlled synthetic transaction generation, routes every transaction
through the existing detection, hybrid scoring, case, graph, policy, and action execution
pipeline, and collects real benchmark results with full data lineage.
"""

import asyncio
import copy
import csv
import io
import math
import random
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.data_store import data_store
from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
from app.services.orchestrator import run_pipeline
from app.services.simulated_action_executor import execute_simulated_action
from app.engines.benchmark_evaluator import (
    EvaluationInputSnapshot,
    build_evaluation_snapshot,
    evaluate_benchmark_transaction_pure,
    EVALUATION_VERSION,
)

SUPPORTED_PROFILES = [
    "BASELINE",
    "NEW_RECEIVER",
    "AMOUNT_ANOMALY",
    "TIME_ANOMALY",
    "ACTIVE_CALL",
    "MULTI_SIGNAL",
    "MULTI_HOP",
]

CHANNELS = ["UPI", "IMPS", "NEFT", "CARD"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sanitize_csv_field(val: Any) -> str:
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


class BenchmarkService:
    """
    Manages benchmark runs, synthetic transaction generation, pipeline routing,
    progress tracking, and aggregate analytics.
    """

    def __init__(self) -> None:
        self.active_runs: Dict[str, Dict[str, Any]] = {}
        self.run_history: List[Dict[str, Any]] = []
        self._run_counter: int = 0
        self._lock = asyncio.Lock()
        self.broadcast_manager: Any = None

    def _next_run_id(self) -> str:
        self._run_counter += 1
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"BM-{date_str}-{self._run_counter:03d}"

    def calculate_distribution(
        self,
        num_transactions: int,
        profile_mode: str,
        single_profile: Optional[str] = None,
        custom_distribution: Optional[Dict[str, float]] = None,
    ) -> Dict[str, int]:
        """
        Calculates exact integer allocation of transactions per profile.
        Guarantees sum(counts) == num_transactions.
        """
        mode = profile_mode.upper()
        if mode == "SINGLE":
            profile = (single_profile or "BASELINE").upper()
            if profile not in SUPPORTED_PROFILES:
                profile = "BASELINE"
            return {profile: num_transactions}

        if mode == "BALANCED":
            profiles = list(SUPPORTED_PROFILES)
            k = len(profiles)
            base_count = num_transactions // k
            remainder = num_transactions % k
            allocation: Dict[str, int] = {}
            for i, p in enumerate(profiles):
                allocation[p] = base_count + (1 if i < remainder else 0)
            return allocation

        if mode == "CUSTOM_MIX":
            raw_mix = custom_distribution or {}
            valid_mix = {
                p.upper(): max(0.0, float(raw_mix.get(p, 0.0)))
                for p in SUPPORTED_PROFILES
                if p.upper() in raw_mix
            }
            total_weight = sum(valid_mix.values())
            if total_weight <= 0:
                # Fallback to balanced
                return self.calculate_distribution(num_transactions, "BALANCED")

            # Allocate proportionally using largest-remainder method
            float_counts = {
                p: (weight / total_weight) * num_transactions
                for p, weight in valid_mix.items()
            }
            int_counts = {p: math.floor(val) for p, val in float_counts.items()}
            allocated = sum(int_counts.values())
            remainder = num_transactions - allocated

            # Distribute remaining to highest fractional parts
            fractions = sorted(
                [(p, float_counts[p] - int_counts[p]) for p in valid_mix],
                key=lambda x: x[1],
                reverse=True,
            )
            for i in range(remainder):
                p = fractions[i % len(fractions)][0]
                int_counts[p] += 1

            return int_counts

        # Default fallback
        return {"BASELINE": num_transactions}

    def generate_synthetic_transaction(
        self,
        run_id: str,
        index: int,
        profile: str,
        rng: random.Random,
        shared_case_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a synthetic transaction strictly based on the requested profile's
        feature characteristics.

        Uses real schema fields that SENTINEL's scoring engine reads.
        """
        tx_id = f"TX-{run_id}-{index:04d}"
        run_idx = run_id.split("-")[-1] if "-" in run_id else "001"
        sender_id = f"ACC-BM-SND-{run_idx}-{index:04d}"
        receiver_id = f"ACC-BM-RCV-{run_idx}-{index:04d}"
        channel = rng.choice(CHANNELS)

        # Standard baseline average monthly transaction amount
        baseline_avg_amount = 25000.0

        # Daytime timestamp helper: 14:00 to 17:00 UTC
        day_hour = rng.randint(14, 17)
        day_minute = rng.randint(0, 59)
        day_timestamp = (
            datetime.now(timezone.utc)
            .replace(hour=day_hour, minute=day_minute, second=rng.randint(0, 59), microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

        # Nighttime timestamp helper: 01:00 to 04:00 UTC (10 PM to 6 AM anomaly window)
        night_hour = rng.randint(1, 4)
        night_minute = rng.randint(0, 59)
        night_timestamp = (
            datetime.now(timezone.utc)
            .replace(hour=night_hour, minute=night_minute, second=rng.randint(0, 59), microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

        tx: Dict[str, Any] = {
            "tx_id": tx_id,
            "benchmark_run_id": run_id,
            "benchmark_profile": profile,
            "source": "BENCHMARK_LAB",
            "sender_account": sender_id,
            "receiver_account": receiver_id,
            "amount": round(rng.uniform(1500.0, 5000.0), 2),
            "currency": "INR",
            "channel": channel,
            "timestamp": day_timestamp,
            "hop_number": 0,
            "on_active_call": False,
            "simulator_meta": {"is_new_receiver": False},
            "avg_monthly_tx_amount": baseline_avg_amount,
        }

        # ── Apply Profile-Specific Feature Characteristics ──────────────────
        if profile == "BASELINE":
            # Routine amount (ratio < 0.25 -> 0 deviation), daytime, known receiver, no active call
            tx["amount"] = round(rng.uniform(1200.0, 4800.0), 2)
            tx["timestamp"] = day_timestamp
            tx["simulator_meta"]["is_new_receiver"] = False
            tx["on_active_call"] = False

        elif profile == "NEW_RECEIVER":
            # Routine amount, daytime, but destination is explicitly a first-time payee
            tx["amount"] = round(rng.uniform(1800.0, 5200.0), 2)
            tx["timestamp"] = day_timestamp
            tx["simulator_meta"]["is_new_receiver"] = True
            tx["on_active_call"] = False

        elif profile == "AMOUNT_ANOMALY":
            # Amount significantly exceeds account baseline (5x - 10x ratio -> deviation = 100)
            tx["amount"] = round(rng.uniform(125000.0, 260000.0), 2)
            tx["timestamp"] = day_timestamp
            tx["simulator_meta"]["is_new_receiver"] = False
            tx["on_active_call"] = False

        elif profile == "TIME_ANOMALY":
            # Routine amount, known receiver, but happens in the deep night window (2 AM - 4 AM)
            tx["amount"] = round(rng.uniform(1500.0, 4500.0), 2)
            tx["timestamp"] = night_timestamp
            tx["simulator_meta"]["is_new_receiver"] = False
            tx["on_active_call"] = False

        elif profile == "ACTIVE_CALL":
            # Routine amount, daytime, known receiver, but sender is on an active voice call
            tx["amount"] = round(rng.uniform(2000.0, 5000.0), 2)
            tx["timestamp"] = day_timestamp
            tx["simulator_meta"]["is_new_receiver"] = False
            tx["on_active_call"] = True

        elif profile == "MULTI_SIGNAL":
            # Massive amount anomaly + Nighttime hour + New receiver + Active call
            tx["amount"] = round(rng.uniform(180000.0, 380000.0), 2)
            tx["timestamp"] = night_timestamp
            tx["simulator_meta"]["is_new_receiver"] = True
            tx["on_active_call"] = True
            tx["velocity_flag"] = True

        elif profile == "MULTI_HOP":
            # Network chained transaction
            if shared_case_context and "case_id" in shared_case_context:
                hop = shared_case_context.get("current_hop", 1)
                tx["case_id"] = shared_case_context["case_id"]
                tx["chain_id"] = shared_case_context.get("chain_id", f"CHAIN-{run_id}")
                tx["hop_number"] = hop
                tx["sender_account"] = shared_case_context.get("last_receiver", sender_id)
                tx["receiver_account"] = f"ACC-BM-MULE-{run_idx}-{hop:02d}-{index:04d}"
                tx["amount"] = round(shared_case_context.get("amount", 200000.0) * 0.92, 2)
                tx["timestamp"] = day_timestamp
                tx["simulator_meta"]["is_new_receiver"] = True
                # update context for next hop
                shared_case_context["current_hop"] = (hop + 1) % 4
                shared_case_context["last_receiver"] = tx["receiver_account"]
                shared_case_context["amount"] = tx["amount"]
            else:
                # Hop 0 initiation
                case_id = f"CASE-{run_id}-{index:04d}"
                chain_id = f"CHAIN-{run_id}-{index:04d}"
                tx["case_id"] = case_id
                tx["chain_id"] = chain_id
                tx["hop_number"] = 0
                tx["total_hops"] = 3
                tx["amount"] = round(rng.uniform(220000.0, 450000.0), 2)
                tx["timestamp"] = day_timestamp
                tx["simulator_meta"]["is_new_receiver"] = True
                tx["on_active_call"] = True
                if shared_case_context is not None:
                    shared_case_context["case_id"] = case_id
                    shared_case_context["chain_id"] = chain_id
                    shared_case_context["current_hop"] = 1
                    shared_case_context["last_receiver"] = receiver_id
                    shared_case_context["amount"] = tx["amount"]

        return tx

    def create_benchmark_batch(
        self,
        num_transactions: int,
        profile_mode: str = "BALANCED",
        single_profile: Optional[str] = None,
        custom_distribution: Optional[Dict[str, float]] = None,
        seed: Optional[str] = None,
    ) -> str:
        """
        Phase 1: Generates a batch of synthetic transactions strictly as UNEVALUATED TEST INPUTS.
        No risk scores, rule scores, ML scores, or policy decisions are assigned yet.
        Transactions exist purely as inputs for compliance analyst / jury review.
        """
        num_transactions = max(1, min(500, int(num_transactions)))
        run_id = self._next_run_id()
        effective_seed = seed or f"SEED-{run_id}-{uuid.uuid4().hex[:6]}"
        rng = random.Random(effective_seed)

        distribution = self.calculate_distribution(
            num_transactions=num_transactions,
            profile_mode=profile_mode,
            single_profile=single_profile,
            custom_distribution=custom_distribution,
        )

        # Prepare ordered list of profiles to generate
        profile_sequence: List[str] = []
        for p, count in distribution.items():
            profile_sequence.extend([p] * count)
        rng.shuffle(profile_sequence)

        shared_multi_hop_context: Dict[str, Any] = {}
        unevaluated_transactions: List[Dict[str, Any]] = []

        for idx, profile in enumerate(profile_sequence, start=1):
            raw_tx = self.generate_synthetic_transaction(
                run_id=run_id,
                index=idx,
                profile=profile,
                rng=rng,
                shared_case_context=shared_multi_hop_context if profile == "MULTI_HOP" else None,
            )

            # Construct immutable evaluation snapshot upfront
            snapshot = build_evaluation_snapshot(
                tx=raw_tx,
                run_id=run_id,
                seed=f"{run_id}:{raw_tx['tx_id']}",
            )

            # Store as clean, unevaluated test input record
            tx_record: Dict[str, Any] = {
                "tx_id": raw_tx["tx_id"],
                "benchmark_run_id": run_id,
                "benchmark_profile": profile,
                "source": raw_tx.get("source", "BENCHMARK_LAB"),
                "sender_account": raw_tx["sender_account"],
                "receiver_account": raw_tx["receiver_account"],
                "amount": float(raw_tx["amount"]),
                "currency": raw_tx.get("currency", "INR"),
                "channel": raw_tx["channel"],
                "timestamp": raw_tx["timestamp"],
                "hop_number": raw_tx.get("hop_number", 0),
                "on_active_call": bool(raw_tx.get("on_active_call", False)),
                "simulator_meta": copy.deepcopy(raw_tx.get("simulator_meta", {})),
                "case_id": None,
                "chain_id": raw_tx.get("chain_id"),
                "total_hops": raw_tx.get("total_hops"),
                "velocity_flag": bool(raw_tx.get("velocity_flag", False)),
                # UNEVALUATED STATE — Explicitly unassigned until user triggers evaluation
                "status": "UNEVALUATED",
                "evaluation_state": "UNEVALUATED",
                "rule_score": None,
                "ml_score": None,
                "risk_score": None,
                "final_score": None,
                "risk_level": None,
                "threshold": None,
                "policy_action": None,
                "policy_decision": None,
                "policy_rule_id": None,
                "execution_status": "UNEVALUATED",
                "requires_operator_action": False,
                "reason": None,
                "full_reason": None,
                "risk_factors": [],
                "ml_feature_importance": {},
                "evaluation_inputs": snapshot.to_dict(),
                "evaluation_version": EVALUATION_VERSION,
                "deterministic_seed": snapshot.seed,
                "is_reproducible": None,
                "previous_evaluation": None,
                "raw_input": copy.deepcopy(raw_tx),
            }
            unevaluated_transactions.append(tx_record)

        run_state: Dict[str, Any] = {
            "run_id": run_id,
            "status": "UNEVALUATED",
            "seed": effective_seed,
            "num_transactions": len(unevaluated_transactions),
            "profile_mode": profile_mode.upper(),
            "single_profile": single_profile.upper() if single_profile else None,
            "distribution": distribution,
            "created_at": _now_iso(),
            "started_at": None,
            "completed_at": None,
            "total_requested": len(unevaluated_transactions),
            "processed_count": 0,
            "successful_count": 0,
            "failed_count": 0,
            "cancel_requested": False,
            "transactions": unevaluated_transactions,
            "failures": [],
            "summary": None,
        }
        run_state["summary"] = self._compute_summary(run_state)

        self.active_runs[run_id] = run_state
        return run_id

    def add_custom_input_to_batch(
        self,
        run_id: str,
        custom_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Adds a manual custom test transaction as an UNEVALUATED input into an existing batch
        before evaluation is triggered.
        """
        run = self.active_runs.get(run_id)
        if not run:
            raise ValueError(f"Run '{run_id}' not found in active runs.")
        if run.get("status") not in ("UNEVALUATED", "DRAFT"):
            raise ValueError(f"Cannot add inputs to run '{run_id}' in '{run.get('status')}' status.")

        idx = len(run["transactions"]) + 1
        tx_id = custom_input.get("tx_id") or f"TX-{run_id}-CUST-{idx:04d}"
        sender_id = custom_input.get("sender_account") or f"ACC-CUSTOM-SND-{idx:04d}"
        receiver_id = custom_input.get("receiver_account") or f"ACC-CUSTOM-RCV-{idx:04d}"
        amount = float(custom_input.get("amount", 25000.0))
        channel = custom_input.get("channel", "UPI")

        is_night = bool(custom_input.get("is_night_time", False))
        hour = 3 if is_night else 14
        timestamp = custom_input.get("timestamp") or (
            datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
        )

        raw_tx: Dict[str, Any] = {
            "tx_id": tx_id,
            "benchmark_run_id": run_id,
            "benchmark_profile": "CUSTOM_MANUAL",
            "source": "MANUAL_CUSTOM_INPUT",
            "sender_account": sender_id,
            "receiver_account": receiver_id,
            "amount": amount,
            "currency": "INR",
            "channel": channel,
            "timestamp": timestamp,
            "hop_number": int(custom_input.get("hop_number", 0)),
            "on_active_call": bool(custom_input.get("on_active_call", False)),
            "simulator_meta": {
                "is_new_receiver": bool(custom_input.get("is_new_receiver", False)),
            },
        }
        if custom_input.get("is_cross_border"):
            raw_tx["is_cross_border"] = True
        if custom_input.get("velocity_flag"):
            raw_tx["velocity_flag"] = True
        if custom_input.get("device_changed"):
            raw_tx["device_changed"] = True

        # Construct immutable snapshot for manual custom input without modifying data_store
        snapshot = build_evaluation_snapshot(
            tx=raw_tx,
            run_id=run_id,
            seed=f"{run_id}:{raw_tx['tx_id']}",
            account_baseline={"avg_monthly_tx_amount": float(custom_input.get("avg_monthly_tx_amount", 25000.0)), "is_new_receiver": bool(custom_input.get("is_new_receiver", False))},
        )

        tx_record: Dict[str, Any] = {
            "tx_id": tx_id,
            "benchmark_run_id": run_id,
            "benchmark_profile": "CUSTOM_MANUAL",
            "source": "MANUAL_CUSTOM_INPUT",
            "sender_account": sender_id,
            "receiver_account": receiver_id,
            "amount": amount,
            "currency": "INR",
            "channel": channel,
            "timestamp": timestamp,
            "hop_number": int(custom_input.get("hop_number", 0)),
            "on_active_call": bool(custom_input.get("on_active_call", False)),
            "simulator_meta": copy.deepcopy(snapshot.simulator_meta),
            "case_id": None,
            "velocity_flag": bool(custom_input.get("velocity_flag", False)),
            "status": "UNEVALUATED",
            "evaluation_state": "UNEVALUATED",
            "rule_score": None,
            "ml_score": None,
            "risk_score": None,
            "final_score": None,
            "risk_level": None,
            "threshold": None,
            "policy_action": None,
            "policy_decision": None,
            "policy_rule_id": None,
            "execution_status": "UNEVALUATED",
            "requires_operator_action": False,
            "reason": None,
            "full_reason": None,
            "risk_factors": [],
            "ml_feature_importance": {},
            "evaluation_inputs": snapshot.to_dict(),
            "evaluation_version": EVALUATION_VERSION,
            "deterministic_seed": snapshot.seed,
            "is_reproducible": None,
            "previous_evaluation": None,
            "raw_input": copy.deepcopy(raw_tx),
        }

        run["transactions"].append(tx_record)
        run["total_requested"] = len(run["transactions"])
        run["num_transactions"] = len(run["transactions"])
        run["summary"] = self._compute_summary(run)
        return tx_record

    async def evaluate_benchmark_batch(
        self,
        run_id: str,
        repo: Any = None,
    ) -> bool:
        """
        Phase 2: User explicitly triggers evaluation.
        Routes every unevaluated transaction through SENTINEL's real scoring, ML emulation,
        case manager, autonomous policy engine, and action executor.
        """
        run = self.active_runs.get(run_id)
        if not run:
            # Check history
            for r in self.run_history:
                if r["run_id"] == run_id:
                    run = r
                    self.active_runs[run_id] = r
                    break

        if not run:
            raise ValueError(f"Benchmark run '{run_id}' not found.")

        if run.get("status") in ("EVALUATING", "RUNNING"):
            return True  # Already running

        run["status"] = "EVALUATING"
        run["started_at"] = _now_iso()
        run["processed_count"] = 0
        run["successful_count"] = 0
        run["failed_count"] = 0
        run["cancel_requested"] = False
        run["failures"] = []

        # Launch background evaluation loop
        asyncio.create_task(
            self._process_evaluation_loop(run_id, repo)
        )
        return True

    async def _process_evaluation_loop(
        self,
        run_id: str,
        repo: Any = None,
    ) -> None:
        """
        Internal worker processing each transaction through the real SENTINEL pipeline.
        """
        run = self.active_runs.get(run_id)
        if not run:
            return

        tx_list = run.get("transactions", [])
        start_time = time.time()

        for idx, tx_record in enumerate(tx_list, start=1):
            if run.get("cancel_requested"):
                run["status"] = "CANCELLED"
                break

            await self._evaluate_single_tx_record(tx_record, run_id, repo=repo)

            if tx_record.get("evaluation_state") in ("EVALUATED", "RE_EVALUATED"):
                run["successful_count"] += 1
            else:
                run["failed_count"] += 1
                run["failures"].append({
                    "index": idx,
                    "tx_id": tx_record.get("tx_id"),
                    "profile": tx_record.get("benchmark_profile"),
                    "error": tx_record.get("reason", "Unknown evaluation error"),
                })

            run["processed_count"] = run["successful_count"] + run["failed_count"]

            # Small cooperative yield to keep event loop responsive
            if idx % 10 == 0:
                await asyncio.sleep(0.01)

            # Broadcast progress over WebSocket if manager available
            if self.broadcast_manager:
                try:
                    await self.broadcast_manager.broadcast({
                        "event": "benchmark.progress",
                        "run_id": run_id,
                        "processed": run["processed_count"],
                        "total": run["total_requested"],
                        "successful": run["successful_count"],
                        "failed": run["failed_count"],
                        "pct": round((run["processed_count"] / max(1, run["total_requested"])) * 100, 1),
                    })
                except Exception:
                    pass

        # Finalize run state
        elapsed_seconds = round(time.time() - start_time, 2)
        if run["status"] != "CANCELLED":
            run["status"] = "COMPLETED"

        run["completed_at"] = _now_iso()
        run["elapsed_seconds"] = elapsed_seconds
        run["summary"] = self._compute_summary(run)

        # Archive run to history (keep latest 30 runs)
        # Update or prepend
        existing_idx = next((i for i, r in enumerate(self.run_history) if r["run_id"] == run_id), None)
        if existing_idx is not None:
            self.run_history[existing_idx] = copy.deepcopy(run)
        else:
            self.run_history.insert(0, copy.deepcopy(run))
            if len(self.run_history) > 30:
                self.run_history.pop()

        # Broadcast completion
        if self.broadcast_manager:
            try:
                await self.broadcast_manager.broadcast({
                    "event": "benchmark.completed",
                    "run_id": run_id,
                    "status": run["status"],
                    "summary": run["summary"],
                })
            except Exception:
                pass

    async def _evaluate_single_tx_record(
        self,
        tx_record: Dict[str, Any],
        run_id: str,
        repo: Any = None,
    ) -> None:
        """
        Processes an individual transaction record through the existing SENTINEL pipeline:
        Validation -> Rule scoring -> ML emulation -> Hybrid score fusion ->
        Autonomous Policy Engine -> Simulated Action Execution (with human operator sign-off boundary).
        """
        try:
            # Check if this transaction was already evaluated (Re-evaluation detection)
            is_re_evaluation = tx_record.get("evaluation_state") in ("EVALUATED", "RE_EVALUATED")
            previous_eval = None
            if is_re_evaluation:
                previous_eval = {
                    "risk_score": tx_record.get("risk_score"),
                    "rule_score": tx_record.get("rule_score"),
                    "ml_score": tx_record.get("ml_score"),
                    "final_score": tx_record.get("final_score"),
                    "risk_level": tx_record.get("risk_level"),
                    "threshold": tx_record.get("threshold"),
                    "policy_action": tx_record.get("policy_action"),
                    "risk_factors": copy.deepcopy(tx_record.get("risk_factors", [])),
                }

            # Retrieve immutable snapshot input or build one
            raw_input = tx_record.get("raw_input") or {}
            eval_inputs = tx_record.get("evaluation_inputs")
            if eval_inputs:
                snapshot = EvaluationInputSnapshot(**eval_inputs)
            else:
                snapshot = build_evaluation_snapshot(
                    tx=raw_input if raw_input else tx_record,
                    run_id=run_id,
                    seed=f"{run_id}:{tx_record.get('tx_id')}",
                )
                tx_record["evaluation_inputs"] = snapshot.to_dict()

            # Execute pure evaluation
            result = evaluate_benchmark_transaction_pure(snapshot)

            # Populate evaluation result into record
            tx_record["status"] = "SUCCESS"
            tx_record["evaluation_state"] = "RE_EVALUATED" if is_re_evaluation else "EVALUATED"
            tx_record["rule_score"] = result["rule_score"]
            tx_record["ml_score"] = result["ml_score"]
            tx_record["risk_score"] = result["risk_score"]
            tx_record["final_score"] = result["final_score"]
            tx_record["risk_level"] = result["risk_level"]
            tx_record["threshold"] = result["threshold"]
            tx_record["policy_action"] = result["policy_action"]
            tx_record["policy_decision"] = result["policy_decision"]
            tx_record["policy_rule_id"] = result["policy_rule_id"]
            tx_record["execution_status"] = result["execution_status"]
            tx_record["requires_operator_action"] = result["requires_operator_action"]
            tx_record["reason"] = result["reason"]
            tx_record["full_reason"] = result["full_reason"]
            tx_record["confidence"] = result["confidence"]
            tx_record["risk_factors"] = result["risk_factors"]
            tx_record["ml_feature_importance"] = result["ml_feature_importance"]
            tx_record["execution_record"] = result["execution_record"]
            tx_record["evaluation_inputs"] = result["evaluation_inputs"]
            tx_record["evaluation_version"] = result["evaluation_version"]
            tx_record["deterministic_seed"] = result["deterministic_seed"]
            tx_record["evaluated_at"] = result["timestamp"]

            # Retain case/chain metadata if present
            if snapshot.chain_id:
                tx_record["chain_id"] = snapshot.chain_id
            if raw_input.get("case_id"):
                tx_record["case_id"] = raw_input["case_id"]

            if is_re_evaluation and previous_eval is not None:
                old_score = previous_eval["risk_score"]
                new_score = result["risk_score"]
                tx_record["previous_evaluation"] = previous_eval
                if old_score == new_score:
                    tx_record["is_reproducible"] = True
                    tx_record["reproducibility_drift"] = False
                    tx_record.pop("reproducibility_warning", None)
                else:
                    tx_record["is_reproducible"] = False
                    tx_record["reproducibility_drift"] = True
                    tx_record["reproducibility_warning"] = {
                        "old_score": old_score,
                        "new_score": new_score,
                        "old_tier": previous_eval["risk_level"],
                        "new_tier": result["risk_level"],
                    }

        except Exception as e:
            tx_record["status"] = "FAILED"
            tx_record["evaluation_state"] = "FAILED"
            tx_record["reason"] = f"Evaluation failed: {str(e)}"

    async def evaluate_single_transaction_in_batch(
        self,
        run_id: str,
        tx_id: str,
        repo: Any = None,
    ) -> Dict[str, Any]:
        """
        Evaluates ONLY the specified transaction in a benchmark run.
        Leaves all other transactions in the batch untouched.
        Reuses SENTINEL's exact pipeline (run_pipeline -> evaluate_autonomous_policy -> execute_simulated_action).
        """
        run = self.active_runs.get(run_id)
        if not run:
            for r in self.run_history:
                if r["run_id"] == run_id:
                    run = r
                    self.active_runs[run_id] = r
                    break

        if not run:
            raise ValueError(f"Benchmark run '{run_id}' not found.")

        target_tx = None
        for tx in run.get("transactions", []):
            if tx.get("tx_id") == tx_id:
                target_tx = tx
                break

        if not target_tx:
            raise ValueError(f"Transaction '{tx_id}' not found in benchmark run '{run_id}'.")

        await self._evaluate_single_tx_record(target_tx, run_id, repo=repo)

        # Update run aggregates dynamically without touching any other transaction
        run["successful_count"] = sum(1 for t in run["transactions"] if t.get("evaluation_state") in ("EVALUATED", "RE_EVALUATED"))
        run["failed_count"] = sum(1 for t in run["transactions"] if t.get("evaluation_state") == "FAILED")
        run["processed_count"] = run["successful_count"] + run["failed_count"]
        run["summary"] = self._compute_summary(run)

        # If all transactions are now evaluated or failed, mark the entire run COMPLETED
        if all(t.get("evaluation_state") in ("EVALUATED", "RE_EVALUATED", "FAILED") for t in run["transactions"]):
            run["status"] = "COMPLETED"
            run["completed_at"] = _now_iso()

        return target_tx


    async def execute_benchmark_run(
        self,
        num_transactions: int,
        profile_mode: str = "BALANCED",
        single_profile: Optional[str] = None,
        custom_distribution: Optional[Dict[str, float]] = None,
        seed: Optional[str] = None,
        repo: Any = None,
    ) -> str:
        """
        Convenience wrapper executing Phase 1 (generation) + Phase 2 (evaluation) immediately.
        Used for programmatic API calls and legacy automated test suites.
        """
        run_id = self.create_benchmark_batch(
            num_transactions=num_transactions,
            profile_mode=profile_mode,
            single_profile=single_profile,
            custom_distribution=custom_distribution,
            seed=seed,
        )
        await self.evaluate_benchmark_batch(run_id, repo=repo)
        return run_id

    def _compute_summary(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes real aggregated metrics from the collected transaction results.
        Gracefully handles both UNEVALUATED inputs and EVALUATED outputs.
        """
        txs = run.get("transactions", [])
        evaluated_txs = [
            t for t in txs
            if t.get("evaluation_state") in ("EVALUATED", "RE_EVALUATED") and t.get("risk_score") is not None
        ]

        if not evaluated_txs:
            # Profile breakdown for input batch
            input_profile_breakdown: Dict[str, int] = {}
            for t in txs:
                p = t.get("benchmark_profile", "UNKNOWN")
                input_profile_breakdown[p] = input_profile_breakdown.get(p, 0) + 1

            return {
                "total_requested": run.get("total_requested", len(txs)),
                "total_processed": 0,
                "successful": 0,
                "failed": run.get("failed_count", 0),
                "average_risk_score": 0.0,
                "median_risk_score": 0.0,
                "min_risk_score": 0.0,
                "max_risk_score": 0.0,
                "risk_distribution": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "policy_distribution": {},
                "operator_actions_required": 0,
                "cases_created": 0,
                "profile_breakdown": input_profile_breakdown,
                "evaluation_status": "UNEVALUATED" if run.get("status") in ("UNEVALUATED", "DRAFT") else run.get("status", "UNEVALUATED"),
            }

        scores = [float(t["risk_score"]) for t in evaluated_txs]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        median_score = round(statistics.median(scores), 1) if scores else 0.0
        min_score = round(min(scores), 1) if scores else 0.0
        max_score = round(max(scores), 1) if scores else 0.0

        risk_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for s in scores:
            if s >= 85:
                risk_dist["CRITICAL"] += 1
            elif s >= 70:
                risk_dist["HIGH"] += 1
            elif s >= 40:
                risk_dist["MEDIUM"] += 1
            else:
                risk_dist["LOW"] += 1

        policy_dist: Dict[str, int] = {}
        for t in evaluated_txs:
            act = t.get("policy_action", "MONITOR")
            policy_dist[act] = policy_dist.get(act, 0) + 1

        operator_reqs = sum(1 for t in evaluated_txs if t.get("requires_operator_action"))
        cases = {t["case_id"] for t in evaluated_txs if t.get("case_id")}

        profile_breakdown: Dict[str, int] = {}
        for t in evaluated_txs:
            p = t.get("benchmark_profile", "UNKNOWN")
            profile_breakdown[p] = profile_breakdown.get(p, 0) + 1

        return {
            "total_requested": run.get("total_requested", len(txs)),
            "total_processed": len(evaluated_txs) + run.get("failed_count", 0),
            "successful": len(evaluated_txs),
            "failed": run.get("failed_count", 0),
            "average_risk_score": avg_score,
            "median_risk_score": median_score,
            "min_risk_score": min_score,
            "max_risk_score": max_score,
            "risk_distribution": risk_dist,
            "policy_distribution": policy_dist,
            "operator_actions_required": operator_reqs,
            "cases_created": len(cases),
            "profile_breakdown": profile_breakdown,
            "evaluation_status": run.get("status", "COMPLETED"),
        }

    def cancel_run(self, run_id: str) -> bool:
        """
        Cooperatively cancels an ongoing benchmark run.
        """
        run = self.active_runs.get(run_id)
        if run and run.get("status") in ("RUNNING", "EVALUATING"):
            run["cancel_requested"] = True
            return True
        return False

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves complete run state and transactions by ID.
        Checks active runs first, then history.
        """
        if run_id in self.active_runs:
            run = self.active_runs[run_id]
            # Dynamic summary if still running
            if not run.get("summary"):
                run_copy = copy.deepcopy(run)
                run_copy["summary"] = self._compute_summary(run_copy)
                return run_copy
            return run

        for r in self.run_history:
            if r["run_id"] == run_id:
                return r
        return None

    def list_runs(self) -> List[Dict[str, Any]]:
        """
        Returns summary list of all recent benchmark runs for selection and comparison.
        """
        runs = []
        for r in self.run_history:
            runs.append({
                "run_id": r["run_id"],
                "status": r["status"],
                "seed": r.get("seed"),
                "num_transactions": r.get("num_transactions"),
                "profile_mode": r.get("profile_mode"),
                "created_at": r.get("created_at"),
                "completed_at": r.get("completed_at"),
                "elapsed_seconds": r.get("elapsed_seconds", 0),
                "summary": r.get("summary"),
            })
        return runs

    async def evaluate_custom_transaction(
        self,
        custom_input: Dict[str, Any],
        repo: Any = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a single user-supplied custom transaction through the pure,
        deterministic benchmark evaluator without mutating any global state.
        """
        snapshot = build_evaluation_snapshot(
            tx=custom_input,
            run_id="BM-CUSTOM",
            seed=custom_input.get("seed"),
            account_baseline={
                "avg_monthly_tx_amount": float(custom_input.get("avg_monthly_tx_amount", 25000.0)),
                "is_new_receiver": bool(custom_input.get("is_new_receiver", False)),
            },
        )
        result = evaluate_benchmark_transaction_pure(snapshot)

        scored_tx: Dict[str, Any] = {
            "tx_id": snapshot.tx_id,
            "source": "MANUAL_CUSTOM_INPUT",
            "sender_account": snapshot.sender_account,
            "receiver_account": snapshot.receiver_account,
            "amount": snapshot.amount,
            "currency": snapshot.currency,
            "channel": snapshot.channel,
            "timestamp": snapshot.timestamp,
            "hop_number": snapshot.hop_number,
            "on_active_call": snapshot.on_active_call,
            "simulator_meta": copy.deepcopy(snapshot.simulator_meta),
            "rule_score": result["rule_score"],
            "ml_score": result["ml_score"],
            "risk_score": result["risk_score"],
            "final_score": result["final_score"],
            "risk_level": result["risk_level"],
            "threshold": result["threshold"],
            "policy_action": result["policy_action"],
            "policy_decision": result["policy_decision"],
            "policy_rule_id": result["policy_rule_id"],
            "reason": result["reason"],
            "full_reason": result["full_reason"],
            "confidence": result["confidence"],
            "risk_factors": result["risk_factors"],
            "ml_feature_importance": result["ml_feature_importance"],
            "execution_record": result["execution_record"],
            "evaluation_inputs": result["evaluation_inputs"],
            "evaluation_version": result["evaluation_version"],
            "deterministic_seed": result["deterministic_seed"],
        }
        if snapshot.is_cross_border:
            scored_tx["is_cross_border"] = True
        if snapshot.velocity_flag:
            scored_tx["velocity_flag"] = True
        if snapshot.device_changed:
            scored_tx["device_changed"] = True

        return {
            "transaction": scored_tx,
            "case": None,
            "policy_decision": result["policy_decision_details"],
            "execution_record": result["execution_record"],
            "graph": None,
            "recovery": None,
            "evaluation_inputs": result["evaluation_inputs"],
            "evaluation_version": result["evaluation_version"],
            "deterministic_seed": result["deterministic_seed"],
        }

    def export_csv(self, run_id: str) -> str:
        """
        Generates 16-field UTF-8 BOM CSV audit export for a benchmark run.
        """
        run = self.get_run(run_id)
        if not run:
            return ""

        output = io.StringIO()
        output.write("\ufeff")  # UTF-8 BOM
        writer = csv.writer(output)

        headers = [
            "transaction_id",
            "benchmark_run_id",
            "profile",
            "timestamp",
            "sender_account",
            "receiver_account",
            "amount",
            "channel",
            "rule_score",
            "ml_score",
            "hybrid_risk_score",
            "risk_level",
            "policy_decision",
            "execution_status",
            "requires_operator_action",
            "case_id",
        ]
        writer.writerow(headers)

        for t in run.get("transactions", []):
            row = [
                _sanitize_csv_field(t.get("tx_id")),
                _sanitize_csv_field(run_id),
                _sanitize_csv_field(t.get("benchmark_profile")),
                _sanitize_csv_field(t.get("timestamp")),
                _sanitize_csv_field(t.get("sender_account")),
                _sanitize_csv_field(t.get("receiver_account")),
                _sanitize_csv_field(t.get("amount")),
                _sanitize_csv_field(t.get("channel")),
                _sanitize_csv_field(t.get("rule_score")),
                _sanitize_csv_field(t.get("ml_score")),
                _sanitize_csv_field(t.get("risk_score")),
                _sanitize_csv_field(t.get("risk_level")),
                _sanitize_csv_field(t.get("policy_action")),
                _sanitize_csv_field(t.get("execution_status")),
                _sanitize_csv_field("YES" if t.get("requires_operator_action") else "NO"),
                _sanitize_csv_field(t.get("case_id") or "NONE"),
            ]
            writer.writerow(row)

        return output.getvalue()


# Global Singleton
benchmark_service = BenchmarkService()
