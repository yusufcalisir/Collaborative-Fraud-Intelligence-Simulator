"""Simulation API endpoints.

Handles creating, listing, and retrieving simulation runs.
Simulation execution runs in background threads within the web process.
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])


# ── In-memory stores ───────────────────────────
# In a full deployment these would come from a database.
_simulation_results: dict[str, dict] = {}
_simulation_events: dict[str, list[dict]] = {}  # simulation_id → list of progress events


@router.post(
    "",
    response_model=SimulationCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_simulation(
    config: SimulationConfigRequest,
) -> SimulationCreateResponse:
    """Start a new federated learning simulation.

    Runs the simulation in a background thread within the web process.
    Poll GET /simulations/{id} for progress.
    """
    import threading
    import uuid

    simulation_id = str(uuid.uuid4())

    # Build config dict
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

    # Store pending status
    _simulation_results[simulation_id] = {
        "id": simulation_id,
        "status": SimulationStatus.PENDING.value,
        "config": config_dict,
        "current_round": 0,
        "total_rounds": config.num_rounds,
        "banks": [],
        "rounds": [],
    }

    # Run simulation in a background thread (no Celery worker needed)
    thread = threading.Thread(
        target=_run_simulation_in_process,
        args=(simulation_id, config_dict),
        daemon=True,
    )
    thread.start()

    logger.info("Started in-process simulation %s", simulation_id)

    return SimulationCreateResponse(
        id=simulation_id,
        status=SimulationStatus.PENDING,
        message=f"Simulation started in-process. ID: {simulation_id}",
    )


@router.get("", response_model=list[SimulationSummaryResponse])
async def list_simulations() -> list[SimulationSummaryResponse]:
    """List all simulation runs."""
    # Results are updated in-place by background threads

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


def _run_simulation_in_process(simulation_id: str, config_dict: dict) -> None:
    """Run the full simulation pipeline in a background thread.

    Updates ``_simulation_results`` in-place so the polling endpoints
    can return real-time progress without Celery or Redis.
    """
    from dataclasses import asdict
    from typing import Any

    from app.application.services.data_generator import DataGenerator
    from app.application.services.fl_engine import FederatedLearningEngine
    from app.application.services.metrics_service import MetricsService
    from app.application.services.model_service import ModelService
    from app.application.services.privacy_service import PrivacyService
    from app.application.services.simulation_service import SimulationService
    from app.config import get_settings
    from app.domain.value_objects import SimulationConfig

    settings = get_settings()
    logger.info("Background simulation %s starting", simulation_id)

    # Prevent PyTorch thread throttling on single-core / shared CPU hosting
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    try:
        # Mark as running
        _simulation_results[simulation_id]["status"] = SimulationStatus.GENERATING_DATA.value

        config = SimulationConfig(**config_dict)

        model_service = ModelService(settings)
        privacy_service = PrivacyService()
        fl_engine = FederatedLearningEngine(settings, model_service, privacy_service)
        data_generator = DataGenerator()
        metrics_service = MetricsService()

        simulation_service = SimulationService(
            settings=settings,
            simulation_repo=None,
            bank_repo=None,
            metrics_repo=None,
            data_generator=data_generator,
            fl_engine=fl_engine,
            metrics_service=metrics_service,
            model_service=model_service,
        )

        # Progress callback: updates in-memory state and event log
        # NOTE: simulation_service creates SimulationRun with its own uuid, so sim_id
        # passed by the service may differ from our simulation_id.  We always look up
        # by our own simulation_id (the key stored in _simulation_results).
        def progress_cb(_sim_id: str, event_type: str, data: dict[str, Any]) -> None:
            sim = _simulation_results.get(simulation_id)
            if sim:
                if event_type == "status":
                    status_val = data.get("status")
                    if status_val:
                        if hasattr(status_val, "value"):
                            sim["status"] = status_val.value
                        else:
                            sim["status"] = str(status_val)
                    logger.info(
                        "Sim %s status -> %s: %s",
                        simulation_id,
                        sim["status"],
                        data.get("message", ""),
                    )
                elif event_type == "round_complete":
                    sim["current_round"] = data.get("round", sim.get("current_round", 0))
                    sim["status"] = SimulationStatus.TRAINING_FEDERATED.value
                elif event_type == "completed":
                    sim["status"] = SimulationStatus.COMPLETED.value
                elif event_type == "error":
                    sim["status"] = SimulationStatus.FAILED.value
                    sim["error_message"] = data.get("error", "Simulation failed.")

                # Keep progress_pct fresh for polling endpoints
                sim["progress_pct"] = _calc_progress(sim)

            # Store every event so the training router can serve them
            _simulation_events.setdefault(simulation_id, []).append(
                {"event_type": event_type, "data": data}
            )

        simulation = simulation_service.run_simulation(
            config=config,
            progress_callback=progress_cb,
        )

        # Serialize and store results
        result: dict[str, Any] = {
            "id": simulation_id,
            "status": simulation.status.value,
            "current_round": simulation.current_round,
            "total_rounds": simulation.total_rounds,
            "created_at": simulation.created_at.isoformat() if simulation.created_at else None,
            "started_at": simulation.started_at.isoformat() if simulation.started_at else None,
            "completed_at": simulation.completed_at.isoformat()
            if simulation.completed_at
            else None,
            "duration_seconds": simulation.duration_seconds,
            "error_message": simulation.error_message,
            "banks": [],
        }

        for bank in simulation.banks:
            bank_dict: dict[str, Any] = {
                "id": bank.id,
                "name": bank.name,
                "tier": bank.tier.value,
                "fraud_ratio": bank.fraud_ratio,
                "num_transactions": bank.num_transactions,
                "status": bank.status.value,
            }
            if bank.data_profile:
                bank_dict["data_profile"] = asdict(bank.data_profile)
            if bank.local_metrics:
                bank_dict["local_metrics"] = asdict(bank.local_metrics)
            if bank.federated_metrics:
                bank_dict["federated_metrics"] = asdict(bank.federated_metrics)
            if bank.improvement:
                bank_dict["improvement"] = bank.improvement
            result["banks"].append(bank_dict)

        # Preserve config in the stored result
        result["config"] = config_dict
        _simulation_results[simulation_id] = result

        logger.info(
            "Background simulation %s completed: %s", simulation_id, simulation.status.value
        )

    except Exception as exc:
        import traceback

        tb = traceback.format_exc()
        logger.exception("Background simulation %s failed", simulation_id)
        sim = _simulation_results.get(simulation_id, {})
        sim["status"] = SimulationStatus.FAILED.value
        # Surface the real error to the frontend so it can be debugged
        sim["error_message"] = f"{type(exc).__name__}: {exc}\n{tb[-500:]}"
        _simulation_results[simulation_id] = sim


def _calc_progress(sim: dict) -> float:
    status = sim.get("status")
    if status == SimulationStatus.COMPLETED.value:
        return 100.0
    if status == SimulationStatus.FAILED.value:
        return 100.0
    if status == SimulationStatus.EVALUATING.value:
        return 95.0

    total = sim.get("total_rounds", 10)
    current = sim.get("current_round", 0)

    if status == SimulationStatus.GENERATING_DATA.value:
        return 5.0
    if status == SimulationStatus.TRAINING_LOCAL.value:
        return 15.0

    # For training_federated, scale from 15% to 90%
    if total == 0:
        return 15.0
    fed_progress = 15.0 + (current / total) * 75.0
    return min(90.0, fed_progress)


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
