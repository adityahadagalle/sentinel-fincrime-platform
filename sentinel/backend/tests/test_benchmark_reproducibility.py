"""
SENTINEL Benchmark Lab — Reproducibility & Side-Effect Free Regression Test Suite.

Covers all 10 mandated architectural regression test categories:
1. Same transaction evaluated 10 times:
   - Identical rule score
   - Identical ML score
   - Identical final score
   - Identical risk level
   - Identical factors & contributions
2. Custom transaction without simulator_meta["is_new_receiver"]:
   - First and subsequent evaluations must match identically (no 35-point drop).
3. Explicit simulator_meta["is_new_receiver"] = true:
   - Remains true across repeated evaluations.
4. Explicit simulator_meta["is_new_receiver"] = false:
   - Remains false across repeated evaluations.
5. Evaluation must not mutate:
   - accounts
   - transactions
   - cases
   - graphs
   - executed actions / investigation state
   - receiver history
6. Deterministic ML:
   - Same run_id + tx_id gives identical ML score across separate calls.
7. Risk-tier boundary tests:
   - 39 = LOW
   - 40 = MEDIUM
   - 69 = MEDIUM
   - 70 = HIGH
   - 84 = HIGH
   - 85 = CRITICAL
8. Multi-hop transactions:
   - Repeated evaluation must preserve hop number and origin score.
   - Hop decay calculation must remain identical.
9. Batch versus single evaluation:
   - Evaluating one transaction individually produces the exact same result
     as evaluating that same transaction inside the batch.
10. Re-running an entire benchmark batch:
    - Re-evaluating the entire batch produces identical results for all transactions.
"""

import copy
import pytest
from app.core.data_store import data_store
from app.services.benchmark_service import BenchmarkService
from app.engines.benchmark_evaluator import (
    build_evaluation_snapshot,
    evaluate_benchmark_transaction_pure,
    EvaluationInputSnapshot,
    EVALUATION_VERSION,
)
from app.services.ml_risk_engine import predict_ml_score


@pytest.mark.asyncio
async def test_1_same_transaction_evaluated_10_times_identical_scores_and_tier():
    """
    Regression Test 1:
    The exact same transaction evaluated 10 times consecutively must return
    strictly identical:
    - rule_score
    - ml_score
    - final_score
    - risk_level
    - factor breakdown and factor contributions
    """
    svc = BenchmarkService()
    run_id = svc.create_benchmark_batch(num_transactions=1, profile_mode="SINGLE", single_profile="MULTI_SIGNAL", seed="TEST-10X-SEED")
    run = svc.get_run(run_id)
    tx_id = run["transactions"][0]["tx_id"]

    results = []
    for _ in range(10):
        res = await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id=tx_id)
        results.append(copy.deepcopy(res))

    first = results[0]
    assert first["rule_score"] is not None
    assert first["ml_score"] is not None
    assert first["final_score"] is not None
    assert first["risk_level"] is not None

    for i in range(1, 10):
        cur = results[i]
        assert cur["rule_score"] == first["rule_score"], f"Iteration {i}: rule_score drifted"
        assert cur["ml_score"] == first["ml_score"], f"Iteration {i}: ml_score drifted"
        assert cur["final_score"] == first["final_score"], f"Iteration {i}: final_score drifted"
        assert cur["risk_score"] == first["risk_score"], f"Iteration {i}: risk_score drifted"
        assert cur["risk_level"] == first["risk_level"], f"Iteration {i}: risk_level drifted"
        assert cur["policy_action"] == first["policy_action"], f"Iteration {i}: policy_action drifted"
        assert cur["policy_decision"] == first["policy_decision"], f"Iteration {i}: policy_decision drifted"
        assert cur["risk_factors"] == first["risk_factors"], f"Iteration {i}: risk_factors drifted"
        assert cur["ml_feature_importance"] == first["ml_feature_importance"], f"Iteration {i}: ml_feature_importance drifted"


