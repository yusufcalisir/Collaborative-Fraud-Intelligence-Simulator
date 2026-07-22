"""Production-grade RabbitMQ / AMQP Bank Connector.

Implements the BankConnectorInterface, publishing training and evaluation tasks
to client queues and waiting for replies with correlation IDs.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any

try:
    import pika
except ImportError:
    pika = None

from app.application.interfaces.bank_connector import BankConnectorInterface

if TYPE_CHECKING:
    from app.domain.value_objects import ModelWeights

logger = logging.getLogger(__name__)


class RabbitMQBankConnector(BankConnectorInterface):
    """Sends FL commands to bank nodes over AMQP/RabbitMQ."""

    credentials: Any | None = None
    connection_params: Any | None = None

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
        queue_prefix: str = "fl.queue",
        fallback_connector: BankConnectorInterface | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.queue_prefix = queue_prefix
        self.fallback_connector = fallback_connector
        if pika is not None:
            self.credentials = pika.PlainCredentials(self.username, self.password)
            self.connection_params = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=self.credentials,
                connection_attempts=3,
                retry_delay=2,
            )
        else:
            self.credentials = None
            self.connection_params = None

    def _get_connection(self) -> Any | None:
        """Establish blocking connection to RabbitMQ with clean fallback."""
        if pika is None:
            return None
        try:
            return pika.BlockingConnection(self.connection_params)
        except Exception as exc:
            logger.warning(
                "RabbitMQ connection failed at %s:%d: %s. Fallback option will be checked.",
                self.host,
                self.port,
                exc,
            )
            return None

    def _publish_and_await(
        self,
        routing_key: str,
        payload: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Publish a payload to a queue and wait for the response on an exclusive reply queue."""
        connection = self._get_connection()
        if connection is None:
            if self.fallback_connector:
                logger.info("Falling back to fallback connector execution.")
                # We need to extract method from routing key
                if "init" in routing_key:
                    return self.fallback_connector.initialize(
                        bank_id=payload.get("bank_id", "unknown"),
                        num_transactions=payload.get("num_transactions", 1000),
                        seed=payload.get("seed", 42),
                    )
                elif "train" in routing_key:
                    from app.domain.value_objects import ModelWeights

                    weights_data = payload.get("weights", {})
                    weights = ModelWeights(
                        layer_shapes=[
                            tuple(shape) for shape in weights_data.get("layer_shapes", [])
                        ],
                        flat_weights=weights_data.get("flat_weights", []),
                    )
                    return self.fallback_connector.train(
                        bank_id=payload.get("bank_id", "unknown"),
                        weights=weights,
                        learning_rate=payload.get("learning_rate", 0.001),
                        batch_size=payload.get("batch_size", 64),
                        epochs=payload.get("epochs", 3),
                        enable_dp=payload.get("enable_dp", False),
                        dp_epsilon=payload.get("dp_epsilon", 1.0),
                        dp_delta=payload.get("dp_delta", 1e-5),
                        dp_max_grad_norm=payload.get("dp_max_grad_norm", 1.0),
                        correlation_id=payload.get("correlation_id", "cid"),
                        **payload,
                    )
                elif "evaluate" in routing_key:
                    from app.domain.value_objects import ModelWeights

                    weights_data = payload.get("weights", {})
                    weights = ModelWeights(
                        layer_shapes=[
                            tuple(shape) for shape in weights_data.get("layer_shapes", [])
                        ],
                        flat_weights=weights_data.get("flat_weights", []),
                    )
                    return self.fallback_connector.evaluate(
                        bank_id=payload.get("bank_id", "unknown"),
                        weights=weights,
                        correlation_id=payload.get("correlation_id", "cid"),
                    )
            raise RuntimeError(
                f"RabbitMQ broker unavailable and no fallback connector configured for routing key: {routing_key}"
            )

        channel = connection.channel()
        try:
            # Declare destination queue
            dest_queue = f"{self.queue_prefix}.{routing_key}"
            channel.queue_declare(queue=dest_queue, durable=True)

            # Declare callback queue
            result = channel.queue_declare(queue="", exclusive=True)
            callback_queue = result.method.queue

            corr_id = payload.get("correlation_id") or str(uuid.uuid4())
            response_payload: dict[str, Any] | None = None

            def on_response(ch: Any, method: Any, props: Any, body: bytes) -> None:
                nonlocal response_payload
                if props.correlation_id == corr_id:
                    try:
                        response_payload = json.loads(body.decode("utf-8"))
                    except Exception as err:
                        logger.error("Failed to decode AMQP response body: %s", err)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    ch.stop_consuming()

            channel.basic_consume(
                queue=callback_queue,
                on_message_callback=on_response,
                auto_ack=False,
            )

            # Publish message
            assert pika is not None
            properties = pika.BasicProperties(
                reply_to=callback_queue,
                correlation_id=corr_id,
                content_type="application/json",
                delivery_mode=2,  # persistent
            )
            channel.basic_publish(
                exchange="",
                routing_key=dest_queue,
                body=json.dumps(payload).encode("utf-8"),
                properties=properties,
            )

            # Wait with simple timeout mechanism
            # Since BlockingConnection.process_data_events blocks, we run in a loop with check
            connection.process_data_events(time_limit=timeout)
            if response_payload is None:
                raise TimeoutError(
                    f"Timed out waiting for response from bank node queue {dest_queue}"
                )

            return response_payload
        finally:
            if connection.is_open:
                connection.close()

    def initialize(
        self,
        bank_id: str,
        num_transactions: int,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Trigger initialization over AMQP queue."""
        payload = {
            "bank_id": bank_id,
            "num_transactions": num_transactions,
            "seed": seed,
            "correlation_id": f"init_{bank_id}_{uuid.uuid4().hex[:8]}",
        }
        return self._publish_and_await(
            routing_key=f"{bank_id}.init",
            payload=payload,
        )

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
        """Trigger training over AMQP queue."""
        schema_weights = {
            "layer_shapes": [list(shape) for shape in weights.layer_shapes],
            "flat_weights": weights.flat_weights,
        }
        payload = {
            "bank_id": bank_id,
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
        return self._publish_and_await(
            routing_key=f"{bank_id}.train",
            payload=payload,
        )

    def evaluate(
        self,
        bank_id: str,
        weights: ModelWeights,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Trigger evaluation over AMQP queue."""
        schema_weights = {
            "layer_shapes": [list(shape) for shape in weights.layer_shapes],
            "flat_weights": weights.flat_weights,
        }
        payload = {
            "bank_id": bank_id,
            "weights": schema_weights,
            "correlation_id": correlation_id,
        }
        return self._publish_and_await(
            routing_key=f"{bank_id}.evaluate",
            payload=payload,
        )
