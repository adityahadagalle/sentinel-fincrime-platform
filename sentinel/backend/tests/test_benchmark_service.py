"""
Unit and Integration Tests for SENTINEL Benchmark Lab Service.

Validates:
1. Batch size validation and exact distribution calculation.
2. Synthetic entity ID uniqueness (TX-BM-..., ACC-BM-...).
3. Controlled profile generation against real scoring features.
4. Pipeline integration: scoring, ML emulation, policy engine, and action execution.
5. No duplicate scoring formulas (verifies hybrid fusion).
6. Human operator approval gate preservation (FREEZE -> REQUIRES_OPERATOR_ACTION).
7. Reproducibility with deterministic seeds.
8. Metric reconciliation (requested == processed + failed).
9. CSV audit log export compliance.
10. Custom transaction evaluation via real pipeline.
"""

import pytest
import random
from app.services.benchmark_service import (
    BenchmarkService,
    SUPPORTED_PROFILES,
    benchmark_service,
)
from app.core.data_store import data_store


def test_supported_profiles_complete():
    expected = {"BASELINE", "NEW_RECEIVER", "AMOUNT_ANOMALY", "TIME_ANOMALY", "ACTIVE_CALL", "MULTI_SIGNAL", "MULTI_HOP"}
    assert set(SUPPORTED_PROFILES) == expected


def test_calculate_distribution_single():
    svc = BenchmarkService()
    dist = svc.calculate_distribution(100, "SINGLE", single_profile="AMOUNT_ANOMALY")
    assert dist == {"AMOUNT_ANOMALY": 100}
    assert sum(dist.values()) == 100


def test_calculate_distribution_balanced():
    svc = BenchmarkService()
    dist = svc.calculate_distribution(100, "BALANCED")
    assert sum(dist.values()) == 100
    assert len(dist) == len(SUPPORTED_PROFILES)
    for p in SUPPORTED_PROFILES:
        assert dist[p] in (14, 15)  # 100 // 7 = 14, rem 2


def test_calculate_distribution_custom_mix():
    svc = BenchmarkService()
    custom = {
        "BASELINE": 30.0,
        "NEW_RECEIVER": 20.0,
        "AMOUNT_ANOMALY": 20.0,
        "MULTI_SIGNAL": 30.0,
    }
    dist = svc.calculate_distribution(100, "CUSTOM_MIX", custom_distribution=custom)
    assert sum(dist.values()) == 100
    assert dist["BASELINE"] == 30
    assert dist["NEW_RECEIVER"] == 20
    assert dist["AMOUNT_ANOMALY"] == 20
    assert dist["MULTI_SIGNAL"] == 30


def test_synthetic_id_uniqueness():
    svc = BenchmarkService()
    rng = random.Random(42)
    tx_ids = set()
    snd_ids = set()
    rcv_ids = set()

    for i in range(1, 101):
        tx = svc.generate_synthetic_transaction("BM-TEST-001", i, "BASELINE", rng)
        assert tx["tx_id"].startswith("TX-BM-TEST-001-")
        assert tx["sender_account"].startswith("ACC-BM-SND-")
        assert tx["receiver_account"].startswith("ACC-BM-RCV-")
        assert tx["tx_id"] not in tx_ids
        assert tx["sender_account"] not in snd_ids
        assert tx["receiver_account"] not in rcv_ids
        tx_ids.add(tx["tx_id"])
        snd_ids.add(tx["sender_account"])
        rcv_ids.add(tx["receiver_account"])

    assert len(tx_ids) == 100


