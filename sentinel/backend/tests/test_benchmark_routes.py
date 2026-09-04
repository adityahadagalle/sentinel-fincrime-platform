"""
Unit and Integration Tests for SENTINEL Benchmark Lab API Endpoints.

Validates:
1. GET /benchmark/profiles - Returns supported profiles and descriptions.
2. POST /benchmark/start - Initiates runs with validation for batch size and profile mode.
3. GET /benchmark/runs/{run_id} - Fetches run status, progress, and transactions.
4. POST /benchmark/runs/{run_id}/cancel - Cancels active run.
5. GET /benchmark/runs - Lists recent runs with summary statistics.
6. POST /benchmark/custom-evaluate - Evaluates custom manual transactions.
7. GET /benchmark/runs/{run_id}/export - Exports CSV audit records.
"""

import time
import pytest
from fastapi.testclient import TestClient
from main import app
from app.services.benchmark_service import benchmark_service


client = TestClient(app)


def test_get_benchmark_profiles():
    response = client.get("/benchmark/profiles")
    assert response.status_code == 200
    data = response.json()
    assert "supported_profiles" in data
    assert "descriptions" in data
    assert "BASELINE" in data["supported_profiles"]
    assert "MULTI_SIGNAL" in data["supported_profiles"]
    assert "MULTI_HOP" in data["supported_profiles"]


def test_start_benchmark_validation_errors():
    # Negative batch size
    res = client.post("/benchmark/start", json={"num_transactions": 0})
    assert res.status_code == 422

    # Over 500 batch size
    res = client.post("/benchmark/start", json={"num_transactions": 600})
    assert res.status_code == 422

    # Invalid profile_mode
    res = client.post("/benchmark/start", json={"num_transactions": 10, "profile_mode": "INVALID_MODE"})
    assert res.status_code == 400
    assert "Invalid profile_mode" in res.json()["detail"]

    # Unknown single profile
    res = client.post(
        "/benchmark/start",
        json={"num_transactions": 10, "profile_mode": "SINGLE", "single_profile": "NON_EXISTENT"},
    )
    assert res.status_code == 400
    assert "Unknown profile" in res.json()["detail"]


def test_start_and_poll_benchmark_run():
    # Start a small balanced run
    res = client.post(
        "/benchmark/start",
        json={
            "num_transactions": 7,
            "profile_mode": "BALANCED",
            "seed": "TEST-ROUTE-SEED-01",
        },
    )
    assert res.status_code == 200
    start_data = res.json()
    run_id = start_data["run_id"]
    assert run_id.startswith("BM-")
    assert start_data["profile_mode"] == "BALANCED"

    # Poll until completed
    completed = False
    for _ in range(40):
        time.sleep(0.05)
        poll_res = client.get(f"/benchmark/runs/{run_id}")
        assert poll_res.status_code == 200
        run_data = poll_res.json()
        if run_data.get("status") in ("COMPLETED", "CANCELLED"):
            completed = True
            break

    assert completed
    assert run_data["total_requested"] == 7
    assert run_data["processed_count"] == 7
    assert len(run_data["transactions"]) == 7
    assert run_data["summary"] is not None
    assert "average_risk_score" in run_data["summary"]
    assert "risk_distribution" in run_data["summary"]


def test_cancel_benchmark_run():
    # Start a larger run to test cancel
    res = client.post(
        "/benchmark/start",
        json={"num_transactions": 100, "profile_mode": "BALANCED"},
    )
    assert res.status_code == 200
    run_id = res.json()["run_id"]

    cancel_res = client.post(f"/benchmark/runs/{run_id}/cancel")
    assert cancel_res.status_code == 200
    data = cancel_res.json()
    assert data["run_id"] == run_id


def test_list_benchmark_runs():
    res = client.get("/benchmark/runs")
    assert res.status_code == 200
    data = res.json()
    assert "runs" in data
    assert "total_runs" in data
    assert isinstance(data["runs"], list)


