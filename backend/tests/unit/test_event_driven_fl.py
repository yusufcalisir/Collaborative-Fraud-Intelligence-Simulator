"""Unit and integration tests for the Redis Event-Driven Federated Learning Engine."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.data_generator import DataGenerator
from app.application.services.fl_engine import FederatedLearningEngine
from app.application.services.metrics_service import MetricsService
from app.application.services.model_service import ModelService
from app.application.services.privacy_service import PrivacyService
from app.application.services.simulation_service import SimulationService
from app.config import get_settings
from app.domain.value_objects import SimulationConfig
from app.presentation.messaging.redis_listener import RedisBankClientListener


@pytest.mark.asyncio
async def test_redis_bank_client_listener_lifecycle() -> None:
    """Verify that the background listener consumes commands and publishes responses correctly."""
    mock_redis = MagicMock()
    mock_pubsub = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub

    listener = RedisBankClientListener(redis_url="redis://localhost:6379", bank_id="bank_a")
    listener.redis = mock_redis
    listener.pubsub = mock_pubsub

    # Mock the receive message channel for training
    train_payload = {
        "weights": {
            "layer_shapes": [[1, 2]],
            "flat_weights": [0.1, 0.2],
        },
        "learning_rate": 0.01,
        "batch_size": 32,
        "epochs": 1,
        "enable_dp": False,
        "correlation_id": "test_train_123",
    }

    with patch.object(listener, "_handle_train", new_callable=AsyncMock) as mock_handle_train:

        def stop_loop(*args: Any, **kwargs: Any) -> None:
            listener.is_running = False

        mock_handle_train.side_effect = stop_loop

        mock_pubsub.get_message.side_effect = [
            {"channel": "bank_client_bank_a_train", "data": json.dumps(train_payload)},
            None,
        ]

        listener.is_running = True
        await listener._listen_loop()

        mock_handle_train.assert_called_once_with(train_payload)


def test_event_driven_simulation_orchestration() -> None:
    """Verify that the coordinator orchestrates a complete run via Redis pub/sub events."""
    settings = get_settings()
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

    config = SimulationConfig(
        num_rounds=1,
        local_epochs=1,
        learning_rate=0.01,
        batch_size=32,
        min_clients_per_round=2,
        enable_latency_simulation=False,
        enable_dropout_simulation=False,
        enable_reconnect_simulation=True,
        enable_differential_privacy=False,
        bank_a_transactions=1000,
        bank_b_transactions=1000,
        bank_c_transactions=1000,
        fl_engine_type="event_driven",
    )

    model = model_service.create_model()
    weights = model_service.get_parameters(model)
    weights_payload = {
        "layer_shapes": [list(shape) for shape in weights.layer_shapes],
        "flat_weights": weights.flat_weights,
    }

    # Sequence of mock events that the coordinator will receive
    mock_responses = [
        # Init replies
        {
            "channel": "bank_client_bank_a_init_response",
            "data": json.dumps({"status": "initialized", "correlation_id": ""}),
        },
        {
            "channel": "bank_client_bank_b_init_response",
            "data": json.dumps({"status": "initialized", "correlation_id": ""}),
        },
        {
            "channel": "bank_client_bank_c_init_response",
            "data": json.dumps({"status": "initialized", "correlation_id": ""}),
        },
        # Train replies
        {
            "channel": "bank_client_bank_a_train_response",
            "data": json.dumps(
                {"weights": weights_payload, "num_samples": 500, "loss": 0.25, "correlation_id": ""}
            ),
        },
        {
            "channel": "bank_client_bank_b_train_response",
            "data": json.dumps(
                {"weights": weights_payload, "num_samples": 500, "loss": 0.28, "correlation_id": ""}
            ),
        },
        {
            "channel": "bank_client_bank_c_train_response",
            "data": json.dumps(
                {"weights": weights_payload, "num_samples": 500, "loss": 0.30, "correlation_id": ""}
            ),
        },
        # Evaluate replies (training loop round evaluation)
        {
            "channel": "bank_client_bank_a_evaluate_response",
            "data": json.dumps({"loss": 0.24, "correlation_id": ""}),
        },
        {
            "channel": "bank_client_bank_b_evaluate_response",
            "data": json.dumps({"loss": 0.26, "correlation_id": ""}),
        },
        {
            "channel": "bank_client_bank_c_evaluate_response",
            "data": json.dumps({"loss": 0.27, "correlation_id": ""}),
        },
        # Evaluate replies (final Phase 4 evaluation)
        {
            "channel": "bank_client_bank_a_evaluate_response",
            "data": json.dumps(
                {
                    "loss": 0.24,
                    "num_samples": 100,
                    "accuracy": 0.9,
                    "precision": 0.9,
                    "recall": 0.9,
                    "f1_score": 0.9,
                    "auc_roc": 0.9,
                    "confusion_matrix": [[50, 0], [0, 50]],
                    "roc_fpr": [0.0, 1.0],
                    "roc_tpr": [0.0, 1.0],
                    "roc_thresholds": [1.0, 0.0],
                    "correlation_id": "",
                }
            ),
        },
        {
            "channel": "bank_client_bank_b_evaluate_response",
            "data": json.dumps(
                {
                    "loss": 0.26,
                    "num_samples": 100,
                    "accuracy": 0.9,
                    "precision": 0.9,
                    "recall": 0.9,
                    "f1_score": 0.9,
                    "auc_roc": 0.9,
                    "confusion_matrix": [[50, 0], [0, 50]],
                    "roc_fpr": [0.0, 1.0],
                    "roc_tpr": [0.0, 1.0],
                    "roc_thresholds": [1.0, 0.0],
                    "correlation_id": "",
                }
            ),
        },
        {
            "channel": "bank_client_bank_c_evaluate_response",
            "data": json.dumps(
                {
                    "loss": 0.27,
                    "num_samples": 100,
                    "accuracy": 0.9,
                    "precision": 0.9,
                    "recall": 0.9,
                    "f1_score": 0.9,
                    "auc_roc": 0.9,
                    "confusion_matrix": [[50, 0], [0, 50]],
                    "roc_fpr": [0.0, 1.0],
                    "roc_tpr": [0.0, 1.0],
                    "roc_thresholds": [1.0, 0.0],
                    "correlation_id": "",
                }
            ),
        },
    ]

    mock_redis_sync = MagicMock()
    mock_pubsub_sync = MagicMock()
    mock_redis_sync.pubsub.return_value = mock_pubsub_sync

    def mock_publish(channel: str, message: str) -> None:
        data = json.loads(message)
        cid = data.get("correlation_id")

        for resp in mock_responses:
            if resp["channel"] == f"{channel}_response":
                rdata = json.loads(resp["data"])
                # Match correlation IDs dynamically
                if (
                    cid.startswith("init_")
                    and resp["channel"].endswith("_init_response")
                    or cid.startswith("train_")
                    and resp["channel"].endswith("_train_response")
                    or cid.startswith("evaluate_final_")
                    and resp["channel"].endswith("_evaluate_response")
                    and "accuracy" in rdata
                    or cid.startswith("evaluate_")
                    and resp["channel"].endswith("_evaluate_response")
                    and "accuracy" not in rdata
                ):
                    rdata["correlation_id"] = cid
                    resp["data"] = json.dumps(rdata)

    mock_redis_sync.publish.side_effect = mock_publish

    msg_iter = iter(mock_responses)

    def mock_get_message(*args: Any, **kwargs: Any) -> Any:
        try:
            return next(msg_iter)
        except StopIteration:
            return None

    mock_pubsub_sync.get_message.side_effect = mock_get_message

    with patch("redis.Redis.from_url", return_value=mock_redis_sync):
        sim_run = simulation_service.run_simulation(config)
        assert sim_run.status.value == "completed"
        assert len(sim_run.rounds) == 1
