# ruff: noqa: UP042
"""Domain models and state machine for Investigator Case Workbench."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class InvestigatorCaseStatus(str, Enum):
    """Lifecycle status enum for an investigator fraud case."""

    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    ESCALATED = "ESCALATED"
    RESOLVED_CONFIRMED_FRAUD = "RESOLVED_CONFIRMED_FRAUD"
    RESOLVED_FALSE_POSITIVE = "RESOLVED_FALSE_POSITIVE"


class InvalidCaseTransitionError(Exception):
    """Raised when an illegal case lifecycle state transition is attempted."""

    pass


# Allowed state transition map for case lifecycle
ALLOWED_CASE_TRANSITIONS: dict[InvestigatorCaseStatus, set[InvestigatorCaseStatus]] = {
    InvestigatorCaseStatus.NEW: {
        InvestigatorCaseStatus.ASSIGNED,
        InvestigatorCaseStatus.UNDER_INVESTIGATION,
    },
    InvestigatorCaseStatus.ASSIGNED: {
        InvestigatorCaseStatus.UNDER_INVESTIGATION,
        InvestigatorCaseStatus.ESCALATED,
    },
    InvestigatorCaseStatus.UNDER_INVESTIGATION: {
        InvestigatorCaseStatus.ESCALATED,
        InvestigatorCaseStatus.RESOLVED_CONFIRMED_FRAUD,
        InvestigatorCaseStatus.RESOLVED_FALSE_POSITIVE,
    },
    InvestigatorCaseStatus.ESCALATED: {
        InvestigatorCaseStatus.UNDER_INVESTIGATION,
        InvestigatorCaseStatus.RESOLVED_CONFIRMED_FRAUD,
        InvestigatorCaseStatus.RESOLVED_FALSE_POSITIVE,
    },
    InvestigatorCaseStatus.RESOLVED_CONFIRMED_FRAUD: set(),  # Terminal state
    InvestigatorCaseStatus.RESOLVED_FALSE_POSITIVE: set(),  # Terminal state
}


@dataclass
class FraudCaseRecord:
    """Domain model representing a fraud investigation case."""

    case_id: str
    title: str
    alert_ids: list[str] = field(default_factory=list)
    status: InvestigatorCaseStatus = InvestigatorCaseStatus.NEW
    assigned_to: str | None = None
    supervisor_signature: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.history:
            self.history.append(
                {
                    "from_status": None,
                    "to_status": self.status.value,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "actor_id": "SYSTEM",
                    "notes": "Initialized case in NEW status",
                }
            )


class CaseLifecycleStateMachine:
    """Manages 6-stage case lifecycle progression and enforces Four-Eyes supervisor signoffs."""

    def transition_case(
        self,
        record: FraudCaseRecord,
        target_status: InvestigatorCaseStatus,
        actor_id: str,
        supervisor_signature: str | None = None,
        notes: str = "Status transition",
    ) -> FraudCaseRecord:
        """Transitions case to target_status, validating transitions and Four-Eyes signoffs."""
        current = record.status

        if target_status not in ALLOWED_CASE_TRANSITIONS[current]:
            raise InvalidCaseTransitionError(
                f"Illegal transition for case '{record.case_id}' from {current.value} to {target_status.value}. Allowed: {[s.value for s in ALLOWED_CASE_TRANSITIONS[current]]}"
            )

        # Four-Eyes Principle: Resolving a case requires supervisor signature
        is_resolution = target_status in (
            InvestigatorCaseStatus.RESOLVED_CONFIRMED_FRAUD,
            InvestigatorCaseStatus.RESOLVED_FALSE_POSITIVE,
        )
        if is_resolution:
            sig = supervisor_signature or record.supervisor_signature
            if not sig or not sig.startswith("SIG_SUPERVISOR_"):
                raise InvalidCaseTransitionError(
                    f"Four-Eyes supervisor dual-authorization signature required to resolve case '{record.case_id}' to {target_status.value}."
                )
            record.supervisor_signature = sig

        record.status = target_status
        record.history.append(
            {
                "from_status": current.value,
                "to_status": target_status.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "actor_id": actor_id,
                "notes": notes,
            }
        )

        logger.info(
            "Case '%s' transitioned from %s to %s by %s",
            record.case_id,
            current.value,
            target_status.value,
            actor_id,
        )
        return record