def test_profile_generation_features():
    svc = BenchmarkService()
    rng = random.Random(99)

    # 1. BASELINE: low amount, daytime, not new receiver, not on call
    tx_base = svc.generate_synthetic_transaction("BM-TEST-002", 1, "BASELINE", rng)
    assert tx_base["amount"] < 5000.0
    assert tx_base["simulator_meta"]["is_new_receiver"] is False
    assert tx_base["on_active_call"] is False

    # 2. NEW_RECEIVER: is_new_receiver is True
    tx_rec = svc.generate_synthetic_transaction("BM-TEST-002", 2, "NEW_RECEIVER", rng)
    assert tx_rec["simulator_meta"]["is_new_receiver"] is True

    # 3. AMOUNT_ANOMALY: high amount
    tx_amt = svc.generate_synthetic_transaction("BM-TEST-002", 3, "AMOUNT_ANOMALY", rng)
    assert tx_amt["amount"] > 100000.0

    # 4. TIME_ANOMALY: hour in deep night (10 PM to 6 AM)
    tx_time = svc.generate_synthetic_transaction("BM-TEST-002", 4, "TIME_ANOMALY", rng)
    from datetime import datetime
    dt = datetime.fromisoformat(tx_time["timestamp"].replace("Z", "+00:00"))
    assert dt.hour < 6 or dt.hour >= 22

    # 5. ACTIVE_CALL: on_active_call is True
    tx_call = svc.generate_synthetic_transaction("BM-TEST-002", 5, "ACTIVE_CALL", rng)
    assert tx_call["on_active_call"] is True

    # 6. MULTI_SIGNAL: multiple flags
    tx_multi = svc.generate_synthetic_transaction("BM-TEST-002", 6, "MULTI_SIGNAL", rng)
    assert tx_multi["amount"] > 100000.0
    assert tx_multi["simulator_meta"]["is_new_receiver"] is True
    assert tx_multi["on_active_call"] is True


def test_reproducibility_with_seed():
    svc = BenchmarkService()
    seed = "BENCHMARK-REPRODUCIBLE-SEED-42"

    rng1 = random.Random(seed)
    tx_run1 = [
        svc.generate_synthetic_transaction("BM-SEED-01", i, "BASELINE", rng1)
        for i in range(1, 15)
    ]

    rng2 = random.Random(seed)
    tx_run2 = [
        svc.generate_synthetic_transaction("BM-SEED-01", i, "BASELINE", rng2)
        for i in range(1, 15)
    ]

    for t1, t2 in zip(tx_run1, tx_run2):
        assert t1["tx_id"] == t2["tx_id"]
        assert t1["amount"] == t2["amount"]
        assert t1["sender_account"] == t2["sender_account"]
        assert t1["receiver_account"] == t2["receiver_account"]
        assert t1["channel"] == t2["channel"]
        assert t1["timestamp"] == t2["timestamp"]


@pytest.mark.asyncio
async def test_benchmark_batch_execution_and_reconciliation():
    svc = BenchmarkService()
    run_id = await svc.execute_benchmark_run(
        num_transactions=14,
        profile_mode="BALANCED",
        seed="TEST-RECONCILE-101",
    )

    # Poll until completed
    import asyncio
    for _ in range(50):
        run = svc.get_run(run_id)
        if run and run.get("status") in ("COMPLETED", "FAILED"):
            break
        await asyncio.sleep(0.05)

    assert run is not None
    assert run["status"] == "COMPLETED"
    assert run["total_requested"] == 14
    assert run["processed_count"] == 14
    assert run["successful_count"] == 14
    assert run["failed_count"] == 0
    assert len(run["transactions"]) == 14

    summary = run["summary"]
    assert summary is not None
    assert summary["total_requested"] == 14
    assert summary["successful"] == 14
    assert summary["failed"] == 0
    assert summary["average_risk_score"] >= 0.0

    # Every transaction must have scores from the real pipeline
    for t in run["transactions"]:
        assert "risk_score" in t
        assert "rule_score" in t
        assert "ml_score" in t
        assert "policy_action" in t
        assert "execution_status" in t
        # Check hybrid fusion: final score = int(0.6 * ml + 0.4 * rule)
        # Allows +/- 1 tolerance due to integer casting of ml_score in score_output
        expected_fusion = int(0.6 * t["ml_score"] + 0.4 * t["rule_score"])
        assert abs(t["risk_score"] - expected_fusion) <= 1


@pytest.mark.asyncio
async def test_multi_signal_reaches_critical_and_preserves_approval_gate():
    svc = BenchmarkService()
    rng = random.Random(123)
    tx = svc.generate_synthetic_transaction("BM-CRIT-01", 1, "MULTI_SIGNAL", rng)

    from app.services.orchestrator import run_pipeline
    from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
    from app.services.simulated_action_executor import execute_simulated_action

    pipeline_res = run_pipeline(tx, data_store)
    scored = pipeline_res["transaction"]

    assert scored["risk_score"] >= 85
    assert scored["threshold"] == "HIGH_RISK"

    policy_decision = evaluate_autonomous_policy(scored, pipeline_res.get("case"), False)
    assert policy_decision["risk_level"] == "CRITICAL"
    assert policy_decision["action"] == "FREEZE"

    # Simulated Action Executor execution
    exec_record = await execute_simulated_action(
        case_id=scored.get("case_id"),
        tx_id=scored.get("tx_id"),
        action_code=policy_decision["action"],
        policy_decision=policy_decision,
        actor_type="AUTOMATION_ENGINE",
    )

    # Non-negotiable human approval gate: FREEZE cannot execute autonomously
    assert exec_record["execution_status"] == "REQUIRES_OPERATOR_ACTION"


