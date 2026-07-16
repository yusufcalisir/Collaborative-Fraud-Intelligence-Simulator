"""Federated Learning engine.

Implements multiple aggregation strategies with support for:
- FedAvg: weighted/unweighted averaging (McMahan et al., 2017)
- Krum: Byzantine-robust selection (Blanchard et al., 2017)
- Coordinate-wise Median: element-wise median aggregation
- Network latency simulation
- Client dropout and reconnection
- Secure aggregation simulation (simplified)
- Model poisoning simulation for adversarial robustness testing

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
from typing import TYPE_CHECKING

import numpy as np

from app.domain.enums import AggregationMethod, ClientStatus
from app.domain.value_objects import ModelWeights

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
    3. Aggregating parameters (FedAvg, Krum, or Coordinate-wise Median)
    4. Simulating network conditions (latency, dropout)
    5. Applying privacy mechanisms before aggregation
    6. Simulating adversarial model poisoning attacks
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
        # Server optimizer states for FedOpt (FedAdam / FedAdaGrad) keyed by simulation_id
        self._server_m_by_sim: dict[str, np.ndarray] = {}
        self._server_v_by_sim: dict[str, np.ndarray] = {}

    def aggregate_parameters(
        self,
        client_weights: list[ModelWeights],
        client_samples: list[int],
        method: AggregationMethod = AggregationMethod.FED_AVG_WEIGHTED,
        global_weights: ModelWeights | None = None,
        simulation_id: str | None = None,
    ) -> ModelWeights:
        """Aggregate model parameters from multiple clients.

        Supports multiple strategies:
        - FedAvg / FedAvg Weighted: standard averaging (McMahan et al., 2017)
        - Krum: selects the single client closest to all others (Blanchard et al., 2017)
        - Coordinate-wise Median: element-wise median across clients
        - FedAdam / FedAdaGrad: adaptive server optimizers (FedOpt framework)

        Args:
            client_weights: Parameter sets from each participating client.
            client_samples: Number of training samples at each client.
            method: Aggregation strategy.
            global_weights: Global weights before this round (required for FedOpt).
            simulation_id: Unique simulation run identifier to persist server states.

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
            for w, proportion in zip(client_weights, proportions, strict=False):
                avg_weights += np.array(w.flat_weights) * proportion
            avg_weights = avg_weights.tolist()

        elif method in (AggregationMethod.FED_ADAM, AggregationMethod.FED_ADAGRAD):
            # Calculate standard weighted FedAvg first to get the averaged updates
            total_samples = sum(client_samples)
            proportions = [s / total_samples for s in client_samples]
            w_avg = np.zeros(len(client_weights[0].flat_weights))
            for w, proportion in zip(client_weights, proportions, strict=False):
                w_avg += np.array(w.flat_weights) * proportion

            if global_weights is None:
                # Round 0 fallback to standard FedAvg
                avg_weights = w_avg.tolist()
            else:
                w_t = np.array(global_weights.flat_weights)
                delta_t = w_avg - w_t  # pseudo-gradient

                sim_id = simulation_id or "default_sim"
                if sim_id not in self._server_m_by_sim:
                    self._server_m_by_sim[sim_id] = np.zeros_like(w_avg)
                if sim_id not in self._server_v_by_sim:
                    self._server_v_by_sim[sim_id] = np.zeros_like(w_avg)

                m_t = self._server_m_by_sim[sim_id]
                v_t = self._server_v_by_sim[sim_id]

                eta = self.settings.fedopt_server_lr
                beta1 = self.settings.fedopt_beta1
                beta2 = self.settings.fedopt_beta2
                tau = self.settings.fedopt_tau

                if method == AggregationMethod.FED_ADAM:
                    # Update moments
                    m_t_next = beta1 * m_t + (1 - beta1) * delta_t
                    v_t_next = beta2 * v_t + (1 - beta2) * (delta_t**2)
                    # Update global weights
                    w_next = w_t + eta * m_t_next / (np.sqrt(v_t_next) + tau)

                    self._server_m_by_sim[sim_id] = m_t_next
                    self._server_v_by_sim[sim_id] = v_t_next
                else:  # FED_ADAGRAD
                    v_t_next = v_t + (delta_t**2)
                    w_next = w_t + eta * delta_t / (np.sqrt(v_t_next) + tau)

                    self._server_v_by_sim[sim_id] = v_t_next

                avg_weights = w_next.tolist()

        elif method == AggregationMethod.KRUM:
            # Krum (Blanchard et al., 2017): Select the client whose
            # parameters are closest to the most other clients.
            # For each client i, compute the sum of squared distances
            # to the (n - f - 2) closest other clients, where f is the
            # number of assumed Byzantine workers. Here f = 1.
            weights_array = np.array([w.flat_weights for w in client_weights])
            n = len(weights_array)
            f = 1  # assume at most 1 Byzantine client
            num_closest = max(1, n - f - 2)

            scores = []
            for i in range(n):
                dists = []
                for j in range(n):
                    if i != j:
                        dist = float(np.sum((weights_array[i] - weights_array[j]) ** 2))
                        dists.append(dist)
                dists.sort()
                scores.append(sum(dists[:num_closest]))

            best_idx = int(np.argmin(scores))
            avg_weights = weights_array[best_idx].tolist()
            logger.info("Krum selected client %d as representative", best_idx)

        elif method == AggregationMethod.COORDINATE_WISE_MEDIAN:
            # Coordinate-wise Median: for each parameter index, take the
            # median value across all clients. Robust to outlier parameters
            # injected by a Byzantine client.
            weights_array = np.array([w.flat_weights for w in client_weights])
            avg_weights = np.median(weights_array, axis=0).tolist()

        else:
            raise ValueError(f"Unsupported aggregation method: {method}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Aggregated %d client models in %.1fms (method=%s)",
            len(client_weights),
            elapsed_ms,
            method,
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
        client_samples: list[int] | None = None,
        rng: np.random.Generator | None = None,
    ) -> list[ModelWeights]:
        """Simulate secure aggregation by applying pairwise masks.

        In real secure aggregation (Bonawitz et al., 2017), each pair of
        clients agrees on a random mask that cancels out during summation.
        Client i adds mask_ij and client j subtracts mask_ij, so the
        aggregator never sees raw parameters.

        This is a simplified demonstration: we add random masks that
        sum to zero across all clients (weighted or unweighted based on config).
        The aggregated result is identical to plaintext FedAvg, but individual
        client parameters are obscured.

        Limitations (documented in docs/threat-model.md or docs/):
        - No key exchange protocol
        - Masks are generated centrally (defeats the purpose in production)
        - No dropout recovery (real protocols handle this with Shamir secret sharing)
        """
        if rng is None:
            rng = np.random.default_rng()

        n_clients = len(client_weights)
        n_params = len(client_weights[0].flat_weights)

        # Generate random masks
        masks = rng.standard_normal((n_clients, n_params))

        if client_samples is not None and len(client_samples) == n_clients:
            total_samples = sum(client_samples)
            if total_samples > 0:
                proportions = [s / total_samples for s in client_samples]
                p_n = proportions[-1]
                if p_n > 0:
                    # Weighted: sum_{i=1}^n p_i * m_i = 0 => m_n = - (sum_{i=1}^{n-1} p_i * m_i) / p_n
                    weighted_sum_prev = np.zeros(n_params)
                    for i in range(n_clients - 1):
                        weighted_sum_prev += proportions[i] * masks[i]
                    masks[-1] = -weighted_sum_prev / p_n
                else:
                    masks[-1] = -masks[:-1].sum(axis=0)
            else:
                masks[-1] = -masks[:-1].sum(axis=0)
        else:
            # Unweighted: sum_{i=1}^n m_i = 0
            masks[-1] = -masks[:-1].sum(axis=0)

        masked_weights = []
        for w, mask in zip(client_weights, masks, strict=False):
            masked = [fw + m for fw, m in zip(w.flat_weights, mask, strict=False)]
            masked_weights.append(
                ModelWeights(
                    layer_shapes=w.layer_shapes,
                    flat_weights=masked,
                )
            )

        logger.info("Applied secure aggregation masks to %d clients", n_clients)
        return masked_weights

    def apply_model_poisoning(
        self,
        honest_weights: ModelWeights,
        scale: float = 5.0,
        rng: np.random.Generator | None = None,
    ) -> ModelWeights:
        """Simulate a model poisoning attack by corrupting model weights.

        Replaces the honest local model weights with random noise scaled
        by ``scale``. This emulates a Byzantine client that either:
        - Sends random garbage to degrade the global model, or
        - Sends carefully crafted updates to introduce a backdoor.

        For this simulator we use the simpler random-noise approach,
        which is sufficient to demonstrate Krum/Median defences.

        Args:
            honest_weights: The correctly-trained local weights to corrupt.
            scale: Multiplier on the random noise magnitude.
            rng: Random generator for reproducibility.

        Returns:
            Poisoned ModelWeights with the same shape metadata.
        """
        if rng is None:
            rng = np.random.default_rng()

        honest_arr = np.array(honest_weights.flat_weights)
        # Generate noise with same magnitude as the honest weights,
        # scaled up by the poisoning factor. If std is zero (e.g. constant weights),
        # fallback to 1.0.
        std_val = float(np.std(honest_arr))
        if std_val == 0.0:
            std_val = 1.0
        noise = rng.standard_normal(len(honest_arr)) * std_val * scale
        poisoned = (honest_arr + noise).tolist()

        logger.warning(
            "Applied model poisoning (scale=%.1f) — %d parameters corrupted",
            scale,
            len(poisoned),
        )

        return ModelWeights(
            layer_shapes=honest_weights.layer_shapes,
            flat_weights=poisoned,
        )

    def apply_byzantine_defense(
        self,
        client_weights: list[ModelWeights],
        defense_type: str = "krum",
    ) -> list[ModelWeights]:
        """Filter client weight updates using a Byzantine-robust defense strategy.

        Supported defense types:
        - ``krum``: Keep only the single update closest to the cluster of honest clients.
        - ``coordinate_wise_median``: Return a synthetic weight equal to the
          element-wise median — already handled by the aggregation step, so this
          path returns the full list unchanged to let aggregation do the work.
        - Any other value: no filtering, all weights returned.

        Args:
            client_weights: Raw update list potentially containing poisoned entries.
            defense_type: Name of the defense algorithm to apply.

        Returns:
            A filtered (or unchanged) list of ModelWeights.
        """
        if len(client_weights) <= 1:
            return client_weights

        if defense_type == "krum":
            # Select the single update with the smallest sum of distances to
            # its (n - f - 2) nearest neighbours, where f = 1 assumed Byzantine.
            weights_array = np.array([w.flat_weights for w in client_weights])
            n = len(weights_array)
            f = 1
            num_closest = max(1, n - f - 2)

            scores = []
            for i in range(n):
                dists = sorted(
                    float(np.sum((weights_array[i] - weights_array[j]) ** 2))
                    for j in range(n)
                    if i != j
                )
                scores.append(sum(dists[:num_closest]))

            best_idx = int(np.argmin(scores))
            logger.info("Byzantine defense (krum): selected client %d as representative", best_idx)
            return [client_weights[best_idx]]

        # coordinate_wise_median and any unknown defense: return all weights
        # unchanged — the aggregation method will apply robustness if configured.
        return client_weights

    def aggregate_graph_parameters(
        self,
        client_weights: list[ModelWeights],
        client_samples: list[int],
        method: AggregationMethod = AggregationMethod.FED_AVG_WEIGHTED,
    ) -> ModelWeights:
        """Aggregate GraphSAGE model parameters from multiple clients.

        This is a thin wrapper around aggregate_parameters() that adds
        GNN-specific validation before delegating to the standard
        aggregation logic. The same FedAvg/Krum/Median strategies apply.

        Validates:
        - All clients have the same number of layers (layer_shapes match)
        - Parameter counts are identical across clients

        Args:
            client_weights: GNN parameter sets from each participating bank.
            client_samples: Number of graph nodes at each bank.
            method: Aggregation strategy (same as MLP aggregation).

        Returns:
            Aggregated global GNN model parameters.
        """
        if not client_weights:
            raise ValueError("Cannot aggregate empty GNN parameter list")

        # Validate layer shape consistency across clients
        reference_shapes = client_weights[0].layer_shapes
        reference_params = client_weights[0].num_parameters

        for i, w in enumerate(client_weights[1:], 1):
            if w.layer_shapes != reference_shapes:
                raise ValueError(
                    f"GNN layer shape mismatch: client 0 has {reference_shapes}, "
                    f"client {i} has {w.layer_shapes}"
                )
            if w.num_parameters != reference_params:
                raise ValueError(
                    f"GNN parameter count mismatch: client 0 has {reference_params}, "
                    f"client {i} has {w.num_parameters}"
                )

        logger.info(
            "Aggregating GNN parameters from %d clients (%d params each, method=%s)",
            len(client_weights),
            reference_params,
            method,
        )

        # Fallback to unweighted FED_AVG if all clients have 0 samples (e.g. empty graphs in testing)
        if sum(client_samples) == 0 and method == AggregationMethod.FED_AVG_WEIGHTED:
            logger.warning("All clients have 0 GNN samples. Falling back to unweighted FED_AVG.")
            method = AggregationMethod.FED_AVG

        # Delegate to the standard aggregation logic
        return self.aggregate_parameters(client_weights, client_samples, method)