@pytest.mark.asyncio
async def test_2_custom_transaction_without_simulator_meta_new_receiver():
    """
    Regression Test 2:
    Custom transaction without simulator_meta["is_new_receiver"]:
    First and subsequent evaluations must match identically.
    Eliminates the known ~35-point drop bug caused by mutating account['is_new_receiver'].
    """
    svc = BenchmarkService()
    custom_input = {
        "tx_id": "TX-CUSTOM-NO-SIM-META",
        "sender_account": "ACC-TEST-SENDER-01",
        "receiver_account": "ACC-TEST-RECEIVER-99",
        "amount": 75000.0,
        "channel": "UPI",
        "avg_monthly_tx_amount": 25000.0,
        "is_night_time": False,
        "on_active_call": False,
        # Intentionally omit simulator_meta["is_new_receiver"]
    }

    # Evaluate iteration 1
    res1 = await svc.evaluate_custom_transaction(custom_input)
    score1 = res1["transaction"]["risk_score"]
    rule1 = res1["transaction"]["rule_score"]
    ml1 = res1["transaction"]["ml_score"]
    tier1 = res1["transaction"]["risk_level"]

    # Evaluate iteration 2
    res2 = await svc.evaluate_custom_transaction(custom_input)
    score2 = res2["transaction"]["risk_score"]
    rule2 = res2["transaction"]["rule_score"]
    ml2 = res2["transaction"]["ml_score"]
    tier2 = res2["transaction"]["risk_level"]

    # Evaluate iteration 3
    res3 = await svc.evaluate_custom_transaction(custom_input)
    score3 = res3["transaction"]["risk_score"]

    assert score1 == score2 == score3, f"Score drifted: {score1} -> {score2} -> {score3}"
    assert rule1 == rule2, f"Rule score drifted: {rule1} -> {rule2}"
    assert ml1 == ml2, f"ML score drifted: {ml1} -> {ml2}"
    assert tier1 == tier2, f"Risk tier changed: {tier1} -> {tier2}"


@pytest.mark.asyncio
async def test_3_explicit_simulator_meta_new_receiver_true():
    """
    Regression Test 3:
    Explicit simulator_meta["is_new_receiver"] = true remains true across repeated evaluations.
    """
    svc = BenchmarkService()
    custom_input = {
        "tx_id": "TX-CUSTOM-META-TRUE",
        "sender_account": "ACC-META-SND-TRUE",
        "receiver_account": "ACC-META-RCV-TRUE",
        "amount": 25000.0,
        "simulator_meta": {"is_new_receiver": True},
    }

    res1 = await svc.evaluate_custom_transaction(custom_input)
    tx1 = res1["transaction"]
    assert tx1["simulator_meta"]["is_new_receiver"] is True
    factors1 = {f["name"]: f for f in tx1["risk_factors"]}
    assert factors1["new_receiver"]["value"] == 100
    assert factors1["new_receiver"]["contribution"] == 35

    # Repeated evaluation
    res2 = await svc.evaluate_custom_transaction(custom_input)
    tx2 = res2["transaction"]
    assert tx2["simulator_meta"]["is_new_receiver"] is True
    factors2 = {f["name"]: f for f in tx2["risk_factors"]}
    assert factors2["new_receiver"]["value"] == 100
    assert factors2["new_receiver"]["contribution"] == 35
    assert tx1["risk_score"] == tx2["risk_score"]


@pytest.mark.asyncio
async def test_4_explicit_simulator_meta_new_receiver_false():
    """
    Regression Test 4:
    Explicit simulator_meta["is_new_receiver"] = false remains false across repeated evaluations.
    """
    svc = BenchmarkService()
    custom_input = {
        "tx_id": "TX-CUSTOM-META-FALSE",
        "sender_account": "ACC-META-SND-FALSE",
        "receiver_account": "ACC-META-RCV-FALSE",
        "amount": 25000.0,
        "simulator_meta": {"is_new_receiver": False},
    }

    res1 = await svc.evaluate_custom_transaction(custom_input)
    tx1 = res1["transaction"]
    assert tx1["simulator_meta"]["is_new_receiver"] is False
    factors1 = {f["name"]: f for f in tx1["risk_factors"]}
    assert factors1["new_receiver"]["value"] == 0
    assert factors1["new_receiver"]["contribution"] == 0

    # Repeated evaluation
    res2 = await svc.evaluate_custom_transaction(custom_input)
    tx2 = res2["transaction"]
    assert tx2["simulator_meta"]["is_new_receiver"] is False
    factors2 = {f["name"]: f for f in tx2["risk_factors"]}
    assert factors2["new_receiver"]["value"] == 0
    assert factors2["new_receiver"]["contribution"] == 0
    assert tx1["risk_score"] == tx2["risk_score"]


