"""Celery tasks for running simulations asynchronously.

Simulations are CPU-intensive (PyTorch training) and can take minutes.
They run in Celery workers to avoid blocking the FastAPI event loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

from app.infrastructure.celery_app import celery_app

logger = logging.getLogger(__name__)


def _progress_callback(simulation_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Progress callback that stores updates in Redis.

    This runs inside the Celery worker process. It caches progress
    so the API can serve real-time status without hitting the database.
    """
    import redis as sync_redis

    from app.config import get_settings

    settings = get_settings()
    r = sync_redis.from_url(settings.redis_url, decode_responses=True)

    # Cache latest progress
    progress_key = f"simulation:{simulation_id}:progress"
    r.set(
        progress_key,
        json.dumps(
            {
                "event_type": event_type,
                "data": data,
            }
        ),
        ex=3600,
    )

    # Publish to pub/sub for WebSocket consumers
    channel = f"training:{simulation_id}"
    r.publish(
        channel,
        json.dumps(
            {
                "event_type": event_type,
                "data": data,
            }
        ),
    )

    # Store event in a list for clients that connect after events happened
    events_key = f"simulation:{simulation_id}:events"
    r.rpush(
        events_key,
        json.dumps(
            {
                "event_type": event_type,
                "data": data,
            }
        ),
    )
    r.expire(events_key, 3600)


@celery_app.task(bind=True, name="run_simulation", max_retries=0)
def run_simulation_task(self: Any, config_dict: dict) -> dict:
    """Execute a full federated learning simulation.

    This task is dispatched by the POST /simulations endpoint.
    It runs the entire pipeline: data generation → local training →
    federated training → evaluation → comparison.

    Args:
        config_dict: Serialized SimulationConfig.

    Returns:
        Serialized simulation results.
    """
    from app.application.services.data_generator import DataGenerator
    from app.application.services.fl_engine import FederatedLearningEngine
    from app.application.services.metrics_service import MetricsService
    from app.application.services.model_service import ModelService
    from app.application.services.privacy_service import PrivacyService
    from app.application.services.simulation_service import SimulationService
    from app.config import get_settings
    from app.domain.value_objects import SimulationConfig

    settings = get_settings()
    task_id = self.request.id

    logger.info("Starting simulation task %s", task_id)

    # Reconstruct config
    config = SimulationConfig(**config_dict)

    # Build services (no database — results are cached in Redis
    # and persisted by the API when the task completes)
    model_service = ModelService(settings)
    privacy_service = PrivacyService()
    fl_engine = FederatedLearningEngine(settings, model_service, privacy_service)
    data_generator = DataGenerator()
    metrics_service = MetricsService()

    simulation_service = SimulationService(
        settings=settings,
        simulation_repo=None,  # No DB access from worker
        bank_repo=None,
        metrics_repo=None,
        data_generator=data_generator,
        fl_engine=fl_engine,
        metrics_service=metrics_service,
        model_service=model_service,
    )

    # Run the simulation
    simulation = simulation_service.run_simulation(
        config=config,
        progress_callback=_progress_callback,
    )

    # Serialize results
    result = {
        "id": simulation.id,
        "status": simulation.status.value,
        "current_round": simulation.current_round,
        "total_rounds": simulation.total_rounds,
        "created_at": simulation.created_at.isoformat() if simulation.created_at else None,
        "started_at": simulation.started_at.isoformat() if simulation.started_at else None,
        "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None,
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

    logger.info("Simulation task %s completed: %s", task_id, simulation.status.value)
    return result
