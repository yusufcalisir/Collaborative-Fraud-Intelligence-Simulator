# ruff: noqa: N818
"""Consortium Policy Engine and Pre-Round Enforcement Rules."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.consortium_governance import Consortium

logger = logging.getLogger(__name__)


class ConsortiumPolicyViolation(Exception):
    """Exception raised when a federated learning round violates consortium policies."""

    pass


@dataclass
class ConsortiumPolicyConfig:
    """Policy configuration limits for a consortium."""

    min_active_members: int = 2
    max_epsilon_budget: float = 5.0
    require_mtls: bool = True
    allowed_architectures: list[str] = field(
        default_factory=lambda: ["PyTorch_MLP", "GraphSAGE", "GAT", "LogisticRegression"]
    )


class ConsortiumPolicyEngine:
    """Evaluates consortium governance constraints prior to starting FL rounds."""

    def __init__(self, config: ConsortiumPolicyConfig | None = None) -> None:
        self.config = config or ConsortiumPolicyConfig()

    def validate_fl_round_preconditions(
        self,
        consortium: Consortium,
        participating_banks: list[str],
        round_epsilon: float,
        architecture: str = "PyTorch_MLP",
    ) -> tuple[bool, list[str]]:
        """Evaluates whether an FL round satisfies all consortium rules. Returns (is_valid, reasons)."""
        reasons: list[str] = []

        # 1. Quorum check: minimum participating bank count
        if len(participating_banks) < self.config.min_active_members:
            reasons.append(
                f"Insufficient participating members ({len(participating_banks)} < min {self.config.min_active_members})"
            )

        # 2. Differential privacy budget cap check
        if round_epsilon > consortium.max_epsilon or round_epsilon > self.config.max_epsilon_budget:
            max_limit = min(consortium.max_epsilon, self.config.max_epsilon_budget)
            reasons.append(
                f"Proposed DP epsilon ({round_epsilon:.2f}) exceeds max allowed limit ({max_limit:.2f})"
            )

        # 3. Member active status verification
        for bank_id in participating_banks:
            if bank_id not in consortium.members:
                reasons.append(
                    f"Bank '{bank_id}' is not an active member of consortium '{consortium.consortium_id}'"
                )

        # 4. Model architecture check
        if architecture not in self.config.allowed_architectures:
            reasons.append(
                f"Model architecture '{architecture}' is not allowed by consortium policy (Allowed: {self.config.allowed_architectures})"
            )

        is_valid = len(reasons) == 0
        if not is_valid:
            logger.warning(
                "FL Round policy validation failed for consortium '%s': %s",
                consortium.consortium_id,
                "; ".join(reasons),
            )
        return is_valid, reasons

    def enforce_fl_round_preconditions(
        self,
        consortium: Consortium,
        participating_banks: list[str],
        round_epsilon: float,
        architecture: str = "PyTorch_MLP",
    ) -> None:
        """Enforces policy gating, raising ConsortiumPolicyViolation if validation fails."""
        is_valid, reasons = self.validate_fl_round_preconditions(
            consortium=consortium,
            participating_banks=participating_banks,
            round_epsilon=round_epsilon,
            architecture=architecture,
        )
        if not is_valid:
            raise ConsortiumPolicyViolation(
                f"Consortium policy violation for '{consortium.consortium_id}': "
                + "; ".join(reasons)
            )
