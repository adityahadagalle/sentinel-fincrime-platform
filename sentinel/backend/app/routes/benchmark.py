"""
SENTINEL Benchmark Lab API Routes.

Exposes endpoints for initiating benchmark runs, polling live progress,
retrieving transaction results, exporting CSV audit records, canceling runs,
and evaluating custom transactions.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.repositories.base import AbstractCaseRepository
from app.repositories.dependencies import get_repository
from app.services.benchmark_service import benchmark_service, SUPPORTED_PROFILES

router = APIRouter(prefix="/benchmark", tags=["Benchmark Lab"])


class BenchmarkStartRequest(BaseModel):
    num_transactions: int = Field(default=100, ge=1, le=500, description="Total transactions to evaluate (1-500)")
    profile_mode: str = Field(default="BALANCED", description="SINGLE, BALANCED, or CUSTOM_MIX")
    single_profile: Optional[str] = Field(default=None, description="Profile name if profile_mode is SINGLE")
    custom_distribution: Optional[Dict[str, float]] = Field(default=None, description="Percentage/weights for CUSTOM_MIX")
    seed: Optional[str] = Field(default=None, description="Reproducibility seed string")
    auto_evaluate: bool = Field(default=True, description="If True, immediately evaluates. If False, keeps inputs as unevaluated.")


class CustomTransactionRequest(BaseModel):
    tx_id: Optional[str] = None
    sender_account: Optional[str] = "ACC-BM-SENDER-01"
    receiver_account: Optional[str] = "ACC-BM-RECEIVER-99"
    amount: float = Field(default=25000.0, ge=1.0)
    channel: str = Field(default="UPI")
    avg_monthly_tx_amount: float = Field(default=25000.0, ge=0.0)
    is_night_time: bool = False
    on_active_call: bool = False
    is_new_receiver: bool = False
    is_cross_border: bool = False
    velocity_flag: bool = False
    device_changed: bool = False
    hop_number: int = 0
    timestamp: Optional[str] = None


@router.get("/profiles")
async def get_benchmark_profiles() -> Dict[str, Any]:
    """
    Returns list of supported benchmark feature profiles and their descriptions.
    """
    return {
        "supported_profiles": SUPPORTED_PROFILES,
        "descriptions": {
            "BASELINE": "Routine normal daytime transaction within account baseline; no anomalous signals.",
            "NEW_RECEIVER": "Transfer to a first-time payee destination account with normal amount and daytime hours.",
            "AMOUNT_ANOMALY": "Transfer amount significantly exceeds account baseline (5x - 10x ratio) with normal hours.",
            "TIME_ANOMALY": "Routine transfer executed during the deep night window (10 PM – 6 AM).",
            "ACTIVE_CALL": "Transfer executed while the sender is actively on an unverified phone call (Social Engineering flag).",
            "MULTI_SIGNAL": "Compound attack pattern: massive amount spike + nighttime hours + new receiver + active call.",
            "MULTI_HOP": "Multi-stage layered flow across chained synthetic accounts testing case and graph topology.",
        },
    }


@router.post("/generate")
async def generate_benchmark_batch(
    payload: BenchmarkStartRequest,
) -> Dict[str, Any]:
    """
    Phase 1: Generates a batch of test transactions strictly as UNEVALUATED INPUTS.
    Risk scores and policy decisions are NOT assigned.
    Returns the created run with its raw transaction inputs for user review.
    """
    mode = payload.profile_mode.upper()
    if mode not in ("SINGLE", "BALANCED", "CUSTOM_MIX"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile_mode '{payload.profile_mode}'. Must be SINGLE, BALANCED, or CUSTOM_MIX.",
        )

    if mode == "SINGLE" and payload.single_profile:
        if payload.single_profile.upper() not in SUPPORTED_PROFILES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown profile '{payload.single_profile}'. Supported: {SUPPORTED_PROFILES}",
            )

    run_id = benchmark_service.create_benchmark_batch(
        num_transactions=payload.num_transactions,
        profile_mode=mode,
        single_profile=payload.single_profile,
        custom_distribution=payload.custom_distribution,
        seed=payload.seed,
    )

    run = benchmark_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to initialize benchmark input batch.")
    return run


@router.post("/runs/{run_id}/evaluate")
async def evaluate_benchmark_run(
    run_id: str,
    repo: AbstractCaseRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """
    Phase 2: User explicitly triggers SENTINEL evaluation.
    Routes every transaction in the run through real rule scoring, ML emulation,
    case linking, autonomous policy engine, and simulated action execution.
    """
    run = benchmark_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")

    try:
        await benchmark_service.evaluate_benchmark_batch(run_id, repo=repo)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    return {
        "run_id": run_id,
        "status": "EVALUATING",
        "message": "SENTINEL pipeline evaluation started.",
        "total_requested": run.get("total_requested", 0),
    }


@router.post("/runs/{run_id}/transactions/{tx_id}/evaluate")
async def evaluate_single_benchmark_transaction(
    run_id: str,
    tx_id: str,
    repo: AbstractCaseRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """
    Evaluates ONLY a single transaction within a benchmark run.
    Enforces transaction scope: all other transactions in the batch remain untouched.
    """
    run = benchmark_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")

    try:
        updated_tx = await benchmark_service.evaluate_single_transaction_in_batch(
            run_id=run_id,
            tx_id=tx_id,
            repo=repo,
        )
        return {
            "run_id": run_id,
            "tx_id": tx_id,
            "transaction": updated_tx,
            "summary": run.get("summary"),
            "status": run.get("status"),
            "message": f"Transaction {tx_id} evaluated successfully.",
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed for transaction {tx_id}: {str(e)}")


@router.post("/runs/{run_id}/add-input")
async def add_custom_input_to_run(
    run_id: str,
    payload: CustomTransactionRequest,
) -> Dict[str, Any]:
    """
    Adds a custom manual test transaction into an existing unevaluated batch.
    """
    run = benchmark_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")

    try:
        tx_record = benchmark_service.add_custom_input_to_batch(
            run_id=run_id,
            custom_input=payload.model_dump(),
        )
        return {
            "run_id": run_id,
            "status": run.get("status"),
            "transaction": tx_record,
            "total_requested": run.get("total_requested"),
            "message": "Custom test input added to batch.",
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/start")
async def start_benchmark(
    payload: BenchmarkStartRequest,
    repo: AbstractCaseRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """
    Initiates controlled benchmark run. If auto_evaluate is True (default for automated calls),
    generates and evaluates immediately. If False, generates unevaluated inputs only.
    """
    mode = payload.profile_mode.upper()
    if mode not in ("SINGLE", "BALANCED", "CUSTOM_MIX"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile_mode '{payload.profile_mode}'. Must be SINGLE, BALANCED, or CUSTOM_MIX.",
        )

    if mode == "SINGLE" and payload.single_profile:
        if payload.single_profile.upper() not in SUPPORTED_PROFILES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown profile '{payload.single_profile}'. Supported: {SUPPORTED_PROFILES}",
            )

    if payload.auto_evaluate:
        run_id = await benchmark_service.execute_benchmark_run(
            num_transactions=payload.num_transactions,
            profile_mode=mode,
            single_profile=payload.single_profile,
            custom_distribution=payload.custom_distribution,
            seed=payload.seed,
            repo=repo,
        )
    else:
        run_id = benchmark_service.create_benchmark_batch(
            num_transactions=payload.num_transactions,
            profile_mode=mode,
            single_profile=payload.single_profile,
            custom_distribution=payload.custom_distribution,
            seed=payload.seed,
        )

    run = benchmark_service.get_run(run_id)
    return {
        "run_id": run_id,
        "status": run.get("status") if run else ("RUNNING" if payload.auto_evaluate else "UNEVALUATED"),
        "num_transactions": payload.num_transactions,
        "profile_mode": mode,
        "distribution": run.get("distribution") if run else {},
        "seed": run.get("seed") if run else payload.seed,
        "created_at": run.get("created_at") if run else "",
        "auto_evaluate": payload.auto_evaluate,
    }


@router.get("/runs/{run_id}")
async def get_benchmark_run(run_id: str) -> Dict[str, Any]:
    """
    Fetches the current state, progress counters, KPIs, and individual transaction results for a run.
    """
    run = benchmark_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
    return run


@router.post("/runs/{run_id}/cancel")
async def cancel_benchmark_run(run_id: str) -> Dict[str, Any]:
    """
    Cooperatively cancels an ongoing benchmark run.
    """
    success = benchmark_service.cancel_run(run_id)
    if not success:
        run = benchmark_service.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
        return {"run_id": run_id, "status": run.get("status"), "message": "Run is not actively running."}
    return {"run_id": run_id, "status": "CANCEL_REQUESTED", "message": "Cancellation request acknowledged."}


@router.get("/runs")
async def list_benchmark_runs() -> Dict[str, Any]:
    """
    Lists recent benchmark runs with summary KPIs for history and comparison.
    """
    runs = benchmark_service.list_runs()
    return {"runs": runs, "total_runs": len(runs)}


@router.post("/custom-evaluate")
async def custom_evaluate_transaction(
    payload: CustomTransactionRequest,
    repo: AbstractCaseRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """
    Evaluates a single manual custom transaction through the exact same SENTINEL pipeline.
    """
    result = await benchmark_service.evaluate_custom_transaction(
        custom_input=payload.model_dump(),
        repo=repo,
    )
    return result


@router.get("/runs/{run_id}/export")
async def export_benchmark_csv(run_id: str) -> Response:
    """
    Downloads a 16-field UTF-8 BOM CSV audit log for the benchmark run.
    """
    csv_data = benchmark_service.export_csv(run_id)
    if not csv_data:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found or empty.")

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=sentinel_benchmark_{run_id}.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
