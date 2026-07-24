# ruff: noqa: UP042
"""Domain models for Commercial Multi-Role Web Management Console."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConsoleUserRole(str, Enum):
    """Enterprise user role enum for tailored web console dashboards."""

    EXECUTIVE = "EXECUTIVE"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    ML_ENGINEER = "ML_ENGINEER"
    FRAUD_INVESTIGATOR = "FRAUD_INVESTIGATOR"


@dataclass
class RoleViewConfig:
    """Dataclass configuring visible dashboard widgets and permissions per user role."""

    role: ConsoleUserRole
    visible_widgets: list[str]
    permissions: list[str]
    theme: str = "dark_glassmorphism"


@dataclass
class ConsoleMetricSummary:
    """Dataclass tracking unified high-level platform performance metrics."""

    active_bank_nodes_count: int = 3
    federated_rounds_completed: int = 25
    global_model_auc: float = 0.885
    total_cases_opened: int = 42
    sla_compliance_pct: float = 99.95
    widgets: dict[str, bool] = field(default_factory=dict)
