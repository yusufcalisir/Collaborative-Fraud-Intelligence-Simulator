"""WebSocket handler for real-time training progress.

Clients connect to /ws/training/{simulation_id} and receive
round-by-round progress updates as JSON messages.

Uses Redis pub/sub to receive events from the Celery worker.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/training/{simulation_id}")
async def training_websocket(websocket: WebSocket, simulation_id: str) -> None:
    """Stream training progress events to a WebSocket client.

    The WebSocket subscribes to a Redis pub/sub channel for the given
    simulation. Events are forwarded to the client in real-time.

    Also replays any previously-published events so clients that
    connect mid-training can catch up.
    """
    await websocket.accept()
    logger.info("WebSocket connected for simulation %s", simulation_id)

    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

    try:
        # Replay past events
        events_key = f"simulation:{simulation_id}:events"
        past_events = await redis_client.lrange(events_key, 0, -1)
        for raw_event in past_events:
            await websocket.send_text(raw_event)

        # Subscribe to live events
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"training:{simulation_id}")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message and message["type"] == "message":
                await websocket.send_text(message["data"])

                # Check if simulation completed
                try:
                    event = json.loads(message["data"])
                    if event.get("event_type") in ("completed", "error"):
                        logger.info(
                            "Simulation %s ended, closing WebSocket", simulation_id,
                        )
                        break
                except json.JSONDecodeError:
                    pass

            # Small delay to prevent busy-waiting
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for simulation %s", simulation_id)
    except Exception:
        logger.exception("WebSocket error for simulation %s", simulation_id)
    finally:
        await redis_client.aclose()
        try:
            await websocket.close()
        except Exception:
            pass
