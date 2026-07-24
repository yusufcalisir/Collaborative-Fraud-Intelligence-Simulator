# ruff: noqa: UP042
"""Domain models for Enterprise SLA/SLO Monitoring and Contract Enforcement."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SLOTargetType(str, Enum):
    """Target types for Service Level Objectives."""

    UPTIME_99_9 = "UPTIME_99_9"
    LATENCY_P95_100MS = "LATENCY_P95_100MS"
    SUCCESS_RATE_99_5 = "SUCCESS_RATE_99_5"


@dataclass
class SLOMetric:
    """Dataclass tracking an SLO metric and remaining error budget."""

    metric_name: str
    target_pct: float
    current_pct: float
    error_budget_remaining_pct: float


@dataclass
class SLAContract:
    """Dataclass representing an enterprise SLA contract with a tenant."""

    contract_id: str
    tenant_id: str
    tier: str = "ENTERPRISE"
    uptime_target_pct: float = 99.9
    monthly_credit_rate_pct: float = 10.0


@dataclass
class PenaltyReport:
    """Dataclass tracking contractual billing service credit discounts upon SLA breach."""

    report_id: str
    tenant_id: str
    month: str
    uptime_achieved_pct: float
    sla_breached: bool
    credit_discount_pct: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
