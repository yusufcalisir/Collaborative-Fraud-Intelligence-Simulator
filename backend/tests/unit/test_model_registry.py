"""Unit tests for the Model Registry and Rollback service.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest

from app.application.services.model_registry import ModelRegistry


class TestModelRegistry(unittest.TestCase):
    """Test suite for ModelRegistry persistence, promotion, and rollback."""

    def setUp(self) -> None:
        # Create a temporary directory for registry storage
        self.test_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(storage_dir=self.test_dir)
        self.simulation_id = "test_sim_123"

        # Mock PyTorch state dict (simple dictionary for testing file saving/loading logic)
        self.mock_state_dict = {"weight": [0.1, 0.2, 0.3], "bias": [0.5]}
        self.mock_metrics = {"auc_roc": 0.85, "f1_score": 0.82, "loss": 0.15}

    def tearDown(self) -> None:
        # Clean up temporary storage directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_list_versions(self) -> None:
        # Save first version
        entry1 = self.registry.save_version(
            self.simulation_id, self.mock_state_dict, self.mock_metrics, is_promoted=True
        )
        self.assertEqual(entry1["version"], 1)
        self.assertTrue(entry1["is_active"])

        # Save second version (not promoted)
        entry2 = self.registry.save_version(
            self.simulation_id,
            {"weight": [0.4, 0.5], "bias": [0.9]},
            {"auc_roc": 0.81, "f1_score": 0.78, "loss": 0.21},
            is_promoted=False,
        )
        self.assertEqual(entry2["version"], 2)
        self.assertFalse(entry2["is_active"])

        # List all versions
        versions = self.registry.list_versions(self.simulation_id)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0]["version"], 1)
        self.assertTrue(versions[0]["is_active"])
        self.assertEqual(versions[1]["version"], 2)
        self.assertFalse(versions[1]["is_active"])

    def test_load_version(self) -> None:
        self.registry.save_version(
            self.simulation_id, self.mock_state_dict, self.mock_metrics, is_promoted=True
        )

        loaded_sd = self.registry.load_version(self.simulation_id, 1)
        self.assertEqual(loaded_sd["weight"], self.mock_state_dict["weight"])
        self.assertEqual(loaded_sd["bias"], self.mock_state_dict["bias"])

        with self.assertRaises(ValueError):
            self.registry.load_version(self.simulation_id, 999)

    def test_rollback(self) -> None:
        # Save v1 (promoted)
        self.registry.save_version(
            self.simulation_id, self.mock_state_dict, self.mock_metrics, is_promoted=True
        )

        # Save v2 (promoted)
        v2_sd = {"weight": [0.9, 0.9], "bias": [1.0]}
        v2_metrics = {"auc_roc": 0.91, "f1_score": 0.88, "loss": 0.09}
        self.registry.save_version(
            self.simulation_id, v2_sd, v2_metrics, is_promoted=True
        )

        # Verify active version is v2
        active = self.registry.get_active_version(self.simulation_id)
        self.assertIsNotNone(active)
        if active:
            self.assertEqual(active["version"], 2)

        # Rollback to v1
        updated = self.registry.rollback(self.simulation_id, 1)
        self.assertEqual(updated["version"], 1)
        self.assertTrue(updated["is_active"])

        # Verify manifest active flags updated
        versions = self.registry.list_versions(self.simulation_id)
        self.assertTrue(versions[0]["is_active"])
        self.assertFalse(versions[1]["is_active"])

        # Verify active version is now v1
        active = self.registry.get_active_version(self.simulation_id)
        self.assertIsNotNone(active)
        if active:
            self.assertEqual(active["version"], 1)


if __name__ == "__main__":
    unittest.main()
