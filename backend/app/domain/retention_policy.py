# ruff: noqa: UP042
"""Domain models for Automated Retention & Erasure Policy Engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DataCategory(str, Enum):
    """Data category classification for TTL and retention governance."""

    TRANSACTION_LOGS = "TRANSACTION_LOGS"
    INFERENCE_AUDITS = "INFERENCE_AUDITS"
    GRAPH_EDGES = "GRAPH_EDGES"
    EXPLAINABILITY_REPORTS = "EXPLAINABILITY_REPORTS"


class ErasureMethod(str, Enum):
    """Method enum for data deletion/sanitization."""

    HARD_DELETE = "HARD_DELETE"
    CRYPTOGRAPHIC_ZEROIZATION = "CRYPTOGRAPHIC_ZEROIZATION"
    ANONYMIZATION = "ANONYMIZATION"


@dataclass
class RetentionPolicy:
    """Dataclass configuring data retention TTL rules per tenant and category."""

    category: DataCategory
    ttl_days: int
    erasure_method: ErasureMethod = ErasureMethod.CRYPTOGRAPHIC_ZEROIZATION

    def __post_init__(self) -> None:
        if self.ttl_days <= 0:
            raise ValueError("Retention policy ttl_days must be positive.")


@dataclass
class ErasureAuditRecord:
    """Dataclass tracking an executed cryptographic erasure event."""

    erasure_id: str
    tenant_id: str
    category: DataCategory
    records_erased_count: int
    erasure_hash: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
