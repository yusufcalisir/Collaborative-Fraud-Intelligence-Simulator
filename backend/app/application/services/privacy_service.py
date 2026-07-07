"""Privacy-enhancing mechanisms for federated learning.

Implements:
1. Differential Privacy (DP) — adds calibrated noise to model updates
2. Privacy budget tracking — monitors cumulative epsilon across rounds

This is a simplified, educational implementation. Production DP would use
libraries like Opacus (PyTorch) or TensorFlow Privacy, which handle
per-sample gradient clipping and noise calibration more rigorously.

See docs/threat-model.md for an honest assessment of what this protects
against and what it doesn't.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from app.domain.value_objects import ModelWeights

logger = logging.getLogger(__name__)


@dataclass
class PrivacyBudget:
    """Tracks cumulative privacy expenditure across rounds.

    Uses simple composition: total epsilon grows linearly with rounds.
    Advanced composition (Moments Accountant / Rényi DP) would give
    tighter bounds but is beyond the scope of this simulator.
    """

    epsilon_per_round: float = 1.0
    delta: float = 1e-5
    rounds_spent: int = 0
    _epsilon_history: list[float] = field(default_factory=list)

    @property
    def total_epsilon(self) -> float:
        """Cumulative privacy loss."""
        return sum(self._epsilon_history)

    @property
    def total_delta(self) -> float:
        """Cumulative delta under basic composition."""
        return self.delta * self.rounds_spent

    def spend(self, epsilon: float) -> None:
        """Record privacy expenditure for one round."""
        self.rounds_spent += 1
        self._epsilon_history.append(epsilon)

    @property
    def history(self) -> list[float]:
        return list(self._epsilon_history)


class PrivacyService:
    """Applies differential privacy mechanisms to model updates.

    Gaussian mechanism: adds noise ~ N(0, σ²) to each parameter,
    where σ is calibrated to the sensitivity and desired ε, δ.
    """

    def __init__(self) -> None:
        self._budgets: dict[str, PrivacyBudget] = {}

    def get_or_create_budget(
        self,
        simulation_id: str,
        epsilon: float = 1.0,
        delta: float = 1e-5,
    ) -> PrivacyBudget:
        """Get or initialize a privacy budget for a simulation."""
        if simulation_id not in self._budgets:
            self._budgets[simulation_id] = PrivacyBudget(
                epsilon_per_round=epsilon,
                delta=delta,
            )
        return self._budgets[simulation_id]

    def add_noise_to_weights(
        self,
        weights: ModelWeights,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        max_grad_norm: float = 1.0,
        sensitivity: float | None = None,
        rng: np.random.Generator | None = None,
    ) -> ModelWeights:
        """Apply Gaussian mechanism to model parameters.

        The noise scale σ is computed as:
            σ = sensitivity * sqrt(2 * ln(1.25/δ)) / ε

        where sensitivity = max_grad_norm (L2 sensitivity of the query).

        Lower epsilon → more noise → stronger privacy → lower utility.
        This is the fundamental privacy-utility tradeoff.

        Args:
            weights: Original model parameters.
            epsilon: Privacy parameter. Lower = more private.
            delta: Probability of privacy breach.
            max_grad_norm: Clipping bound for gradient sensitivity.
            sensitivity: Override for sensitivity calculation.
            rng: Random number generator.

        Returns:
            Noised model parameters.
        """
        if rng is None:
            rng = np.random.default_rng()

        if sensitivity is None:
            sensitivity = max_grad_norm

        # Gaussian mechanism noise scale
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon

        noise = rng.normal(0, sigma, len(weights.flat_weights))
        noised_weights = [w + n for w, n in zip(weights.flat_weights, noise, strict=False)]

        logger.info(
            "Applied DP noise: ε=%.2f, δ=%.1e, σ=%.4f, params=%d",
            epsilon,
            delta,
            sigma,
            len(weights.flat_weights),
        )

        return ModelWeights(
            layer_shapes=weights.layer_shapes,
            flat_weights=noised_weights,
        )

    def clip_model_update(
        self,
        original_weights: ModelWeights,
        updated_weights: ModelWeights,
        max_norm: float = 1.0,
    ) -> ModelWeights:
        """Clip the model update (delta) to bound sensitivity.

        In DP-FL, we clip the difference between the local update and
        the global model, not the parameters themselves. This bounds
        the contribution of any single client's data.
        """
        delta_w = np.array(updated_weights.flat_weights) - np.array(original_weights.flat_weights)
        norm = np.linalg.norm(delta_w)

        if norm > max_norm:
            delta_w = delta_w * (max_norm / norm)
            logger.debug("Clipped model update: norm %.4f → %.4f", norm, max_norm)

        clipped = np.array(original_weights.flat_weights) + delta_w

        return ModelWeights(
            layer_shapes=updated_weights.layer_shapes,
            flat_weights=clipped.tolist(),
        )

    def record_opacus_epsilon(self, simulation_id: str, epsilon: float) -> None:
        """Record the actual privacy budget spent in Opacus mode for a round.

        Since Opacus computes the total Rényi Differential Privacy (RDP)
        epsilon across multiple steps using composition, we directly record the
        resulting epsilon computed by the PrivacyEngine.
        """
        budget = self.get_or_create_budget(simulation_id)
        budget.spend(epsilon)
        logger.info(
            "Recorded Opacus DP spend for simulation %s: round_epsilon=%.4f, total_spent_epsilon=%.4f",
            simulation_id,
            epsilon,
            budget.total_epsilon,
        )

    def clear_budget(self, simulation_id: str) -> None:
        """Remove privacy budget for a completed simulation."""
        self._budgets.pop(simulation_id, None)