@pytest.mark.asyncio
async def test_custom_transaction_evaluation():
    svc = BenchmarkService()
    custom_input = {
        "sender_account": "ACC-CUSTOM-ALICE",
        "receiver_account": "ACC-CUSTOM-BOB",
        "amount": 180000.0,
        "channel": "IMPS",
        "is_night_time": True,
        "on_active_call": True,
        "is_new_receiver": True,
    }

    result = await svc.evaluate_custom_transaction(custom_input)
    assert "transaction" in result
    assert "policy_decision" in result
    assert "execution_record" in result

    tx = result["transaction"]
    assert tx["source"] == "MANUAL_CUSTOM_INPUT"
    assert tx["amount"] == 180000.0
    assert tx["channel"] == "IMPS"
    assert tx["risk_score"] >= 70
    assert result["policy_decision"]["action"] in ("FREEZE", "ESCALATE_ANALYST_REVIEW")


def test_export_csv_format():
    svc = BenchmarkService()
    # Create mock run in active_runs
    mock_run_id = "BM-MOCK-CSV"
    svc.active_runs[mock_run_id] = {
        "run_id": mock_run_id,
        "status": "COMPLETED",
        "transactions": [
            {
                "tx_id": "TX-BM-001",
                "benchmark_profile": "BASELINE",
                "timestamp": "2026-09-04T12:00:00Z",
                "sender_account": "ACC-BM-SND-01",
                "receiver_account": "ACC-BM-RCV-01",
                "amount": 2500.0,
                "channel": "UPI",
                "rule_score": 0.0,
                "ml_score": 0.0,
                "risk_score": 0.0,
                "risk_level": "LOW",
                "policy_action": "MONITOR",
                "execution_status": "NOT_EXECUTED",
                "requires_operator_action": False,
                "case_id": None,
            }
        ],
    }

    csv_out = svc.export_csv(mock_run_id)
    assert csv_out.startswith("\ufeff")  # UTF-8 BOM
    lines = csv_out.strip().splitlines()
    assert len(lines) == 2
    assert "transaction_id,benchmark_run_id,profile" in lines[0]
    assert "TX-BM-001,BM-MOCK-CSV,BASELINE" in lines[1]


