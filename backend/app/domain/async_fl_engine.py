"""Domain-level Asynchronous Federated Learning Engine (FedAsync).

Allows fast bank nodes to contribute parameter updates asynchronously without blocking
on slower straggler nodes. Down-weights older updates using staleness attenuation S(tau).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np  # noqa: TC002

logger = logging.getLogger(__name__)


def staleness_attenuation(tau: int, alpha: float = 0.5) -> float:
    """Computes staleness attenuation factor S(tau) = (1 + tau)^(-alpha).

    tau = current_round - update_submitted_round
    """
    if tau <= 0:
        return 1.0
    return float((1.0 + float(tau)) ** (-alpha))


@dataclass
class AsynchronousUpdateRecord:
    """Record of an asynchronous model parameter update submitted by a bank node."""

    node_id: str
    submitted_round: int
    staleness_tau: int
    weights: dict[str, np.ndarray]
    sample_count: int


@dataclass
class AsyncFLEngine:
    """FedAsync engine executing asynchronous global model updates with staleness attenuation."""

    current_round: int = 1
    alpha_staleness: float = 0.5
    learning_rate: float = 0.8
    global_weights: dict[str, np.ndarray] = field(default_factory=dict)

    def set_global_weights(self, weights: dict[str, np.ndarray]) -> None:
        """Sets the baseline global model weights."""
        self.global_weights = {layer: arr.copy() for layer, arr in weights.items()}

    def apply_async_update(
        self,
        node_id: str,
        submitted_round: int,
        client_weights: dict[str, np.ndarray],
        sample_count: int = 100,
    ) -> dict[str, np.ndarray]:
        """Applies an asynchronous parameter update from a bank node.

        Calculates staleness tau = current_round - submitted_round,
        computes attenuation factor S(tau), and updates global weights:
          W^(t+1) = (1 - alpha_tau) * W^(t) + alpha_tau * W_client
        """
        if not self.global_weights:
            self.set_global_weights(client_weights)
            return self.global_weights

        tau = max(0, self.current_round - submitted_round)
        s_tau = staleness_attenuation(tau, alpha=self.alpha_staleness)
        effective_alpha = round(self.learning_rate * s_tau, 4)

        logger.info(
            "Async update from node %s (round %d, tau=%d, s(tau)=%.4f, eff_alpha=%.4f)",
            node_id,
            submitted_round,
            tau,
            s_tau,
            effective_alpha,
        )

        new_global: dict[str, np.ndarray] = {}
        for layer, current_arr in self.global_weights.items():
            if layer in client_weights:
                client_arr = client_weights[layer]
                new_global[layer] = (
                    1.0 - effective_alpha
                ) * current_arr + effective_alpha * client_arr
            else:
                new_global[layer] = current_arr

        self.global_weights = new_global
        return self.global_weights
