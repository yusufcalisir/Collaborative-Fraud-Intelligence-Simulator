"""Streaming engine.

Manages real-time event streaming for scenario replay. Events are
pushed to Redis pub/sub for WebSocket delivery to the frontend.

The streaming engine replays pre-built scenarios at configurable
speed, generating transactions, alerts, and intelligence events
that demonstrate collaborative fraud detection in real-time.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.entities_phase2 import Scenario

logger = logging.getLogger(__name__)


class StreamingEngine:
    """Manages streaming event delivery for scenario replay.

    The engine takes a Scenario (list of timed events) and replays
    them at configurable speed via Redis pub/sub. Frontend consumers
    receive events through WebSocket connections.

    This is designed for demonstration purposes — it simulates what
    a real-time transaction monitoring system would look like without
    requiring actual Kafka/Kinesis infrastructure.
    """

    def __init__(self) -> None:
        self._active_scenarios: dict[str, dict] = {}

    async def start_scenario(
        self,
        scenario: Scenario,
        speed_multiplier: float = 1.0,
        redis_client=None,
    ) -> str:
        """Start replaying a scenario's events.

        Args:
            scenario: The scenario to replay.
            speed_multiplier: Speed up (>1) or slow down (<1) event delivery.
            redis_client: Async Redis client for pub/sub.

        Returns:
            Scenario ID for tracking.
        """
        self._active_scenarios[scenario.id] = {
            "status": "running",
            "scenario_type": scenario.scenario_type.value,
            "total_events": len(scenario.events),
            "delivered_events": 0,
            "speed_multiplier": speed_multiplier,
            "started_at": datetime.now(UTC).isoformat(),
        }

        logger.info(
            "Starting scenario %s (%s) at %.1fx speed — %d events",
            scenario.id[:8],
            scenario.name,
            speed_multiplier,
            len(scenario.events),
        )

        # Launch event delivery in background
        asyncio.create_task(self._deliver_events(scenario, speed_multiplier, redis_client))

        return scenario.id

    async def stop_scenario(self, scenario_id: str) -> None:
        """Stop a running scenario."""
        if scenario_id in self._active_scenarios:
            self._active_scenarios[scenario_id]["status"] = "stopped"
            logger.info("Stopped scenario %s", scenario_id[:8])

    def get_scenario_status(self, scenario_id: str) -> dict | None:
        return self._active_scenarios.get(scenario_id)

    def get_active_scenarios(self) -> list[dict]:
        return [
            {"scenario_id": sid, **status}
            for sid, status in self._active_scenarios.items()
            if status["status"] == "running"
        ]

    async def _deliver_events(
        self,
        scenario: Scenario,
        speed_multiplier: float,
        redis_client=None,
    ) -> None:
        """Deliver scenario events with timing."""
        prev_delay = 0

        for i, event in enumerate(scenario.events):
            # Check if scenario was stopped
            status = self._active_scenarios.get(scenario.id, {})
            if status.get("status") != "running":
                break

            # Wait for the inter-event delay
            delay_ms = event.delay_ms - prev_delay
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000 / speed_multiplier)
            prev_delay = event.delay_ms

            # Prepare event payload
            event_data = {
                "event_id": event.id,
                "event_type": event.event_type,
                "bank_id": event.bank_id,
                "timestamp": event.timestamp.isoformat(),
                "payload": event.payload,
                "sequence": i + 1,
                "total": len(scenario.events),
                "scenario_id": scenario.id,
            }

            # Publish via Redis
            if redis_client:
                channel = f"streaming:{scenario.id}"
                await redis_client.publish(channel, json.dumps(event_data))

                # Also store in event list for late-joining consumers
                events_key = f"scenario:{scenario.id}:events"
                await redis_client.rpush(events_key, json.dumps(event_data))
                await redis_client.expire(events_key, 3600)

            # Update progress
            if scenario.id in self._active_scenarios:
                self._active_scenarios[scenario.id]["delivered_events"] = i + 1

            logger.debug(
                "Delivered event %d/%d: %s from %s",
                i + 1,
                len(scenario.events),
                event.event_type,
                event.bank_id,
            )

        # Mark as completed
        if scenario.id in self._active_scenarios:
            self._active_scenarios[scenario.id]["status"] = "completed"
            self._active_scenarios[scenario.id]["completed_at"] = datetime.now(UTC).isoformat()

        logger.info("Scenario %s completed", scenario.id[:8])
