# ruff: noqa: UP042
"""Domain models for Multi-Stage Production Model State Machine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ModelState(str, Enum):
    """Production progression states for a registered model checkpoint."""

    STAGING = "STAGING"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


class InvalidStateTransitionError(Exception):
    """Raised when an illegal model state transition is attempted."""

    pass


# Allowed state transition mapping
ALLOWED_TRANSITIONS: dict[ModelState, set[ModelState]] = {
    ModelState.STAGING: {ModelState.SHADOW, ModelState.ARCHIVED},
    ModelState.SHADOW: {ModelState.CANARY, ModelState.ARCHIVED},
    ModelState.CANARY: {ModelState.PRODUCTION, ModelState.SHADOW, ModelState.ARCHIVED},
    ModelState.PRODUCTION: {ModelState.ARCHIVED},
    ModelState.ARCHIVED: set(),  # Terminal state
}


@dataclass
class ModelLifecycleRecord:
    """Record container tracking a model version's production state machine trajectory."""

    model_version: str
    current_state: ModelState = ModelState.STAGING
    compliance_signoff: bool = False
    state_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.state_history:
            self.state_history.append(
                {
                    "from_state": None,
                    "to_state": self.current_state.value,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "actor_role": "SYSTEM",
                    "reason": "Initialized in STAGING",
                }
            )


class ModelLifecycleManager:
    """Manages progression of model checkpoints through progressive production stages."""

    def __init__(self) -> None:
        self._models: dict[str, ModelLifecycleRecord] = {}

    def register_model(self, model_version: str) -> ModelLifecycleRecord:
        """Initializes a new model checkpoint version in STAGING state."""
        clean_version = model_version.strip()
        if clean_version in self._models:
            return self._models[clean_version]

        record = ModelLifecycleRecord(model_version=clean_version)
        self._models[clean_version] = record
        logger.info("Registered model version '%s' in STAGING", clean_version)
        return record

    def transition_state(
        self,
        model_version: str,
        target_state: ModelState,
        actor_role: str = "ML_ENGINEER",
        signoff_approved: bool = False,
        reason: str = "Standard progression",
    ) -> ModelLifecycleRecord:
        """Transitions a model checkpoint to target_state with transition & signoff validation."""
        clean_version = model_version.strip()
        if clean_version not in self._models:
            self.register_model(clean_version)

        record = self._models[clean_version]
        current = record.current_state

        if target_state not in ALLOWED_TRANSITIONS[current]:
            raise InvalidStateTransitionError(
                f"Illegal state transition for model '{clean_version}' from {current.value} to {target_state.value}. Allowed: {[s.value for s in ALLOWED_TRANSITIONS[current]]}"
            )

        # Enforce compliance signoff for CANARY or PRODUCTION promotions
        if (
            target_state in (ModelState.CANARY, ModelState.PRODUCTION)
            and not signoff_approved
            and not record.compliance_signoff
        ):
            raise InvalidStateTransitionError(
                f"Compliance sign-off is required to promote model '{clean_version}' to {target_state.value}."
            )

        if signoff_approved:
            record.compliance_signoff = True

        # Execute transition
        record.current_state = target_state
        record.state_history.append(
            {
                "from_state": current.value,
                "to_state": target_state.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "actor_role": actor_role,
                "reason": reason,
            }
        )

        logger.info(
            "Model '%s' transitioned from %s to %s by %s",
            clean_version,
            current.value,
            target_state.value,
            actor_role,
        )
        return record

    def get_model_record(self, model_version: str) -> ModelLifecycleRecord | None:
        """Retrieves model lifecycle record by version."""
        return self._models.get(model_version.strip())
