"""Metrics computation and comparison service.

Converts raw evaluation dicts from ModelService into domain value objects,
and computes aggregate comparisons between local and federated models.
"""

from __future__ import annotations

import logging

from app.domain.value_objects import EvaluationMetrics

logger = logging.getLogger(__name__)


class MetricsService:
    """Transforms and aggregates evaluation metrics."""

    @staticmethod
    def from_eval_dict(
        eval_dict: dict,
        feature_importance: dict[str, float] | None = None,
    ) -> EvaluationMetrics:
        """Convert ModelService evaluation output to a domain value object."""
        return EvaluationMetrics(
            accuracy=eval_dict["accuracy"],
            precision=eval_dict["precision"],
            recall=eval_dict["recall"],
            f1_score=eval_dict["f1_score"],
            auc_roc=eval_dict["auc_roc"],
            loss=eval_dict["loss"],
            confusion_matrix=eval_dict["confusion_matrix"],
            roc_fpr=eval_dict["roc_fpr"],
            roc_tpr=eval_dict["roc_tpr"],
            roc_thresholds=eval_dict["roc_thresholds"],
            feature_importance=feature_importance or {},
        )

    @staticmethod
    def compute_aggregate_improvement(
        local_metrics: list[EvaluationMetrics],
        federated_metrics: list[EvaluationMetrics],
    ) -> dict[str, float]:
        """Compute average improvement across all banks.

        Returns the mean delta for each metric (federated - local).
        Positive values indicate federated model outperforms local.
        """
        if not local_metrics or not federated_metrics:
            return {}

        n = len(local_metrics)
        improvements: dict[str, float] = {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "auc_roc": 0.0,
        }

        for local, federated in zip(local_metrics, federated_metrics, strict=False):
            improvements["accuracy"] += federated.accuracy - local.accuracy
            improvements["precision"] += federated.precision - local.precision
            improvements["recall"] += federated.recall - local.recall
            improvements["f1_score"] += federated.f1_score - local.f1_score
            improvements["auc_roc"] += federated.auc_roc - local.auc_roc

        return {k: round(v / n, 4) for k, v in improvements.items()}

    @staticmethod
    def metrics_to_dict(metrics: EvaluationMetrics) -> dict:
        """Serialize metrics to a plain dict for storage/API response."""
        return {
            "accuracy": metrics.accuracy,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1_score": metrics.f1_score,
            "auc_roc": metrics.auc_roc,
            "loss": metrics.loss,
            "confusion_matrix": metrics.confusion_matrix,
            "roc_fpr": metrics.roc_fpr,
            "roc_tpr": metrics.roc_tpr,
            "roc_thresholds": metrics.roc_thresholds,
            "feature_importance": metrics.feature_importance,
        }
