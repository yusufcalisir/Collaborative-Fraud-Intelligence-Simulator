"""Federated Learning engine.

Implements FedAvg aggregation with support for:
- Weighted averaging proportional to dataset size
- Network latency simulation
- Client dropout and reconnection
- Secure aggregation simulation (simplified)

This is a custom simulation engine, not the Flower (flwr) framework.
See docs/engineering-decisions.md for the rationale. In short: Flower is
designed for real distributed deployments over gRPC. For a single-machine
simulation where we need fine-grained control over failure injection and
real-time observability through a web UI, a custom engine is simpler
and more transparent.
"""

from __future__ import annotations

import asyncio
import logging
import time
from copy import deepcopy
from typing import TYPE_CHECKING

import numpy as np

from app.domain.enums import AggregationMethod, ClientStatus
from app.domain.value_objects import ModelWeights, RoundMetrics

if TYPE_CHECKING:
    from app.application.services.model_service import ModelService
    from app.application.services.privacy_service import PrivacyService
    from app.config import Settings

logger = logging.getLogger(__name__)


class FederatedLearningEngine:
    """Orchestrates the federated training loop.

    Responsible for:
    1. Distributing global model parameters to clients
    2. Collecting locally-trained parameters
    3. Aggregating parameters (FedAvg)
    4. Simulating network conditions (latency, dropout)
    5. Applying privacy mechanisms before aggregation
    """

    def __init__(
        self,
        settings: Settings,
        model_service: ModelService,
        privacy_service: PrivacyService,
    ) -> None:
        self.settings = settings
        self.model_service = model_service
        self.privacy_service = privacy_service

    def aggregate_parameters(
        self,
        client_weights: list[ModelWeights],
        client_samples: list[int],
        method: AggregationMethod = AggregationMethod.FED_AVG_WEIGHTED,
    ) -> ModelWeights:
        """Aggregate model parameters from multiple clients.

        FedAvg: weighted average of parameters proportional to local dataset size.
        This is the same algorithm used by McMahan et al. (2017) and implemented
        in Flower's FedAvg strategy.

        Args:
            client_weights: Parameter sets from each participating client.
            client_samples: Number of training samples at each client.
            method: Aggregation strategy.

        Returns:
            Aggregated global model parameters.
        """
        if not client_weights:
            raise ValueError("Cannot aggregate empty parameter list")

        if len(client_weights) == 1:
            return client_weights[0]

        start_time = time.perf_counter()

        if method == AggregationMethod.FED_AVG:
            # Unweighted average
            weights_array = np.array([w.flat_weights for w in client_weights])
            avg_weights = weights_array.mean(axis=0).tolist()

        elif method == AggregationMethod.FED_AVG_WEIGHTED:
            # Weighted average by dataset size
            total_samples = sum(client_samples)
            proportions = [s / total_samples for s in client_samples]

            avg_weights = np.zeros(len(client_weights[0].flat_weights))
            for w, proportion in zip(client_weights, proportions):
                avg_weights += np.array(w.flat_weights) * proportion
            avg_weights = avg_weights.tolist()

        else:
            raise ValueError(f"Unsupported aggregation method: {method}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Aggregated %d client models in %.1fms (method=%s)",
            len(client_weights), elapsed_ms, method,
        )

        return ModelWeights(
            layer_shapes=client_weights[0].layer_shapes,
            flat_weights=avg_weights,
        )

    def simulate_client_availability(
        self,
        bank_ids: list[str],
        dropout_probability: float = 0.2,
        previously_dropped: set[str] | None = None,
        enable_reconnect: bool = True,
        rng: np.random.Generator | None = None,
    ) -> dict[str, ClientStatus]:
        """Determine which clients participate in this round.

        Simulates realistic network conditions where clients may:
        - Drop out (network failure, maintenance window)
        - Reconnect after being offline in a previous round
        - Remain offline for multiple rounds

        Args:
            bank_ids: All registered bank IDs.
            dropout_probability: Chance of any client dropping out.
            previously_dropped: Banks that were offline last round.
            enable_reconnect: Whether dropped clients can rejoin.
            rng: Random number generator for reproducibility.
        """
        if rng is None:
            rng = np.random.default_rng()

        previously_dropped = previously_dropped or set()
        statuses: dict[str, ClientStatus] = {}

        for bank_id in bank_ids:
            was_dropped = bank_id in previously_dropped

            if was_dropped and enable_reconnect:
                # 70% chance of reconnecting after being dropped
                if rng.random() < 0.7:
                    statuses[bank_id] = ClientStatus.RECONNECTED
                    logger.info("Bank %s reconnected", bank_id)
                else:
                    statuses[bank_id] = ClientStatus.OFFLINE
                    logger.info("Bank %s remains offline", bank_id)
            elif rng.random() < dropout_probability:
                statuses[bank_id] = ClientStatus.DROPPED
                logger.info("Bank %s dropped out this round", bank_id)
            else:
                statuses[bank_id] = ClientStatus.ACTIVE

        return statuses

    async def simulate_network_latency(
        self,
        bank_id: str,
        latency_range_ms: tuple[int, int] = (50, 500),
        rng: np.random.Generator | None = None,
    ) -> float:
        """Simulate variable network delay for a client.

        Returns the simulated latency in milliseconds.
        """
        if rng is None:
            rng = np.random.default_rng()

        min_ms, max_ms = latency_range_ms
        latency_ms = float(rng.integers(min_ms, max_ms))

        await asyncio.sleep(latency_ms / 1000.0)
        logger.debug("Simulated %.0fms latency for %s", latency_ms, bank_id)

        return latency_ms

    def apply_secure_aggregation_masks(
        self,
        client_weights: list[ModelWeights],
        rng: np.random.Generator | None = None,
    ) -> list[ModelWeights]:
        """Simulate secure aggregation by applying pairwise masks.

        In real secure aggregation (Bonawitz et al., 2017), each pair of
        clients agrees on a random mask that cancels out during summation.
        Client i adds mask_ij and client j subtracts mask_ij, so the
        aggregator never sees raw parameters.

        This is a simplified demonstration: we add random masks that
        sum to zero across all clients. The aggregated result is identical
        to plaintext FedAvg, but individual client parameters are obscured.

        Limitations (documented in threat-model.md):
        - No key exchange protocol
        - Masks are generated centrally (defeats the purpose in production)
        - No dropout recovery (real protocols handle this with Shamir secret sharing)
        """
        if rng is None:
            rng = np.random.default_rng()

        n_clients = len(client_weights)
        n_params = len(client_weights[0].flat_weights)

        # Generate masks that sum to zero
        masks = rng.standard_normal((n_clients, n_params))
        masks[-1] = -masks[:-1].sum(axis=0)  # Last mask ensures sum = 0

        masked_weights = []
        for w, mask in zip(client_weights, masks):
            masked = [fw + m for fw, m in zip(w.flat_weights, mask)]
            masked_weights.append(ModelWeights(
                layer_shapes=w.layer_shapes,
                flat_weights=masked,
            ))

        logger.info("Applied secure aggregation masks to %d clients", n_clients)
        return masked_weights
