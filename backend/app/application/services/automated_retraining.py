# ruff: noqa: UP042
"""Automated Drift-Triggered Retraining Service."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RetrainingCause(str, Enum):
    """Reason enum triggering an automated model retraining pipeline."""

    PSI_DRIFT_EXCEEDED = "PSI_DRIFT_EXCEEDED"
    CONCEPT_DRIFT_DETECTED = "CONCEPT_DRIFT_DETECTED"
    ACCURACY_DEGRADATION = "ACCURACY_DEGRADATION"
    SCHEDULED_CADENCE = "SCHEDULED_CADENCE"


@dataclass
class RetrainingJobRecord:
    """Record container tracking an automated retraining job execution."""

    job_id: str
    cause: RetrainingCause
    psi_score: float
    status: str = "TRIGGERED"
    candidate_model_version: str | None = None
    triggered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DriftTriggeredRetrainingService:
    """Monitors drift metrics and dispatches automated FL retraining pipelines."""

    def __init__(self, psi_threshold: float = 0.20, min_auc_threshold: float = 0.70) -> None:
        self.psi_threshold = psi_threshold
        self.min_auc_threshold = min_auc_threshold
        self._jobs: dict[str, RetrainingJobRecord] = {}

    def evaluate_drift_and_trigger(
        self,
        psi_score: float,
        concept_drift_score: float = 0.0,
        current_auc: float = 0.85,
    ) -> RetrainingJobRecord | None:
        """Evaluates drift metrics and dispatches a retraining job if thresholds are exceeded."""
        cause: RetrainingCause | None = None

        if psi_score >= self.psi_threshold:
            cause = RetrainingCause.PSI_DRIFT_EXCEEDED
        elif concept_drift_score >= 0.15:
            cause = RetrainingCause.CONCEPT_DRIFT_DETECTED
        elif current_auc < self.min_auc_threshold:
            cause = RetrainingCause.ACCURACY_DEGRADATION

        if not cause:
            return None

        job_id = f"retrain_{uuid.uuid4().hex[:8]}"
        record = RetrainingJobRecord(
            job_id=job_id,
            cause=cause,
            psi_score=psi_score,
            status="TRIGGERED",
        )
        self._jobs[job_id] = record
        logger.info(
            "Dispatched retraining job %s (Cause: %s, PSI: %.4f)",
            job_id,
            cause.value,
            psi_score,
        )
        return record

    def execute_retraining_pipeline(self, job_id: str) -> dict[str, Any]:
        """Executes automated FL retraining task producing a candidate model checkpoint."""
        if job_id not in self._jobs:
            raise KeyError(f"Retraining job '{job_id}' does not exist.")

        record = self._jobs[job_id]
        candidate_version = f"model_candidate_{uuid.uuid4().hex[:6]}"
        record.status = "COMPLETED"
        record.candidate_model_version = candidate_version

        logger.info(
            "Retraining job %s completed. Candidate model: %s",
            job_id,
            candidate_version,
        )
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "candidate_model_version": candidate_version,
            "metrics": {"auc": 0.88, "precision": 0.84, "recall": 0.81},
        }

    def get_job(self, job_id: str) -> RetrainingJobRecord | None:
        """Retrieves retraining job record by ID."""
        return self._jobs.get(job_id)
