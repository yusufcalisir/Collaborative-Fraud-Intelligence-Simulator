# ruff: noqa: UP042
"""Domain models for SRE Incident Response Playbooks and Triage Engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class IncidentSeverity(str, Enum):
    """Severity classification enum for system incidents."""

    SEV1_CRITICAL = "SEV1_CRITICAL"
    SEV2_MAJOR = "SEV2_MAJOR"
    SEV3_MODERATE = "SEV3_MODERATE"
    SEV4_MINOR = "SEV4_MINOR"


class IncidentCategory(str, Enum):
    """System incident trigger categories."""

    PRIVACY_LEAK_ALERT = "PRIVACY_LEAK_ALERT"
    CONSENSUS_FAILURE = "CONSENSUS_FAILURE"
    SLA_BREACH = "SLA_BREACH"
    PSI_DRIFT_SPIKE = "PSI_DRIFT_SPIKE"
    DATA_CORRUPTION = "DATA_CORRUPTION"


@dataclass
class PlaybookAction:
    """Dataclass representing an SRE mitigation step."""

    step_number: int
    action_name: str
    command_hint: str
    automated: bool = True


@dataclass
class IncidentRecord:
    """Dataclass tracking an active or resolved operational incident."""

    incident_id: str
    title: str
    severity: IncidentSeverity
    category: IncidentCategory
    status: str = "OPEN"  # "OPEN" or "RESOLVED"
    recommended_actions: list[PlaybookAction] = field(default_factory=list)
    resolution_notes: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