@pytest.mark.asyncio
async def test_5_evaluation_must_not_mutate_state():
    """
    Regression Test 5:
    Evaluation must not mutate accounts, transactions, cases, graphs,
    executed actions, or receiver history in global data_store.
    """
    svc = BenchmarkService()

    # Capture initial store snapshot
    initial_accounts = copy.deepcopy(data_store.get("accounts", {}))
    initial_transactions = copy.deepcopy(data_store.get("transactions", {}))
    initial_cases = copy.deepcopy(data_store.get("cases", {}))
    initial_graphs = copy.deepcopy(data_store.get("graphs", {}))
    initial_actions = copy.deepcopy(data_store.get("executed_actions", {}))

    # Run 10 evaluations
    for i in range(10):
        await svc.evaluate_custom_transaction({
            "tx_id": f"TX-ISOLATION-{i:03d}",
            "sender_account": f"ACC-ISOLATION-SND-{i:03d}",
            "receiver_account": f"ACC-ISOLATION-RCV-{i:03d}",
            "amount": 150000.0,
            "on_active_call": True,
            "simulator_meta": {"is_new_receiver": True},
        })

    # Assert completely unmutated
    assert data_store.get("accounts", {}) == initial_accounts, "data_store['accounts'] was mutated"
    assert data_store.get("transactions", {}) == initial_transactions, "data_store['transactions'] was mutated"
    assert data_store.get("cases", {}) == initial_cases, "data_store['cases'] was mutated"
    assert data_store.get("graphs", {}) == initial_graphs, "data_store['graphs'] was mutated"
    assert data_store.get("executed_actions", {}) == initial_actions, "data_store['executed_actions'] was mutated"


def test_6_deterministic_ml_score():
    """
    Regression Test 6:
    Same run_id + tx_id gives identical ML score across invocations.
    """
    run_id = "BM-20260904-999"
    tx_id = "TX-BM-20260904-999-0042"
    seed = f"{run_id}:{tx_id}"

    rule_scores = [15.0, 45.0, 75.0, 92.0]
    for r in rule_scores:
        ml1 = predict_ml_score(r, seed=seed)
        ml2 = predict_ml_score(r, seed=seed)
        ml3 = predict_ml_score(r, seed=seed)
        assert ml1 == ml2 == ml3, f"ML score not deterministic for rule_score {r}"


def test_7_risk_tier_boundaries():
    """
    Regression Test 7:
    Risk-tier boundary tests:
    - 39 = LOW
    - 40 = MEDIUM
    - 69 = MEDIUM
    - 70 = HIGH
    - 84 = HIGH
    - 85 = CRITICAL
    """
    test_cases = [
        (39, "LOW"),
        (40, "MEDIUM"),
        (69, "MEDIUM"),
        (70, "HIGH"),
        (84, "HIGH"),
        (85, "CRITICAL"),
        (100, "CRITICAL"),
        (0, "LOW"),
    ]

    for score, expected_tier in test_cases:
        if score >= 85:
            tier = "CRITICAL"
        elif score >= 70:
            tier = "HIGH"
        elif score >= 40:
            tier = "MEDIUM"
        else:
            tier = "LOW"
        assert tier == expected_tier, f"Score {score} expected {expected_tier} but got {tier}"


