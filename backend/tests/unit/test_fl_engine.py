"""Unit tests for the federated learning engine."""

import numpy as np
import pytest

from app.application.services.fl_engine import FederatedLearningEngine
from app.application.services.model_service import ModelService
from app.application.services.privacy_service import PrivacyService
from app.config import get_settings
from app.domain.enums import AggregationMethod, ClientStatus
from app.domain.value_objects import ModelWeights


@pytest.fixture
def fl_engine() -> FederatedLearningEngine:
    settings = get_settings()
    model_service = ModelService(settings)
    privacy_service = PrivacyService()
    return FederatedLearningEngine(settings, model_service, privacy_service)


@pytest.fixture
def sample_weights() -> list[ModelWeights]:
    """Create sample model weights for testing aggregation."""
    shapes = [(4, 2), (4,)]
    return [
        ModelWeights(layer_shapes=shapes, flat_weights=[1.0] * 12),
        ModelWeights(layer_shapes=shapes, flat_weights=[3.0] * 12),
        ModelWeights(layer_shapes=shapes, flat_weights=[2.0] * 12),
    ]


class TestAggregation:
    def test_fed_avg_unweighted(
        self,
        fl_engine: FederatedLearningEngine,
        sample_weights: list[ModelWeights],
    ) -> None:
        result = fl_engine.aggregate_parameters(
            sample_weights,
            client_samples=[100, 100, 100],
            method=AggregationMethod.FED_AVG,
        )
        # Unweighted mean of [1, 3, 2] = 2.0
        assert all(abs(w - 2.0) < 1e-6 for w in result.flat_weights)

    def test_fed_avg_weighted(
        self,
        fl_engine: FederatedLearningEngine,
        sample_weights: list[ModelWeights],
    ) -> None:
        result = fl_engine.aggregate_parameters(
            sample_weights,
            client_samples=[1000, 100, 100],  # Bank A has 10x more data
            method=AggregationMethod.FED_AVG_WEIGHTED,
        )
        # Weighted toward bank A (value 1.0)
        assert all(w < 2.0 for w in result.flat_weights)

    def test_single_client_returns_unchanged(
        self,
        fl_engine: FederatedLearningEngine,
    ) -> None:
        weights = ModelWeights(
            layer_shapes=[(2, 2)],
            flat_weights=[1.0, 2.0, 3.0, 4.0],
        )
        result = fl_engine.aggregate_parameters([weights], [100])
        assert result.flat_weights == weights.flat_weights

    def test_empty_clients_raises(self, fl_engine: FederatedLearningEngine) -> None:
        with pytest.raises(ValueError, match="empty"):
            fl_engine.aggregate_parameters([], [])

    def test_preserves_layer_shapes(
        self,
        fl_engine: FederatedLearningEngine,
        sample_weights: list[ModelWeights],
    ) -> None:
        result = fl_engine.aggregate_parameters(
            sample_weights,
            [100, 100, 100],
        )
        assert result.layer_shapes == sample_weights[0].layer_shapes


class TestClientAvailability:
    def test_all_active_when_no_dropout(self, fl_engine: FederatedLearningEngine) -> None:
        statuses = fl_engine.simulate_client_availability(
            bank_ids=["a", "b", "c"],
            dropout_probability=0.0,
            rng=np.random.default_rng(42),
        )
        assert all(s == ClientStatus.ACTIVE for s in statuses.values())

    def test_all_dropped_with_high_probability(
        self,
        fl_engine: FederatedLearningEngine,
    ) -> None:
        statuses = fl_engine.simulate_client_availability(
            bank_ids=["a", "b", "c"],
            dropout_probability=1.0,
            rng=np.random.default_rng(42),
        )
        for s in statuses.values():
            assert s in (ClientStatus.DROPPED, ClientStatus.OFFLINE)

    def test_reconnection_possible(self, fl_engine: FederatedLearningEngine) -> None:
        """Previously dropped banks should have a chance to reconnect."""
        rng = np.random.default_rng(42)
        reconnected_count = 0
        trials = 100

        for _ in range(trials):
            statuses = fl_engine.simulate_client_availability(
                bank_ids=["a"],
                dropout_probability=0.0,
                previously_dropped={"a"},
                enable_reconnect=True,
                rng=rng,
            )
            if statuses["a"] == ClientStatus.RECONNECTED:
                reconnected_count += 1

        # Should reconnect ~70% of the time
        assert reconnected_count > 50


class TestSecureAggregation:
    def test_masks_preserve_aggregate(
        self,
        fl_engine: FederatedLearningEngine,
    ) -> None:
        """Masked aggregation should produce the same result as plaintext."""
        shapes: list[tuple[int, ...]] = [(3,)]
        weights = [
            ModelWeights(layer_shapes=shapes, flat_weights=[1.0, 2.0, 3.0]),
            ModelWeights(layer_shapes=shapes, flat_weights=[4.0, 5.0, 6.0]),
        ]

        rng = np.random.default_rng(42)
        masked = fl_engine.apply_secure_aggregation_masks(weights, rng=rng)

        # Individual masked weights should differ from original
        assert masked[0].flat_weights != weights[0].flat_weights

        # But the mean should be the same (masks cancel out)
        plain_avg = np.mean([w.flat_weights for w in weights], axis=0)
        masked_avg = np.mean([w.flat_weights for w in masked], axis=0)

        np.testing.assert_allclose(plain_avg, masked_avg, atol=1e-10)
