"""Model Registry and Rollback API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.application.services.model_registry import ModelRegistry
from app.presentation.routers.simulation import _simulation_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/registry", tags=["registry"])

# Shared registry instance
registry = ModelRegistry()


@router.get("/{simulation_id}/versions")
async def list_model_versions(simulation_id: str) -> list[dict[str, Any]]:
    """List all model versions tracked in the registry for this simulation."""
    try:
        return registry.list_versions(simulation_id)
    except Exception as e:
        logger.error("Failed to list versions for %s: %s", simulation_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list model versions: {e}",
        )


@router.post("/{simulation_id}/rollback/{version}")
async def rollback_model_version(simulation_id: str, version: int) -> dict[str, Any]:
    """Rollback/promote a specific model version as active."""
    try:
        updated_entry = registry.rollback(simulation_id, version)

        # Notify the UI about the rollback event
        _simulation_events.push_list(
            simulation_id,
            {
                "event_type": "rollback",
                "data": {
                    "version": version,
                    "message": f"Global model rolled back to version {version}",
                    "timestamp": updated_entry.get("created_at"),
                },
            },
        )
        return updated_entry
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to rollback model for %s: %s", simulation_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute model rollback: {e}",
        )


@router.get("/{simulation_id}/canary")
async def get_canary_history(simulation_id: str) -> list[dict[str, Any]]:
    """Retrieve the canary evaluation decisions history from simulation events."""
    events = _simulation_events.get_list(simulation_id)
    canary_history = []
    for event in events:
        if event.get("event_type") == "round_complete":
            data = event.get("data", {})
            canary_info = data.get("canary_info")
            if canary_info:
                canary_history.append(
                    {
                        "round": data.get("round"),
                        "version": canary_info.get("version"),
                        "candidate_auc": canary_info.get("candidate_auc"),
                        "promoted_auc": canary_info.get("promoted_auc"),
                        "is_promoted": canary_info.get("is_promoted"),
                        "reason": canary_info.get("reason"),
                    }
                )
    return canary_history
