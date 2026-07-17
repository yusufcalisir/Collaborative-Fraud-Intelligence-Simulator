"""Model Registry and Rollback API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.application.services.model_registry import ModelEvaluationEngine, ModelRegistry
from app.presentation.routers.simulation import _simulation_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/registry", tags=["registry"])

# Shared registry instance
registry = ModelRegistry()
_eval_engine = ModelEvaluationEngine(registry)


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


class ModelSignOffRequest(BaseModel):
    role: str = Field(..., description="Role of the signer ('compliance' or 'ml_engineer')")
    user: str = Field(..., description="Name/identifier of the user signing off")
    signature: str = Field(..., description="Cryptographic signature string")
    fairness_score: float = Field(1.0, description="Evaluated model fairness score")
    bias_metric: float = Field(0.0, description="Evaluated model bias metric")
    drift_divergence: float = Field(0.0, description="Evaluated dataset drift divergence")


@router.post("/{simulation_id}/versions/{version}/signoff")
async def sign_off_model(
    simulation_id: str, version: int, payload: ModelSignOffRequest
) -> dict[str, Any]:
    """Approve and sign off on a new global model's metrics."""
    try:
        updated_entry = registry.sign_off(
            simulation_id=simulation_id,
            version=version,
            role=payload.role,
            user=payload.user,
            signature=payload.signature,
            fairness_score=payload.fairness_score,
            bias_metric=payload.bias_metric,
            drift_divergence=payload.drift_divergence,
        )
        return updated_entry
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Failed to sign off on model version: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit model sign-off: {e}",
        )


@router.get("/{simulation_id}/shadow/metrics")
async def get_shadow_metrics(simulation_id: str) -> dict[str, Any]:
    """Get real-time shadowing deployment and evaluation metrics."""
    try:
        return _eval_engine.get_shadow_metrics(simulation_id)
    except Exception as e:
        logger.error("Failed to retrieve shadow metrics: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load shadow metrics: {e}",
        )
