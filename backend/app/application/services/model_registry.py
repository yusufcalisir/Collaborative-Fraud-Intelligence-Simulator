"""Model Registry service.

Handles versioned model persistence, registry manifest updates, promotions, and rollbacks.
Global models are saved per simulation run with metrics metadata.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Any

import torch

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Manages versioned model artifacts and registry manifests.

    Models are stored in the filesystem under `storage/registry/{simulation_id}/`.
    A manifest file `registry.json` tracks versions, metrics, and active states.
    """

    def __init__(self, storage_dir: str | None = None) -> None:
        if storage_dir is None:
            # Resolve default storage path
            self.storage_dir = os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "storage",
                )
            )
        else:
            self.storage_dir = os.path.abspath(storage_dir)

        self.registry_root = os.path.join(self.storage_dir, "registry")
        os.makedirs(self.registry_root, exist_ok=True)

    def _get_sim_dir(self, simulation_id: str) -> str:
        sim_dir = os.path.join(self.registry_root, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _load_manifest(self, simulation_id: str) -> list[dict[str, Any]]:
        sim_dir = self._get_sim_dir(simulation_id)
        manifest_path = os.path.join(sim_dir, "registry.json")
        if not os.path.exists(manifest_path):
            return []
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning("Failed to load registry manifest for %s: %s", simulation_id, e)
        return []

    def _save_manifest(self, simulation_id: str, manifest: list[dict[str, Any]]) -> None:
        sim_dir = self._get_sim_dir(simulation_id)
        manifest_path = os.path.join(sim_dir, "registry.json")
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            logger.error("Failed to save registry manifest for %s: %s", simulation_id, e)

    def save_version(
        self,
        simulation_id: str,
        state_dict: dict[str, Any],
        metrics: dict[str, float],
        is_promoted: bool = True,
    ) -> dict[str, Any]:
        """Save a new version of the global model weights.

        Args:
            simulation_id: ID of the active simulation run.
            state_dict: PyTorch model state dict.
            metrics: Dict of metrics (accuracy, f1_score, auc_roc, recall, etc.).
            is_promoted: Whether this version is currently promoted as active.

        Returns:
            The created version entry metadata.
        """
        manifest = self._load_manifest(simulation_id)
        next_version = 1
        if manifest:
            next_version = max(entry["version"] for entry in manifest) + 1

        sim_dir = self._get_sim_dir(simulation_id)
        filename = f"model_v{next_version}.pt"
        filepath = os.path.join(sim_dir, filename)

        try:
            torch.save(state_dict, filepath)
            logger.info("Saved model version %d to %s", next_version, filepath)
        except Exception as e:
            logger.error("Failed to save model file: %s", e)
            raise

        # If this new version is promoted, set other versions to inactive
        if is_promoted:
            for entry in manifest:
                entry["is_active"] = False

        entry = {
            "version": next_version,
            "filename": filename,
            "metrics": metrics,
            "is_active": is_promoted,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest.append(entry)
        self._save_manifest(simulation_id, manifest)

        # If promoted, also copy/link this version to the main global model path for backward compatibility
        if is_promoted:
            self._update_global_model_link(simulation_id, filepath)

        return entry

    def _update_global_model_link(self, simulation_id: str, filepath: str) -> None:
        """Update the root global_model.pt file to point to the active version."""
        global_path = os.path.join(self.storage_dir, "global_model.pt")
        try:
            shutil.copy2(filepath, global_path)
            logger.info("Updated global_model.pt with version from %s", filepath)
        except Exception as e:
            logger.error("Failed to link/copy active version to global_model.pt: %s", e)

    def list_versions(self, simulation_id: str) -> list[dict[str, Any]]:
        """List all model versions tracked in this simulation registry."""
        return self._load_manifest(simulation_id)

    def load_version(self, simulation_id: str, version: int) -> dict[str, Any]:
        """Load state dict of a specific model version from the registry."""
        manifest = self._load_manifest(simulation_id)
        entry = next((e for e in manifest if e["version"] == version), None)
        if not entry:
            raise ValueError(f"Version {version} not found in registry for {simulation_id}")

        sim_dir = self._get_sim_dir(simulation_id)
        filepath = os.path.join(sim_dir, entry["filename"])
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file {filepath} not found on disk")

        try:
            return torch.load(filepath, map_location="cpu")
        except Exception as e:
            logger.error("Failed to load model file: %s", e)
            raise

    def get_active_version(self, simulation_id: str) -> dict[str, Any] | None:
        """Get metadata of the currently active model version."""
        manifest = self._load_manifest(simulation_id)
        return next((e for e in manifest if e["is_active"]), None)

    def rollback(self, simulation_id: str, version: int) -> dict[str, Any]:
        """Rollback/promote a specific historical version as the active model."""
        manifest = self._load_manifest(simulation_id)
        target_entry = next((e for e in manifest if e["version"] == version), None)
        if not target_entry:
            raise ValueError(f"Version {version} not found in registry for {simulation_id}")

        sim_dir = self._get_sim_dir(simulation_id)
        filepath = os.path.join(sim_dir, target_entry["filename"])
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file {filepath} not found on disk")

        # Mark target as active, all others as inactive
        for entry in manifest:
            entry["is_active"] = (entry["version"] == version)

        self._save_manifest(simulation_id, manifest)
        self._update_global_model_link(simulation_id, filepath)

        logger.info("Rolled back registry of %s to version %d", simulation_id, version)
        return target_entry
