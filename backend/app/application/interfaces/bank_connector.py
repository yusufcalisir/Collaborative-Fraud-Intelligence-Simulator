"""Bank Connector Interface Port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.value_objects import ModelWeights


class BankConnectorInterface(ABC):
    """Abstract port interface decoupling federated learning platform from bank integrations."""

    @abstractmethod
    def initialize(
        self,
        bank_id: str,
        num_transactions: int,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Initialize local dataset partition for client bank."""
        pass

    @abstractmethod
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
    ) -> dict[str, Any]:
        """Perform local training on bank client node and return updated weights."""
        pass

    @abstractmethod
    def evaluate(
        self,
        bank_id: str,
        weights: ModelWeights,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Perform evaluation of global model on bank test partition and return metrics."""
        pass