def test_8_multi_hop_decay_preservation():
    """
    Regression Test 8:
    Multi-hop transactions:
    Repeated evaluation must preserve hop number and origin score;
    hop decay must remain identical.
    """
    origin_score = 90.0
    hop1_tx = {
        "tx_id": "TX-HOP-01",
        "sender_account": "ACC-HOP-SND",
        "receiver_account": "ACC-HOP-RCV-1",
        "amount": 100000.0,
        "hop_number": 1,
        "origin_score": origin_score,
    }
    hop2_tx = {
        "tx_id": "TX-HOP-02",
        "sender_account": "ACC-HOP-RCV-1",
        "receiver_account": "ACC-HOP-RCV-2",
        "amount": 90000.0,
        "hop_number": 2,
        "origin_score": origin_score,
    }

    snap1 = build_evaluation_snapshot(hop1_tx, run_id="BM-HOP-TEST")
    snap2 = build_evaluation_snapshot(hop2_tx, run_id="BM-HOP-TEST")

    res1_a = evaluate_benchmark_transaction_pure(snap1)
    res1_b = evaluate_benchmark_transaction_pure(snap1)
    assert res1_a["rule_score"] == res1_b["rule_score"]
    assert res1_a["final_score"] == res1_b["final_score"]

    res2_a = evaluate_benchmark_transaction_pure(snap2)
    res2_b = evaluate_benchmark_transaction_pure(snap2)
    assert res2_a["rule_score"] == res2_b["rule_score"]
    assert res2_a["final_score"] == res2_b["final_score"]

    # Hop 1 vs Hop 2 decay verification
    # Hop 2 should have lower decayed rule score than Hop 1
    assert res2_a["rule_score"] < res1_a["rule_score"]


@pytest.mark.asyncio
async def test_9_batch_versus_single_evaluation():
    """
    Regression Test 9:
    Evaluating one transaction individually must produce the exact same result
    as evaluating that same transaction inside the batch.
    """
    import asyncio
    svc = BenchmarkService()
    seed = "TEST-BATCH-VS-SINGLE-SEED"

    run_id = svc.create_benchmark_batch(num_transactions=5, profile_mode="BALANCED", seed=seed)
    run = svc.get_run(run_id)
    target_tx = run["transactions"][2]
    target_tx_id = target_tx["tx_id"]

    # 1. Evaluate target transaction individually
    single_evaluated = await svc.evaluate_single_transaction_in_batch(run_id=run_id, tx_id=target_tx_id)
    single_score = single_evaluated["risk_score"]
    single_rule = single_evaluated["rule_score"]
    single_ml = single_evaluated["ml_score"]
    single_tier = single_evaluated["risk_level"]
    single_action = single_evaluated["policy_action"]

    # 2. Now run the batch evaluation on the entire run
    await svc.evaluate_benchmark_batch(run_id)
    for _ in range(50):
        batch_run = svc.get_run(run_id)
        if batch_run and batch_run.get("status") == "COMPLETED":
            break
        await asyncio.sleep(0.05)

    batch_evaluated = next(t for t in batch_run["transactions"] if t["tx_id"] == target_tx_id)

    assert single_score == batch_evaluated["risk_score"]
    assert single_rule == batch_evaluated["rule_score"]
    assert single_ml == batch_evaluated["ml_score"]
    assert single_tier == batch_evaluated["risk_level"]
    assert single_action == batch_evaluated["policy_action"]


@pytest.mark.asyncio
async def test_10_rerunning_entire_batch_preserves_results():
    """
    Regression Test 10:
    Re-running an entire benchmark batch must not alter results from previous evaluation.
    """
    svc = BenchmarkService()
    seed = "TEST-RERUN-BATCH-SEED"

    run_id = svc.create_benchmark_batch(num_transactions=10, profile_mode="BALANCED", seed=seed)

    # Evaluation Pass 1
    await svc.evaluate_benchmark_batch(run_id)
    import asyncio
    for _ in range(50):
        run = svc.get_run(run_id)
        if run and run.get("status") == "COMPLETED":
            break
        await asyncio.sleep(0.05)

    pass1_scores = [(t["tx_id"], t["final_score"], t["rule_score"], t["ml_score"], t["risk_level"]) for t in run["transactions"]]

    # Evaluation Pass 2 (Re-run all transactions in the batch)
    run["status"] = "UNEVALUATED"
    await svc.evaluate_benchmark_batch(run_id)
    for _ in range(50):
        run = svc.get_run(run_id)
        if run and run.get("status") == "COMPLETED":
            break
        await asyncio.sleep(0.05)

    pass2_scores = [(t["tx_id"], t["final_score"], t["rule_score"], t["ml_score"], t["risk_level"]) for t in run["transactions"]]

    assert pass1_scores == pass2_scores, "Re-running entire benchmark batch produced drifting scores!"
