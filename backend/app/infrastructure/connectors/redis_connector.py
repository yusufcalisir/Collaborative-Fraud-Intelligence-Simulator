"""Redis Pub/Sub Bank Connector implementing the connector port."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

import redis

from app.application.interfaces.bank_connector import BankConnectorInterface

if TYPE_CHECKING:
    from app.domain.value_objects import ModelWeights

logger = logging.getLogger(__name__)


class RedisBankConnector(BankConnectorInterface):
    """Sends FL commands as asynchronous events over Redis Pub/Sub."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe(
            "bank_client_bank_a_init_response",
            "bank_client_bank_b_init_response",
            "bank_client_bank_c_init_response",
            "bank_client_bank_a_train_response",
            "bank_client_bank_b_train_response",
            "bank_client_bank_c_train_response",
            "bank_client_bank_a_evaluate_response",
            "bank_client_bank_b_evaluate_response",
            "bank_client_bank_c_evaluate_response",
        )

    def initialize(
        self,
        bank_id: str,
        num_transactions: int,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Trigger event-driven bank dataset initialization."""
        correlation_id = f"init_conn_{bank_id}_{int(time.time())}"
        payload = {
            "bank_id": bank_id,
            "num_transactions": num_transactions,
            "seed": seed,
            "correlation_id": correlation_id,
        }
        self.redis_client.publish(f"bank_client_{bank_id}_init", json.dumps(payload))

        start_time = time.perf_counter()
        while (time.perf_counter() - start_time) < 20.0:
            msg = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if msg and msg["channel"] == f"bank_client_{bank_id}_init_response":
                resp_data = json.loads(msg["data"])
                if resp_data.get("correlation_id") == correlation_id:
                    return resp_data
        raise TimeoutError(f"Event-driven initialization timed out for bank {bank_id}")

    def train(
        self,
        bank_id: str,
        weights: ModelWeights,
        learning_rate: float,
        batch_size: int,
        epochs: int,
        enable_dp: bool,
        dp_epsilon: float,
        dp_delta: float,
        dp_max_grad_norm: float,
        correlation_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Trigger event-driven bank local training."""
        schema_weights = {
            "layer_shapes": [list(shape) for shape in weights.layer_shapes],
            "flat_weights": weights.flat_weights,
        }
        payload = {
            "weights": schema_weights,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "epochs": epochs,
            "enable_dp": enable_dp,
            "dp_epsilon": dp_epsilon,
            "dp_delta": dp_delta,
            "dp_max_grad_norm": dp_max_grad_norm,
            "correlation_id": correlation_id,
            "fedprox_mu": kwargs.get("fedprox_mu", 0.0),
            "moon_mu": kwargs.get("moon_mu", 0.0),
            "moon_temperature": kwargs.get("moon_temperature", 0.5),
        }
        prev_local_weights = kwargs.get("prev_local_weights")
        if prev_local_weights:
            payload["prev_local_weights"] = {
                "layer_shapes": [list(shape) for shape in prev_local_weights.layer_shapes],
                "flat_weights": prev_local_weights.flat_weights,
            }
        self.redis_client.publish(f"bank_client_{bank_id}_train", json.dumps(payload))

        start_time = time.perf_counter()
        while (time.perf_counter() - start_time) < 120.0:
            msg = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if msg and msg["channel"] == f"bank_client_{bank_id}_train_response":
                resp_data = json.loads(msg["data"])
                if resp_data.get("correlation_id") == correlation_id:
                    return resp_data
        raise TimeoutError(f"Event-driven training timed out for bank {bank_id}")

    def evaluate(
        self,
        bank_id: str,
        weights: ModelWeights,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Trigger event-driven bank model evaluation."""
        schema_weights = {
            "layer_shapes": [list(shape) for shape in weights.layer_shapes],
            "flat_weights": weights.flat_weights,
        }
        payload = {
            "weights": schema_weights,
            "correlation_id": correlation_id,
        }
        self.redis_client.publish(f"bank_client_{bank_id}_evaluate", json.dumps(payload))

        start_time = time.perf_counter()
        while (time.perf_counter() - start_time) < 60.0:
            msg = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if msg and msg["channel"] == f"bank_client_{bank_id}_evaluate_response":
                resp_data = json.loads(msg["data"])
                if resp_data.get("correlation_id") == correlation_id:
                    return resp_data
        raise TimeoutError(f"Event-driven evaluation timed out for bank {bank_id}")
