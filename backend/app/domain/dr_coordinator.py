# ruff: noqa: UP042
"""Domain entities for Multi-Region Disaster Recovery and Failover."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CoordinatorRegionRole(str, Enum):
    """Regional role enum for federated coordinator nodes."""

    PRIMARY_ACTIVE = "PRIMARY_ACTIVE"
    PASSIVE_STANDBY = "PASSIVE_STANDBY"
    FAILOVER_PROMOTED = "FAILOVER_PROMOTED"


@dataclass
class DRNodeStatus:
    """Dataclass tracking regional coordinator cluster status."""

    node_id: str
    region: str
    role: CoordinatorRegionRole
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_healthy: bool = True


@dataclass
class FailoverAuditEvent:
    """Dataclass tracking an automatic cross-region failover event."""

    event_id: str
    failed_primary_region: str
    promoted_standby_region: str
    rto_seconds: float
    rpo_loss_records: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
