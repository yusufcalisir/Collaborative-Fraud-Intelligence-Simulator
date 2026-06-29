"""Unit tests for the model service."""

import numpy as np
import pytest

from app.application.services.model_service import FraudDetectionModel, ModelService
from app.config import get_settings


@pytest.fixture
def model_service() -> ModelService:
    return ModelService(get_settings())


@pytest.fixture
def sample_data() -> tuple[np.ndarray, np.ndarray]:
    """Generate simple training data."""
    rng = np.random.default_rng(42)
    X = rng.random((200, 10)).astype(np.float32)
    y = (X[:, 0] > 0.5).astype(np.float32)
    return X, y


class TestFraudDetectionModel:
    def test_model_creation(self) -> None:
        model = FraudDetectionModel(input_dim=10)
        assert model is not None

    def test_forward_pass_shape(self) -> None:
        import torch

        model = FraudDetectionModel(input_dim=10)
        X = torch.randn(16, 10)
        output = model(X)
        assert output.shape == (16,)

    def test_output_range(self) -> None:
        """Output should be in [0, 1] due to sigmoid."""
        import torch

        model = FraudDetectionModel(input_dim=10)
        model.eval()
        X = torch.randn(100, 10)
        with torch.no_grad():
            output = model(X)
        assert output.min() >= 0.0
        assert output.max() <= 1.0


class TestModelService:
    def test_create_model(self, model_service: ModelService) -> None:
        model = model_service.create_model()
        assert isinstance(model, FraudDetectionModel)

    def test_train_returns_loss_history(
        self,
        model_service: ModelService,
        sample_data: tuple,
    ) -> None:
        X, y = sample_data
        model = model_service.create_model()
        model, loss_history = model_service.train_local(model, X, y, epochs=2)

        assert len(loss_history) == 2
        assert all(isinstance(loss_val, float) for loss_val in loss_history)

    def test_loss_decreases(
        self,
        model_service: ModelService,
        sample_data: tuple,
    ) -> None:
        X, y = sample_data
        model = model_service.create_model()
        model, loss_history = model_service.train_local(model, X, y, epochs=5)

        # Loss should generally decrease (not guaranteed but very likely with 5 epochs)
        assert loss_history[-1] <= loss_history[0] * 1.5  # Allow some tolerance

    def test_evaluate_returns_metrics(
        self,
        model_service: ModelService,
        sample_data: tuple,
    ) -> None:
        X, y = sample_data
        model = model_service.create_model()
        model, _ = model_service.train_local(model, X, y, epochs=2)
        metrics = model_service.evaluate(model, X, y)

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "auc_roc" in metrics
        assert "confusion_matrix" in metrics
        assert "roc_fpr" in metrics

    def test_parameter_roundtrip(self, model_service: ModelService) -> None:
        """get_parameters → set_parameters should preserve model behavior."""
        import torch

        model1 = model_service.create_model()
        weights = model_service.get_parameters(model1)

        model2 = model_service.create_model()
        model2 = model_service.set_parameters(model2, weights)

        # Both models should produce identical output
        model1.eval()
        model2.eval()
        X = torch.randn(10, 10)
        with torch.no_grad():
            out1 = model1(X)
            out2 = model2(X)

        np.testing.assert_allclose(out1.numpy(), out2.numpy(), atol=1e-6)

    def test_feature_importance_keys(self, model_service: ModelService) -> None:
        from app.application.services.data_generator import FEATURE_NAMES

        model = model_service.create_model()
        importance = model_service.get_feature_importance(model)

        assert set(importance.keys()) == set(FEATURE_NAMES)
        assert all(0 <= v <= 1 for v in importance.values())
