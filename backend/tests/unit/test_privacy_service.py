"""Unit tests for the privacy service."""

import numpy as np
import pytest

from app.application.services.privacy_service import PrivacyBudget, PrivacyService
from app.domain.value_objects import ModelWeights


@pytest.fixture
def privacy_service() -> PrivacyService:
    return PrivacyService()


@pytest.fixture
def sample_weights() -> ModelWeights:
    return ModelWeights(
        layer_shapes=[(5,)],
        flat_weights=[1.0, 2.0, 3.0, 4.0, 5.0],
    )


class TestPrivacyBudget:
    def test_initial_budget(self) -> None:
        budget = PrivacyBudget(epsilon_per_round=1.0, delta=1e-5)
        assert budget.total_epsilon == 0.0
        assert budget.rounds_spent == 0

    def test_spending_accumulates(self) -> None:
        budget = PrivacyBudget(epsilon_per_round=1.0, delta=1e-5)
        budget.spend(1.0)
        budget.spend(1.0)
        assert budget.rounds_spent == 2
        assert budget.total_epsilon == 2.0

    def test_history_tracked(self) -> None:
        budget = PrivacyBudget(epsilon_per_round=1.0)
        budget.spend(0.5)
        budget.spend(0.8)
        assert budget.history == [0.5, 0.8]


class TestDifferentialPrivacy:
    def test_noise_changes_weights(
        self, privacy_service: PrivacyService, sample_weights: ModelWeights,
    ) -> None:
        noised = privacy_service.add_noise_to_weights(
            sample_weights, epsilon=1.0, rng=np.random.default_rng(42),
        )
        assert noised.flat_weights != sample_weights.flat_weights

    def test_lower_epsilon_adds_more_noise(
        self, privacy_service: PrivacyService, sample_weights: ModelWeights,
    ) -> None:
        rng = np.random.default_rng(42)
        noised_high_eps = privacy_service.add_noise_to_weights(
            sample_weights, epsilon=10.0, rng=rng,
        )
        rng = np.random.default_rng(42)
        noised_low_eps = privacy_service.add_noise_to_weights(
            sample_weights, epsilon=0.1, rng=rng,
        )

        # Lower epsilon should produce larger deviations
        dev_high = np.std(
            np.array(noised_high_eps.flat_weights) - np.array(sample_weights.flat_weights),
        )
        dev_low = np.std(
            np.array(noised_low_eps.flat_weights) - np.array(sample_weights.flat_weights),
        )
        assert dev_low > dev_high

    def test_preserves_shape(
        self, privacy_service: PrivacyService, sample_weights: ModelWeights,
    ) -> None:
        noised = privacy_service.add_noise_to_weights(sample_weights, epsilon=1.0)
        assert noised.layer_shapes == sample_weights.layer_shapes
        assert len(noised.flat_weights) == len(sample_weights.flat_weights)


class TestGradientClipping:
    def test_clips_large_update(self, privacy_service: PrivacyService) -> None:
        original = ModelWeights(layer_shapes=[(3,)], flat_weights=[0.0, 0.0, 0.0])
        updated = ModelWeights(layer_shapes=[(3,)], flat_weights=[10.0, 10.0, 10.0])

        clipped = privacy_service.clip_model_update(original, updated, max_norm=1.0)

        # The L2 norm of the clipped update should be <= 1.0
        delta = np.array(clipped.flat_weights) - np.array(original.flat_weights)
        assert np.linalg.norm(delta) <= 1.0 + 1e-6

    def test_small_update_unchanged(self, privacy_service: PrivacyService) -> None:
        original = ModelWeights(layer_shapes=[(3,)], flat_weights=[0.0, 0.0, 0.0])
        updated = ModelWeights(layer_shapes=[(3,)], flat_weights=[0.1, 0.1, 0.1])

        clipped = privacy_service.clip_model_update(original, updated, max_norm=10.0)

        np.testing.assert_allclose(
            clipped.flat_weights, updated.flat_weights, atol=1e-10,
        )


class TestBudgetManagement:
    def test_create_and_retrieve_budget(self, privacy_service: PrivacyService) -> None:
        budget = privacy_service.get_or_create_budget("sim_1", epsilon=2.0)
        assert budget.epsilon_per_round == 2.0

        # Should return the same budget
        budget2 = privacy_service.get_or_create_budget("sim_1")
        assert budget is budget2

    def test_clear_budget(self, privacy_service: PrivacyService) -> None:
        privacy_service.get_or_create_budget("sim_1")
        privacy_service.clear_budget("sim_1")

        # Creating again should be a fresh budget
        budget = privacy_service.get_or_create_budget("sim_1", epsilon=5.0)
        assert budget.epsilon_per_round == 5.0
        assert budget.rounds_spent == 0
