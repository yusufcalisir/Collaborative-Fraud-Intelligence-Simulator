"""Unit tests for the metrics service."""

import pytest

from app.application.services.metrics_service import MetricsService
from app.domain.value_objects import EvaluationMetrics


@pytest.fixture
def metrics_service() -> MetricsService:
    return MetricsService()


def _make_metrics(accuracy: float, f1: float, auc: float) -> EvaluationMetrics:
    return EvaluationMetrics(
        accuracy=accuracy,
        precision=f1,
        recall=f1,
        f1_score=f1,
        auc_roc=auc,
        loss=0.3,
        confusion_matrix=[[90, 5], [3, 2]],
        roc_fpr=[0.0, 0.5, 1.0],
        roc_tpr=[0.0, 0.8, 1.0],
        roc_thresholds=[1.0, 0.5, 0.0],
    )


class TestMetricsService:
    def test_from_eval_dict(self) -> None:
        eval_dict = {
            "accuracy": 0.95,
            "precision": 0.90,
            "recall": 0.85,
            "f1_score": 0.87,
            "auc_roc": 0.92,
            "loss": 0.15,
            "confusion_matrix": [[950, 20], [15, 15]],
            "roc_fpr": [0.0, 0.5, 1.0],
            "roc_tpr": [0.0, 0.9, 1.0],
            "roc_thresholds": [1.0, 0.5, 0.0],
        }
        metrics = MetricsService.from_eval_dict(eval_dict)
        assert metrics.accuracy == 0.95
        assert metrics.f1_score == 0.87

    def test_from_eval_dict_with_feature_importance(self) -> None:
        eval_dict = {
            "accuracy": 0.9, "precision": 0.8, "recall": 0.7,
            "f1_score": 0.75, "auc_roc": 0.85, "loss": 0.2,
            "confusion_matrix": [[80, 10], [5, 5]],
            "roc_fpr": [0.0, 1.0], "roc_tpr": [0.0, 1.0],
            "roc_thresholds": [1.0, 0.0],
        }
        feat_imp = {"amount": 0.9, "velocity": 0.7}
        metrics = MetricsService.from_eval_dict(eval_dict, feat_imp)
        assert metrics.feature_importance == {"amount": 0.9, "velocity": 0.7}

    def test_aggregate_improvement_positive(self) -> None:
        local = [_make_metrics(0.80, 0.60, 0.75)]
        federated = [_make_metrics(0.90, 0.75, 0.85)]

        improvement = MetricsService.compute_aggregate_improvement(local, federated)
        assert improvement["accuracy"] == pytest.approx(0.10, abs=1e-4)
        assert improvement["f1_score"] == pytest.approx(0.15, abs=1e-4)

    def test_aggregate_improvement_averages_across_banks(self) -> None:
        local = [
            _make_metrics(0.80, 0.60, 0.70),
            _make_metrics(0.85, 0.70, 0.80),
        ]
        federated = [
            _make_metrics(0.90, 0.75, 0.85),
            _make_metrics(0.90, 0.75, 0.85),
        ]

        improvement = MetricsService.compute_aggregate_improvement(local, federated)
        # (0.10 + 0.05) / 2 = 0.075
        assert improvement["accuracy"] == pytest.approx(0.075, abs=1e-4)

    def test_empty_metrics_returns_empty(self) -> None:
        result = MetricsService.compute_aggregate_improvement([], [])
        assert result == {}

    def test_metrics_to_dict_roundtrip(self) -> None:
        metrics = _make_metrics(0.95, 0.85, 0.90)
        d = MetricsService.metrics_to_dict(metrics)
        assert d["accuracy"] == 0.95
        assert d["f1_score"] == 0.85
        assert len(d["confusion_matrix"]) == 2
