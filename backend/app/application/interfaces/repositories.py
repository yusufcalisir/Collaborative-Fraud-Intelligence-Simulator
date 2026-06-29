"""Repository interface contracts.

Abstract base classes that define how the application layer talks to
the persistence layer. Concrete implementations live in infrastructure/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities import SimulationRun, TrainingRound


class SimulationRepositoryInterface(ABC):
    """Persistence contract for simulation runs."""

    @abstractmethod
    async def create(self, simulation: SimulationRun) -> SimulationRun:
        ...

    @abstractmethod
    async def get_by_id(self, simulation_id: str) -> SimulationRun | None:
        ...

    @abstractmethod
    async def list_all(self, limit: int = 20, offset: int = 0) -> list[SimulationRun]:
        ...

    @abstractmethod
    async def update(self, simulation: SimulationRun) -> SimulationRun:
        ...

    @abstractmethod
    async def delete(self, simulation_id: str) -> bool:
        ...


class TrainingRoundRepositoryInterface(ABC):
    """Persistence contract for training rounds."""

    @abstractmethod
    async def create(self, training_round: TrainingRound) -> TrainingRound:
        ...

    @abstractmethod
    async def get_by_simulation(self, simulation_id: str) -> list[TrainingRound]:
        ...

    @abstractmethod
    async def get_round(self, simulation_id: str, round_number: int) -> TrainingRound | None:
        ...
