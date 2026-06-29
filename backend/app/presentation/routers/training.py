"""Training progress endpoints.

Provides access to per-round training data for a simulation.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/training", tags=["training"])


@router.get("/{simulation_id}/rounds")
async def get_training_rounds(simulation_id: str) -> list[dict]:
    """Get all training rounds for a simulation.

    Returns round-by-round metrics including loss, participants,
    dropouts, and timing data.
    """
    import redis as sync_redis
    from app.config import get_settings

    settings = get_settings()
    r = sync_redis.from_url(settings.redis_url, decode_responses=True)

    # Retrieve all events for this simulation
    events_key = f"simulation:{simulation_id}:events"
    raw_events = r.lrange(events_key, 0, -1)

    rounds = []
    for raw in raw_events:
        event = json.loads(raw)
        if event.get("event_type") == "round_complete":
            data = event["data"]
            rounds.append({
                "round_number": data.get("round"),
                "total_rounds": data.get("total"),
                "global_loss": data.get("loss", 0),
                "participating_banks": data.get("participants", []),
                "dropped_banks": data.get("dropped", []),
                "duration_ms": data.get("duration_ms", 0),
                "privacy_budget": data.get("privacy_budget", 0),
            })

    return rounds


@router.get("/{simulation_id}/rounds/{round_number}")
async def get_training_round(simulation_id: str, round_number: int) -> dict:
    """Get details for a specific training round."""
    rounds = await get_training_rounds(simulation_id)

    for r in rounds:
        if r.get("round_number") == round_number:
            return r

    raise HTTPException(
        status_code=404,
        detail=f"Round {round_number} not found for simulation {simulation_id}",
    )


@router.get("/{simulation_id}/progress")
async def get_training_progress(simulation_id: str) -> dict:
    """Get the latest progress update for a running simulation."""
    import redis as sync_redis
    from app.config import get_settings

    settings = get_settings()
    r = sync_redis.from_url(settings.redis_url, decode_responses=True)

    progress_key = f"simulation:{simulation_id}:progress"
    raw = r.get(progress_key)

    if raw:
        return json.loads(raw)

    return {"event_type": "unknown", "data": {"message": "No progress data available"}}
