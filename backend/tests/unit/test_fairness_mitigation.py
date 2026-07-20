import numpy as np
import pytest

from app.application.services.fl_engine import FederatedLearningEngine
from app.application.services.metrics_service import MetricsService
from app.application.services.model_service import ModelService


@pytest.fixture
def fl_engine() -> FederatedLearningEngine:
    from app.application.services.privacy_service import PrivacyService
    from app.config import get_settings

    settings = get_settings()
    model_service = ModelService(settings)
    privacy_service = PrivacyService()
    return FederatedLearningEngine(settings, model_service, privacy_service)


@pytest.fixture
def model_service() -> ModelService:
    from app.config import get_settings

    settings = get_settings()
    return ModelService(settings)


@pytest.fixture
def metrics_service() -> MetricsService:
    return MetricsService()


def test_aggregate_fairness_counts(fl_engine) -> None:
    client_counts = [
        {
            "protected_positive_pred": 100,
            "protected_negative_pred": 10,
            "reference_positive_pred": 200,
            "reference_negative_pred": 5,
            "protected_tp": 8,
            "protected_fn": 2,
            "reference_tp": 4,
            "reference_fn": 1,
        },
        {
            "protected_positive_pred": 50,
            "protected_negative_pred": 5,
            "reference_positive_pred": 100,
            "reference_negative_pred": 3,
            "protected_tp": 4,
            "protected_fn": 1,
            "reference_tp": 2,
            "reference_fn": 1,
        },
    ]
    aggregated = fl_engine.aggregate_fairness_counts(client_counts)

    assert aggregated["protected_positive_pred"] == 150
    assert aggregated["protected_negative_pred"] == 15
    assert aggregated["reference_positive_pred"] == 300
    assert aggregated["reference_negative_pred"] == 8
    assert aggregated["protected_tp"] == 12
    assert aggregated["protected_fn"] == 3
    assert aggregated["reference_tp"] == 6
    assert aggregated["reference_fn"] == 2


def test_model_training_with_bias_mitigation(model_service) -> None:
    X_train = np.random.uniform(0.0, 1.0, (100, 10)).astype(np.float32)
    y_train = np.random.choice([0.0, 1.0], 100).astype(np.float32)
    sens_attr = np.random.choice([0.0, 1.0], 100).astype(np.float32)

    model = model_service.create_model()
    # Train with mitigation enabled
    trained_model, loss_history, _ = model_service.train_local(
        model,
        X_train,
        y_train,
        epochs=1,
        learning_rate=0.01,
        batch_size=32,
        sens_attr=sens_attr,
        enable_bias_mitigation=True,
        fairness_lambda=1.0,
    )

    assert trained_model is not None
    assert len(loss_history) == 1
    assert loss_history[0] > 0


def test_model_evaluation_with_fairness(model_service) -> None:
    X_test = np.random.uniform(0.0, 1.0, (50, 10)).astype(np.float32)
    y_test = np.random.choice([0.0, 1.0], 50).astype(np.float32)
    sens_attr = np.random.choice([0.0, 1.0], 50).astype(np.float32)

    model = model_service.create_model()
    eval_res = model_service.evaluate(
        model,
        X_test,
        y_test,
        sens_attr=sens_attr,
    )

    assert "fairness_counts" in eval_res
    assert "disparate_impact" in eval_res
    assert "equal_opportunity_diff" in eval_res
    assert "protected_selection_rate" in eval_res
    assert "reference_selection_rate" in eval_res
    assert 0.0 <= eval_res["disparate_impact"] <= 100.0
    assert 0.0 <= eval_res["equal_opportunity_diff"] <= 1.0


def test_serialization_metrics(metrics_service) -> None:
    eval_dict = {
        "accuracy": 0.9,
        "precision": 0.8,
        "recall": 0.7,
        "f1_score": 0.75,
        "auc_roc": 0.85,
        "loss": 0.2,
        "confusion_matrix": [[40, 5], [2, 3]],
        "roc_fpr": [0.0, 1.0],
        "roc_tpr": [0.0, 1.0],
        "roc_thresholds": [1.0, 0.0],
        "disparate_impact": 0.85,
        "equal_opportunity_diff": 0.05,
        "protected_selection_rate": 0.8,
        "reference_selection_rate": 0.94,
    }
    metrics = metrics_service.from_eval_dict(eval_dict)
    assert metrics.disparate_impact == 0.85
    assert metrics.equal_opportunity_diff == 0.05

    serialized = metrics_service.metrics_to_dict(metrics)
    assert serialized["disparate_impact"] == 0.85
    assert serialized["equal_opportunity_diff"] == 0.05
    assert serialized["protected_selection_rate"] == 0.8
    assert serialized["reference_selection_rate"] == 0.94
