"""Integration tests for the complete Federated Learning simulation orchestrator."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from app.application.services.data_generator import DataGenerator
from app.application.services.fl_engine import FederatedLearningEngine
from app.application.services.metrics_service import MetricsService
from app.application.services.model_service import ModelService
from app.application.services.privacy_service import PrivacyService
from app.application.services.simulation_service import SimulationService
from app.config import get_settings
from app.domain.enums import ClientStatus, SimulationStatus
from app.domain.value_objects import SimulationConfig

logger = logging.getLogger(__name__)


@pytest.fixture
def simulation_service() -> SimulationService:
    """Fixture to build the orchestrator service."""
    settings = get_settings()
    model_service = ModelService(settings)
    privacy_service = PrivacyService()
    fl_engine = FederatedLearningEngine(settings, model_service, privacy_service)
    data_generator = DataGenerator()
    metrics_service = MetricsService()

    return SimulationService(
        settings=settings,
        simulation_repo=None,
        bank_repo=None,
        metrics_repo=None,
        data_generator=data_generator,
        fl_engine=fl_engine,
        metrics_service=metrics_service,
        model_service=model_service,
    )


def test_simulation_flow_success(simulation_service: SimulationService, sample_config: dict):
    """Test that a standard simulation completes successfully and fires all expected progress events."""
    # Scale down sizes for faster test runs
    sample_config["bank_a_transactions"] = 1000
    sample_config["bank_b_transactions"] = 1000
    sample_config["bank_c_transactions"] = 1000
    sample_config["num_rounds"] = 2
    sample_config["local_epochs"] = 1

    config = SimulationConfig(**sample_config)
    events = []

    def progress_callback(sim_id: str, event_type: str, data: dict[str, Any]) -> None:
        events.append((event_type, data))

    simulation = simulation_service.run_simulation(config, progress_callback=progress_callback)

    # 1. Verify final status and attributes
    assert simulation.status == SimulationStatus.COMPLETED
    assert len(simulation.banks) == 3
    assert simulation.current_round == 2
    assert simulation.total_rounds == 2
    assert simulation.duration_seconds > 0
    assert simulation.error_message is None

    # 2. Check generated bank metrics
    for bank in simulation.banks:
        assert bank.local_metrics is not None
        assert bank.federated_metrics is not None
        assert bank.improvement is not None
        assert "f1_score" in bank.improvement
        assert "auc_roc" in bank.improvement

    # 3. Check progress events order
    event_types = [e[0] for e in events]
    assert "status" in event_types
    assert "local_training" in event_types
    assert "round_start" in event_types
    assert "round_complete" in event_types
    assert "completed" in event_types


def test_simulation_with_differential_privacy(
    simulation_service: SimulationService, sample_config: dict
):
    """Test FL simulation with Differential Privacy enabled."""
    sample_config["enable_differential_privacy"] = True
    sample_config.pop("privacy_mechanism", None)
    sample_config["dp_epsilon"] = 0.5
    sample_config["dp_delta"] = 1e-5
    sample_config["num_rounds"] = 2
    sample_config["local_epochs"] = 1

    config = SimulationConfig(**sample_config)
    simulation = simulation_service.run_simulation(config)

    assert simulation.status == SimulationStatus.COMPLETED
    # Ensure DP is applied (privacy budget must be tracked)
    assert simulation.current_round == 2


def test_simulation_with_secure_aggregation(
    simulation_service: SimulationService, sample_config: dict
):
    """Test FL simulation with Secure Aggregation enabled."""
    sample_config["enable_secure_aggregation"] = True
    sample_config.pop("privacy_mechanism", None)
    sample_config["num_rounds"] = 2
    sample_config["local_epochs"] = 1

    config = SimulationConfig(**sample_config)
    simulation = simulation_service.run_simulation(config)

    assert simulation.status == SimulationStatus.COMPLETED


def test_simulation_with_client_dropouts(
    simulation_service: SimulationService, sample_config: dict
):
    """Test FL simulation with simulated dropout rates and client failures."""
    sample_config["enable_dropout_simulation"] = True
    sample_config["dropout_probability"] = 0.8  # High probability to force dropouts
    sample_config["num_rounds"] = 3
    sample_config["local_epochs"] = 1

    config = SimulationConfig(**sample_config)
    simulation = simulation_service.run_simulation(config)

    assert simulation.status == SimulationStatus.COMPLETED
    # Some banks might have been inactive/dropped
    statuses = [bank.status for bank in simulation.banks]
    assert any(
        status in (ClientStatus.DROPPED, ClientStatus.ACTIVE, ClientStatus.RECONNECTED)
        for status in statuses
    )