@pytest.mark.asyncio
async def test_two_phase_benchmark_lifecycle():
    """
    Validates the core principle:
    1. Transactions are created as UNEVALUATED TEST INPUTS first.
    2. No risk scores or policy decisions are assigned during generation.
    3. User reviews inputs.
    4. Explicit evaluation trigger processes them through the real SENTINEL pipeline.
    """
    svc = BenchmarkService()
    
    # Phase 1: Generate unevaluated batch
    run_id = svc.create_benchmark_batch(
        num_transactions=10,
        profile_mode="BALANCED",
        seed="PHASE-TEST-SEED-001",
    )
    run = svc.get_run(run_id)
    assert run is not None
    assert run["status"] == "UNEVALUATED"
    assert len(run["transactions"]) == 10
    assert run["total_requested"] == 10
    assert run["processed_count"] == 0

    # Verify every transaction is an unevaluated input
    for tx in run["transactions"]:
        assert tx["status"] == "UNEVALUATED"
        assert tx["evaluation_state"] == "UNEVALUATED"
        assert tx["risk_score"] is None
        assert tx["rule_score"] is None
        assert tx["ml_score"] is None
        assert tx["policy_action"] is None
        assert tx["policy_decision"] is None
        assert tx["case_id"] is None
        # But input features are fully formed:
        assert tx["tx_id"].startswith("TX-")
        assert tx["sender_account"].startswith("ACC-")
        assert tx["receiver_account"].startswith("ACC-")
        assert tx["amount"] > 0
        assert tx["channel"] in ("UPI", "IMPS", "NEFT", "CARD")
        assert tx["timestamp"] is not None

    summary_before = run["summary"]
    assert summary_before["evaluation_status"] == "UNEVALUATED"
    assert summary_before["successful"] == 0
    assert summary_before["average_risk_score"] == 0.0

    # Phase 2: Explicit User Evaluation Trigger
    started = await svc.evaluate_benchmark_batch(run_id)
    assert started is True

    # Poll until completed
    import asyncio
    for _ in range(50):
        eval_run = svc.get_run(run_id)
        if eval_run and eval_run.get("status") in ("COMPLETED", "FAILED"):
            break
        await asyncio.sleep(0.05)

    assert eval_run["status"] == "COMPLETED"
    assert eval_run["processed_count"] == 10
    assert eval_run["successful_count"] == 10

    # Verify every transaction now has real SENTINEL scores and decisions
    for tx in eval_run["transactions"]:
        assert tx["status"] == "SUCCESS"
        assert tx["evaluation_state"] == "EVALUATED"
        assert isinstance(tx["risk_score"], float)
        assert isinstance(tx["rule_score"], float)
        assert isinstance(tx["ml_score"], float)
        assert tx["policy_action"] in ("MONITOR", "ENHANCED_MONITORING", "ESCALATE_ANALYST_REVIEW", "FREEZE", "REJECT_TRANSACTION", "BLOCK")
        assert tx["execution_status"] in ("NOT_EXECUTED", "REQUIRES_OPERATOR_ACTION", "SIMULATED_SUCCESS")

    summary_after = eval_run["summary"]
    assert summary_after["evaluation_status"] == "COMPLETED"
    assert summary_after["successful"] == 10
    assert summary_after["average_risk_score"] >= 0.0


def test_add_custom_input_to_unevaluated_batch():
    svc = BenchmarkService()
    run_id = svc.create_benchmark_batch(num_transactions=5, profile_mode="BASELINE")
    
    custom_input = {
        "sender_account": "ACC-CUSTOM-USER-01",
        "receiver_account": "ACC-CUSTOM-PAYEE-99",
        "amount": 75000.0,
        "channel": "IMPS",
        "is_night_time": True,
        "on_active_call": True,
        "is_new_receiver": True,
    }

    added = svc.add_custom_input_to_batch(run_id, custom_input)
    assert added["sender_account"] == "ACC-CUSTOM-USER-01"
    assert added["amount"] == 75000.0
    assert added["status"] == "UNEVALUATED"
    assert added["risk_score"] is None

    run = svc.get_run(run_id)
    assert run["total_requested"] == 6
    assert len(run["transactions"]) == 6


@pytest.mark.asyncio
async def test_case_1_single_evaluation_leaves_other_transactions_untouched():
    """
    Case 1 — Single evaluation:
    Given 5 unevaluated transactions, evaluate only #3.
    Expected:
    #1 unchanged (UNEVALUATED)
    #2 unchanged (UNEVALUATED)
    #3 evaluated (EVALUATED with real risk_score)
    #4 unchanged (UNEVALUATED)
    #5 unchanged (UNEVALUATED)
    """
    svc = BenchmarkService()
    run_id = svc.create_benchmark_batch(num_transactions=5, profile_mode="BALANCED", seed="SEED-CASE1")
    run = svc.get_run(run_id)
    txs = run["transactions"]
    assert len(txs) == 5

    # Target transaction is #3 (index 2)
    target_tx_id = txs[2]["tx_id"]
    for i in range(5):
        assert txs[i]["evaluation_state"] == "UNEVALUATED"
        assert txs[i]["risk_score"] is None

    # Evaluate ONLY transaction #3
    evaluated_tx = await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id=target_tx_id)
    assert evaluated_tx["tx_id"] == target_tx_id
    assert evaluated_tx["evaluation_state"] == "EVALUATED"
    assert evaluated_tx["status"] == "SUCCESS"
    assert isinstance(evaluated_tx["risk_score"], float)
    assert isinstance(evaluated_tx["rule_score"], float)
    assert isinstance(evaluated_tx["ml_score"], float)
    assert evaluated_tx["policy_action"] is not None

    # Refresh run and verify scope enforcement
    updated_run = svc.get_run(run_id)
    updated_txs = updated_run["transactions"]

    # Transaction 1: unchanged
    assert updated_txs[0]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs[0]["risk_score"] is None
    # Transaction 2: unchanged
    assert updated_txs[1]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs[1]["risk_score"] is None
    # Transaction 3: evaluated
    assert updated_txs[2]["evaluation_state"] == "EVALUATED"
    assert updated_txs[2]["risk_score"] == evaluated_tx["risk_score"]
    # Transaction 4: unchanged
    assert updated_txs[3]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs[3]["risk_score"] is None
    # Transaction 5: unchanged
    assert updated_txs[4]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs[4]["risk_score"] is None

    # Summary metrics must correctly reflect only 1 evaluated transaction
    summary = updated_run["summary"]
    assert summary["successful"] == 1
    assert summary["total_requested"] == 5
    assert summary["average_risk_score"] == evaluated_tx["risk_score"]