def test_custom_evaluate_endpoint():
    payload = {
        "sender_account": "ACC-TEST-ALICE",
        "receiver_account": "ACC-TEST-BOB",
        "amount": 220000.0,
        "channel": "UPI",
        "is_night_time": True,
        "on_active_call": True,
        "is_new_receiver": True,
    }
    res = client.post("/benchmark/custom-evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "transaction" in data
    assert "policy_decision" in data
    assert "execution_record" in data
    tx = data["transaction"]
    assert tx["amount"] == 220000.0
    assert tx["risk_score"] >= 70
    assert data["policy_decision"]["action"] in ("FREEZE", "ESCALATE_ANALYST_REVIEW")


def test_export_csv_endpoint():
    # Trigger export on an existing run
    runs = benchmark_service.list_runs()
    if not runs:
        # Create quick run
        res = client.post(
            "/benchmark/start",
            json={"num_transactions": 5, "profile_mode": "BASELINE", "single_profile": "BASELINE"},
        )
        run_id = res.json()["run_id"]
        time.sleep(0.3)
    else:
        run_id = runs[0]["run_id"]

    res = client.get(f"/benchmark/runs/{run_id}/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "sentinel_benchmark_" in res.headers.get("content-disposition", "")
    content = res.text
    assert "transaction_id,benchmark_run_id" in content


def test_two_phase_route_lifecycle():
    # 1. Generate unevaluated batch
    gen_res = client.post(
        "/benchmark/generate",
        json={
            "num_transactions": 6,
            "profile_mode": "BALANCED",
            "seed": "ROUTE-TWO-PHASE-SEED",
        },
    )
    assert gen_res.status_code == 200
    run_data = gen_res.json()
    run_id = run_data["run_id"]
    assert run_data["status"] == "UNEVALUATED"
    assert len(run_data["transactions"]) == 6
    for t in run_data["transactions"]:
        assert t["status"] == "UNEVALUATED"
        assert t["risk_score"] is None

    # 2. Add a custom transaction input before evaluation
    add_res = client.post(
        f"/benchmark/runs/{run_id}/add-input",
        json={
            "sender_account": "ACC-TEST-ADD-01",
            "receiver_account": "ACC-TEST-ADD-02",
            "amount": 99000.0,
            "channel": "UPI",
            "on_active_call": True,
        },
    )
    assert add_res.status_code == 200
    assert add_res.json()["total_requested"] == 7

    # 3. Explicitly trigger evaluation
    eval_res = client.post(f"/benchmark/runs/{run_id}/evaluate")
    assert eval_res.status_code == 200
    assert eval_res.json()["status"] == "EVALUATING"

    # 4. Poll until completed
    completed = False
    for _ in range(40):
        time.sleep(0.05)
        poll = client.get(f"/benchmark/runs/{run_id}")
        assert poll.status_code == 200
        if poll.json().get("status") in ("COMPLETED", "CANCELLED"):
            completed = True
            break

    assert completed
    final_data = poll.json()
    assert final_data["status"] == "COMPLETED"
    assert final_data["processed_count"] == 7
    assert final_data["successful_count"] == 7
    for t in final_data["transactions"]:
        assert t["status"] == "SUCCESS"
        assert t["risk_score"] is not None


def test_single_transaction_evaluation_route():
    """
    Validates POST /benchmark/runs/{run_id}/transactions/{tx_id}/evaluate
    evaluates ONLY the specified transaction and preserves untouched state of other transactions.
    """
    # 1. Generate unevaluated batch with 5 transactions
    gen_res = client.post(
        "/benchmark/generate",
        json={"num_transactions": 5, "profile_mode": "BALANCED", "seed": "ROUTE-SINGLE-TEST-01"},
    )
    assert gen_res.status_code == 200
    batch = gen_res.json()
    run_id = batch["run_id"]
    txs = batch["transactions"]
    assert len(txs) == 5

    target_tx = txs[2]
    target_tx_id = target_tx["tx_id"]

    # 2. Call single transaction evaluate route
    eval_res = client.post(f"/benchmark/runs/{run_id}/transactions/{target_tx_id}/evaluate")
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["run_id"] == run_id
    assert eval_data["tx_id"] == target_tx_id
    assert eval_data["transaction"]["evaluation_state"] == "EVALUATED"
    assert isinstance(eval_data["transaction"]["risk_score"], float)

    # 3. Fetch entire run and verify isolation
    poll = client.get(f"/benchmark/runs/{run_id}")
    assert poll.status_code == 200
    run_state = poll.json()
    run_txs = run_state["transactions"]

    # TX 0, 1, 3, 4 must remain UNEVALUATED
    assert run_txs[0]["evaluation_state"] == "UNEVALUATED"
    assert run_txs[0]["risk_score"] is None
    assert run_txs[1]["evaluation_state"] == "UNEVALUATED"
    assert run_txs[1]["risk_score"] is None
    assert run_txs[2]["evaluation_state"] == "EVALUATED"
    assert run_txs[2]["risk_score"] == eval_data["transaction"]["risk_score"]
    assert run_txs[3]["evaluation_state"] == "UNEVALUATED"
    assert run_txs[3]["risk_score"] is None
    assert run_txs[4]["evaluation_state"] == "UNEVALUATED"
    assert run_txs[4]["risk_score"] is None

    # Summary reflects 1 evaluated
    assert run_state["summary"]["successful"] == 1

    # 4. Error testing: invalid tx_id
    invalid_tx_res = client.post(f"/benchmark/runs/{run_id}/transactions/NON_EXISTENT_TX/evaluate")
    assert invalid_tx_res.status_code == 404

    # 5. Error testing: invalid run_id
    invalid_run_res = client.post(f"/benchmark/runs/INVALID_RUN/transactions/{target_tx_id}/evaluate")
    assert invalid_run_res.status_code == 404


def test_case_3_batch_evaluation_processes_all():
    """
    Case 3 — Batch evaluation:
    Clicking EVALUATE BENCHMARK processes the whole eligible benchmark dataset.
    """
    gen_res = client.post(
        "/benchmark/generate",
        json={"num_transactions": 4, "profile_mode": "BALANCED", "seed": "BATCH-EVAL-TEST-01"},
    )
    assert gen_res.status_code == 200
    run_id = gen_res.json()["run_id"]

    # 1. Single-evaluate TX #1 first
    tx1_id = gen_res.json()["transactions"][0]["tx_id"]
    client.post(f"/benchmark/runs/{run_id}/transactions/{tx1_id}/evaluate")

    # 2. Trigger Batch Evaluation (EVALUATE BENCHMARK)
    batch_eval_res = client.post(f"/benchmark/runs/{run_id}/evaluate")
    assert batch_eval_res.status_code == 200

    # Poll until completed
    completed = False
    for _ in range(40):
        time.sleep(0.05)
        poll = client.get(f"/benchmark/runs/{run_id}")
        if poll.json().get("status") in ("COMPLETED", "CANCELLED"):
            completed = True
            break

    assert completed
    run_data = poll.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["processed_count"] == 4
    assert run_data["successful_count"] == 4
    for t in run_data["transactions"]:
        assert t["evaluation_state"] in ("EVALUATED", "RE_EVALUATED")
        assert t["risk_score"] is not None

