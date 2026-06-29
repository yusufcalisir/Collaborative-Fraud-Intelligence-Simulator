"""Redis cache client.

Used for caching active simulation state and real-time training
progress. Not used as a primary data store.
"""

from __future__ import annotations

import json
import logging

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

redis_client = redis.from_url(
    settings.celery_broker_url,
    decode_responses=True,
    ssl_cert_reqs="none" if settings.celery_broker_url.startswith("rediss://") else None,
)


async def set_simulation_progress(simulation_id: str, data: dict) -> None:
    """Cache the current progress of a running simulation."""
    key = f"simulation:{simulation_id}:progress"
    await redis_client.set(key, json.dumps(data), ex=3600)


async def get_simulation_progress(simulation_id: str) -> dict | None:
    """Retrieve cached simulation progress."""
    key = f"simulation:{simulation_id}:progress"
    raw = await redis_client.get(key)
    if raw:
        return json.loads(raw)
    return None


async def publish_training_event(simulation_id: str, event: dict) -> None:
    """Publish a training event to Redis pub/sub for WebSocket consumers."""
    channel = f"training:{simulation_id}"
    await redis_client.publish(channel, json.dumps(event))


async def check_redis_health() -> bool:
    """Check if Redis is responsive."""
    try:
        return await redis_client.ping()
    except Exception:
        logger.warning("Redis health check failed", exc_info=True)
        return False
