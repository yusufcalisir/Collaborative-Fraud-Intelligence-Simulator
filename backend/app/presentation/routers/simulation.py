"""Simulation API endpoints.

Handles creating, listing, and retrieving simulation runs.
Simulation execution is dispatched to Celery workers.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.application.schemas.simulation import (
    BankComparisonResponse,
    BankResponse,
    ComparisonResponse,
    DataProfileResponse,
    MetricsResponse,
    SimulationConfigRequest,
    SimulationCreateResponse,
    SimulationDetailResponse,
    SimulationSummaryResponse,
)
from app.domain.enums import PrivacyMechanism, SimulationStatus
from app.tasks.simulation_tasks import run_simulation_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])


# ── In-memory store for simulation results ─────
# In a full deployment, these would come from the database.
# For the simulator, we store results from completed Celery tasks here.
_simulation_results: dict[str, dict] = {}
_simulation_tasks: dict[str, str] = {}  # simulation_id → celery_task_id


@router.post(
    "",
    response_model=SimulationCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_simulation(
    config: SimulationConfigRequest,
) -> SimulationCreateResponse:
    """Start a new federated learning simulation.

    The simulation runs asynchronously in a Celery worker.
    Poll GET /simulations/{id} or connect to the WebSocket for progress.
    """
    import uuid

    simulation_id = str(uuid.uuid4())

    # Build config dict for Celery task
    config_dict = {
        "num_rounds": config.num_rounds,
        "local_epochs": config.local_epochs,
        "learning_rate": config.learning_rate,
        "batch_size": config.batch_size,
        "min_clients_per_round": config.min_clients_per_round,
        "enable_latency_simulation": config.enable_latency_simulation,
        "latency_range_ms": (config.latency_min_ms, config.latency_max_ms),
        "enable_dropout_simulation": config.enable_dropout_simulation,
        "dropout_probability": config.dropout_probability,
        "enable_reconnect_simulation": config.enable_reconnect_simulation,
        "enable_differential_privacy": config.privacy_mechanism
        in (
            PrivacyMechanism.DIFFERENTIAL_PRIVACY,
            PrivacyMechanism.BOTH,
        ),
        "dp_epsilon": config.dp_epsilon,
        "dp_delta": config.dp_delta,
        "dp_max_grad_norm": config.dp_max_grad_norm,
        "enable_secure_aggregation": config.privacy_mechanism
        in (
            PrivacyMechanism.SECURE_AGGREGATION,
            PrivacyMechanism.BOTH,
        ),
        "bank_a_transactions": config.bank_a_transactions,
        "bank_b_transactions": config.bank_b_transactions,
        "bank_c_transactions": config.bank_c_transactions,
    }

    # Dispatch to Celery
    task = run_simulation_task.delay(config_dict)
    _simulation_tasks[simulation_id] = task.id

    # Store pending status
    _simulation_results[simulation_id] = {
        "id": simulation_id,
        "status": SimulationStatus.PENDING.value,
        "config": config_dict,
        "current_round": 0,
        "total_rounds": config.num_rounds,
        "celery_task_id": task.id,
        "banks": [],
        "rounds": [],
    }

    logger.info("Dispatched simulation %s as Celery task %s", simulation_id, task.id)

    return SimulationCreateResponse(
        id=simulation_id,
        status=SimulationStatus.PENDING,
        message=f"Simulation queued. Task ID: {task.id}",
    )


@router.get("", response_model=list[SimulationSummaryResponse])
async def list_simulations() -> list[SimulationSummaryResponse]:
    """List all simulation runs."""
    # Check for completed Celery tasks and update results
    _sync_task_results()

    summaries = []
    for sim in _simulation_results.values():
        summaries.append(
            SimulationSummaryResponse(
                id=sim["id"],
                status=SimulationStatus(sim["status"]),
                current_round=sim.get("current_round", 0),
                total_rounds=sim.get("total_rounds", 10),
                progress_pct=_calc_progress(sim),
                created_at=sim.get("created_at", "2026-01-01T00:00:00Z"),
                completed_at=sim.get("completed_at"),
                duration_seconds=sim.get("duration_seconds"),
            )
        )

    return summaries


@router.get("/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(simulation_id: str) -> SimulationDetailResponse:
    """Get full simulation details including metrics."""
    _sync_task_results()

    sim = _simulation_results.get(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Build bank responses
    bank_responses = []
    for bank_data in sim.get("banks", []):
        bank_resp = BankResponse(
            id=bank_data["id"],
            name=bank_data["name"],
            tier=bank_data["tier"],
            fraud_ratio=bank_data["fraud_ratio"],
            num_transactions=bank_data["num_transactions"],
            status=bank_data.get("status", "active"),
            local_metrics=_build_metrics_response(bank_data.get("local_metrics")),
            federated_metrics=_build_metrics_response(bank_data.get("federated_metrics")),
            improvement=bank_data.get("improvement"),
            data_profile=_build_profile_response(bank_data.get("data_profile")),
        )
        bank_responses.append(bank_resp)

    config = sim.get("config", {})

    return SimulationDetailResponse(
        id=sim["id"],
        status=SimulationStatus(sim["status"]),
        config=SimulationConfigRequest(
            num_rounds=config.get("num_rounds", 10),
            local_epochs=config.get("local_epochs", 3),
            learning_rate=config.get("learning_rate", 0.001),
            batch_size=config.get("batch_size", 64),
        ),
        current_round=sim.get("current_round", 0),
        total_rounds=sim.get("total_rounds", 10),
        progress_pct=_calc_progress(sim),
        created_at=sim.get("created_at", "2026-01-01T00:00:00Z"),
        started_at=sim.get("started_at"),
        completed_at=sim.get("completed_at"),
        duration_seconds=sim.get("duration_seconds"),
        error_message=sim.get("error_message"),
        banks=bank_responses,
        rounds=[],  # Rounds are in the training router
    )


@router.get("/{simulation_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(simulation_id: str) -> ComparisonResponse:
    """Get local vs federated comparison for all banks."""
    _sync_task_results()

    sim = _simulation_results.get(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim["status"] != SimulationStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Simulation not yet completed")

    bank_comparisons = []
    total_improvement: dict[str, float] = {}

    for bank_data in sim.get("banks", []):
        local = bank_data.get("local_metrics")
        federated = bank_data.get("federated_metrics")
        if not local or not federated:
            continue

        improvement = bank_data.get("improvement", {})
        bank_comparisons.append(
            BankComparisonResponse(
                bank_id=bank_data["id"],
                bank_name=bank_data["name"],
                local_metrics=_build_metrics_response(local),
                federated_metrics=_build_metrics_response(federated),
                improvement=improvement,
            )
        )

        for k, v in improvement.items():
            total_improvement[k] = total_improvement.get(k, 0) + v

    n = len(bank_comparisons) or 1
    avg_improvement = {k: round(v / n, 4) for k, v in total_improvement.items()}

    return ComparisonResponse(
        simulation_id=simulation_id,
        banks=bank_comparisons,
        aggregate_improvement=avg_improvement,
    )


# ── Helpers ─────────────────────────────────────


def _sync_task_results() -> None:
    """Check for completed Celery tasks and merge results."""
    from celery.result import AsyncResult

    for sim_id, task_id in list(_simulation_tasks.items()):
        result = AsyncResult(task_id)
        if result.ready():
            try:
                task_result = result.get(timeout=1)
                if isinstance(task_result, dict):
                    # Merge task results into our store
                    existing = _simulation_results.get(sim_id, {})
                    existing.update(task_result)
                    existing["id"] = sim_id  # Keep original ID
                    _simulation_results[sim_id] = existing
            except Exception:
                logger.warning("Failed to get result for task %s", task_id)
                sim = _simulation_results.get(sim_id, {})
                sim["status"] = SimulationStatus.FAILED.value
            finally:
                del _simulation_tasks[sim_id]


def _calc_progress(sim: dict) -> float:
    total = sim.get("total_rounds", 10)
    current = sim.get("current_round", 0)
    if total == 0:
        return 0.0
    return min(100.0, (current / total) * 100)


def _build_metrics_response(data: dict | None) -> MetricsResponse | None:
    if not data:
        return None
    return MetricsResponse(
        accuracy=data.get("accuracy", 0),
        precision=data.get("precision", 0),
        recall=data.get("recall", 0),
        f1_score=data.get("f1_score", 0),
        auc_roc=data.get("auc_roc", 0),
        loss=data.get("loss", 0),
        confusion_matrix=data.get("confusion_matrix", [[0, 0], [0, 0]]),
        roc_fpr=data.get("roc_fpr", []),
        roc_tpr=data.get("roc_tpr", []),
        roc_thresholds=data.get("roc_thresholds", []),
        feature_importance=data.get("feature_importance", {}),
    )


def _build_profile_response(data: dict | None) -> DataProfileResponse | None:
    if not data:
        return None
    return DataProfileResponse(**data)
