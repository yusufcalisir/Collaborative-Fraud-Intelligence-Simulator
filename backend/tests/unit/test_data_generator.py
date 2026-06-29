"""Unit tests for the synthetic data generator."""

import numpy as np
import pytest

from app.application.services.data_generator import DataGenerator, FEATURE_NAMES


class TestDataGenerator:
    """Tests for DataGenerator service."""

    def setup_method(self) -> None:
        self.generator = DataGenerator(seed=42)

    def test_generates_three_banks(self) -> None:
        datasets = self.generator.generate_bank_datasets(
            bank_a_size=500, bank_b_size=300, bank_c_size=200,
        )
        assert set(datasets.keys()) == {"bank_a", "bank_b", "bank_c"}

    def test_correct_dataset_sizes(self) -> None:
        datasets = self.generator.generate_bank_datasets(
            bank_a_size=500, bank_b_size=300, bank_c_size=200,
        )
        for bank_id, (features, labels) in datasets.items():
            assert len(features) == len(labels)

    def test_bank_a_has_expected_size(self) -> None:
        datasets = self.generator.generate_bank_datasets(bank_a_size=1000)
        features, labels = datasets["bank_a"]
        assert len(features) == 1000

    def test_features_match_expected_columns(self) -> None:
        datasets = self.generator.generate_bank_datasets(bank_a_size=100)
        features, _ = datasets["bank_a"]
        assert list(features.columns) == FEATURE_NAMES

    def test_labels_are_binary(self) -> None:
        datasets = self.generator.generate_bank_datasets(bank_a_size=500)
        for _, (_, labels) in datasets.items():
            assert set(labels.unique()).issubset({0, 1})

    def test_fraud_ratios_differ_across_banks(self) -> None:
        """Banks should have intentionally different fraud rates (Non-IID)."""
        datasets = self.generator.generate_bank_datasets(
            bank_a_size=10000, bank_b_size=10000, bank_c_size=10000,
        )
        ratios = {}
        for bank_id, (_, labels) in datasets.items():
            ratios[bank_id] = labels.mean()

        # Bank B should have highest fraud ratio (~2.5%)
        assert ratios["bank_b"] > ratios["bank_a"]
        assert ratios["bank_b"] > ratios["bank_c"]

    def test_encode_features_returns_float_array(self) -> None:
        datasets = self.generator.generate_bank_datasets(bank_a_size=100)
        features, _ = datasets["bank_a"]
        encoded = DataGenerator.encode_features(features)

        assert isinstance(encoded, np.ndarray)
        assert encoded.dtype == np.float32
        assert encoded.shape == (100, len(FEATURE_NAMES))

    def test_encoded_features_normalized(self) -> None:
        datasets = self.generator.generate_bank_datasets(bank_a_size=500)
        features, _ = datasets["bank_a"]
        encoded = DataGenerator.encode_features(features)

        # Values should be in [0, 1] after normalization
        assert encoded.min() >= 0.0
        assert encoded.max() <= 1.0

    def test_bank_profiles_created(self) -> None:
        datasets = self.generator.generate_bank_datasets(
            bank_a_size=500, bank_b_size=300, bank_c_size=200,
        )
        profiles = self.generator.create_bank_profiles(datasets)

        assert len(profiles) == 3
        assert "bank_a" in profiles
        assert profiles["bank_a"].bank_name == "Meridian National"
        assert profiles["bank_a"].num_transactions == 500

    def test_bank_entities_created(self) -> None:
        datasets = self.generator.generate_bank_datasets(
            bank_a_size=500, bank_b_size=300, bank_c_size=200,
        )
        profiles = self.generator.create_bank_profiles(datasets)
        banks = self.generator.create_bank_entities(datasets, profiles)

        assert len(banks) == 3
        bank_names = {b.name for b in banks}
        assert "Meridian National" in bank_names
        assert "Nexus Digital" in bank_names
        assert "Heritage Regional" in bank_names

    def test_deterministic_with_seed(self) -> None:
        gen1 = DataGenerator(seed=123)
        gen2 = DataGenerator(seed=123)

        d1 = gen1.generate_bank_datasets(bank_a_size=100)
        d2 = gen2.generate_bank_datasets(bank_a_size=100)

        f1, l1 = d1["bank_a"]
        f2, l2 = d2["bank_a"]

        assert f1.equals(f2)
        assert l1.equals(l2)
