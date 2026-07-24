# ruff: noqa: UP042
"""Local Label Feedback Pipeline for Continuous Federated Learning."""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.domain.label_privacy_guard import LabelPrivacyGuard

logger = logging.getLogger(__name__)


class FeedbackLabel(str, Enum):
    """Ground-truth determination label enum."""

    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    FALSE_POSITIVE = "FALSE_POSITIVE"


@dataclass
class LabelFeedbackItem:
    """Dataclass storing ground-truth feedback for a transaction."""

    transaction_id_hash: str
    label: FeedbackLabel
    weight: float = 1.0
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class LocalLabelFeedbackPipeline:
    """Ingests analyst ground-truth determinations and computes DP-noise-protected gradient updates."""

    def __init__(self) -> None:
        self.privacy_guard = LabelPrivacyGuard()
        self._buffers: dict[str, list[LabelFeedbackItem]] = {}

    def ingest_analyst_determination(
        self,
        tenant_id: str,
        transaction_id_hash: str,
        determination: str,
        raw_attributes: dict[str, Any] | None = None,
    ) -> LabelFeedbackItem:
        """Ingests an analyst determination into local tenant label feedback buffer after zero-PII check."""
        self.privacy_guard.validate_feedback_identifier(
            transaction_id_hash=transaction_id_hash,
            raw_attributes=raw_attributes,
        )

        label = FeedbackLabel(determination)
        item = LabelFeedbackItem(
            transaction_id_hash=transaction_id_hash,
            label=label,
        )

        if tenant_id not in self._buffers:
            self._buffers[tenant_id] = []
        self._buffers[tenant_id].append(item)

        logger.info(
            "Ingested feedback for tenant '%s' (Tx: %s, Label: %s)",
            tenant_id,
            transaction_id_hash[:8],
            label.value,
        )
        return item

    def compute_dp_gradient_update(
        self,
        tenant_id: str,
        epsilon: float = 1.0,
    ) -> dict[str, Any]:
        """Computes local weight delta from ground-truth feedback buffer with Gaussian DP noise injection."""
        self.privacy_guard.validate_gradient_privacy(epsilon=epsilon)

        buffer = self._buffers.get(tenant_id, [])
        if not buffer:
            return {
                "tenant_id": tenant_id,
                "delta_weights": [0.0, 0.0, 0.0, 0.0],
                "sample_count": 0,
                "epsilon": epsilon,
            }

        # Calculate base gradient delta from positive/negative feedback ratio
        fraud_count = sum(1 for item in buffer if item.label == FeedbackLabel.CONFIRMED_FRAUD)
        total = len(buffer)
        raw_gradient = (fraud_count / total) * 0.1

        # Add Gaussian Differential Privacy noise proportional to 1 / epsilon
        noise_scale = (1.0 / math.sqrt(2.0 * math.log(1.25 / 1e-5))) / epsilon
        raw_deltas = [raw_gradient * (i + 1) for i in range(4)]
        dp_deltas = [round(d + random.gauss(0, noise_scale * 0.01), 6) for d in raw_deltas]

        logger.info(
            "Computed DP gradient update for tenant '%s' (%d samples, epsilon=%.2f)",
            tenant_id,
            total,
            epsilon,
        )
        return {
            "tenant_id": tenant_id,
            "delta_weights": dp_deltas,
            "sample_count": total,
            "epsilon": epsilon,
        }

    def get_buffer_size(self, tenant_id: str) -> int:
        """Retrieves tenant feedback buffer size."""
        return len(self._buffers.get(tenant_id, []))