@pytest.mark.asyncio
async def test_case_2_multiple_independent_evaluations():
    """
    Case 2 — Multiple independent evaluations:
    Evaluate #2, then #4.
    Expected:
    #1 unchanged
    #2 evaluated
    #3 unchanged
    #4 evaluated
    #5 unchanged
    """
    svc = BenchmarkService()
    run_id = svc.create_benchmark_batch(num_transactions=5, profile_mode="BALANCED", seed="SEED-CASE2")
    run = svc.get_run(run_id)
    txs = run["transactions"]

    tx2_id = txs[1]["tx_id"]
    tx4_id = txs[3]["tx_id"]

    # Step 1: Evaluate #2
    await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id=tx2_id)
    updated_txs_step1 = svc.get_run(run_id)["transactions"]
    assert updated_txs_step1[0]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs_step1[1]["evaluation_state"] == "EVALUATED"
    assert updated_txs_step1[2]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs_step1[3]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs_step1[4]["evaluation_state"] == "UNEVALUATED"

    # Step 2: Evaluate #4
    await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id=tx4_id)
    updated_txs_step2 = svc.get_run(run_id)["transactions"]
    assert updated_txs_step2[0]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs_step2[1]["evaluation_state"] == "EVALUATED"
    assert updated_txs_step2[2]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs_step2[3]["evaluation_state"] == "EVALUATED"
    assert updated_txs_step2[4]["evaluation_state"] == "UNEVALUATED"

    summary = svc.get_run(run_id)["summary"]
    assert summary["successful"] == 2
    assert summary["total_requested"] == 5


@pytest.mark.asyncio
async def test_case_4_re_evaluation_of_single_transaction():
    """
    Case 4 — Already evaluated transaction:
    Re-evaluating an already evaluated transaction updates its calculation
    while leaving all other transactions untouched.
    """
    svc = BenchmarkService()
    run_id = svc.create_benchmark_batch(num_transactions=3, profile_mode="BALANCED", seed="SEED-CASE4")
    run = svc.get_run(run_id)
    txs = run["transactions"]
    tx1_id = txs[0]["tx_id"]

    # First evaluation
    first_res = await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id=tx1_id)
    assert first_res["evaluation_state"] == "EVALUATED"
    first_score = first_res["risk_score"]

    # Re-evaluate same transaction
    second_res = await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id=tx1_id)
    assert second_res["evaluation_state"] in ("EVALUATED", "RE_EVALUATED")
    assert isinstance(second_res["risk_score"], float)
    assert second_res["risk_score"] == first_score

    # Others remain untouched and unevaluated
    updated_txs = svc.get_run(run_id)["transactions"]
    assert updated_txs[0]["evaluation_state"] in ("EVALUATED", "RE_EVALUATED")
    assert updated_txs[0]["risk_score"] == second_res["risk_score"]
    assert updated_txs[1]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs[1]["risk_score"] is None
    assert updated_txs[2]["evaluation_state"] == "UNEVALUATED"
    assert updated_txs[2]["risk_score"] is None


@pytest.mark.asyncio
async def test_single_evaluation_invalid_ids_raise_error():
    svc = BenchmarkService()
    run_id = svc.create_benchmark_batch(num_transactions=3, profile_mode="BALANCED")
    
    with pytest.raises(ValueError, match="Transaction 'NON-EXISTENT' not found"):
        await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id="NON-EXISTENT")

    with pytest.raises(ValueError, match="Benchmark run 'INVALID-RUN' not found"):
        await svc.evaluate_single_transaction_in_batch(run_id="INVALID-RUN", tx_id="TX-1")

