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
from typing import TYPE_CHECKING, Any

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
        redis_client: Any = None,
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
        redis_client: Any = None,
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

            # Process the event locally to populate in-memory stores
            try:
                await self._process_streaming_event(event)
            except Exception as exc:
                logger.error(
                    "Error processing streaming event %s: %s", event.id, exc, exc_info=True
                )

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

    async def _process_streaming_event(self, event: Any) -> None:
        """Process a scenario streaming event and update the local in-memory stores."""
        import uuid

        from app.domain.entities_phase2 import Alert, CaseEvent, SharedIntelligence
        from app.domain.enums import (
            AlertSeverity,
            AlertStatus,
            CasePriority,
            EntityType,
            IntelligenceType,
            RelationshipType,
            RiskLevel,
        )
        from app.presentation.routers.alerts import get_alert_service
        from app.presentation.routers.cases import get_case_service
        from app.presentation.routers.entities import get_entity_service
        from app.presentation.routers.graph import get_graph_engine

        alert_svc = get_alert_service()
        case_svc = get_case_service()
        entity_svc = get_entity_service()
        graph_engine = get_graph_engine()

        payload = event.payload or {}

        if event.event_type == "transaction":
            # 1. Register customer entity
            cust_id = payload.get("customer_id")
            if cust_id:
                cust_entity = entity_svc.create_entity(
                    EntityType.CUSTOMER,
                    cust_id,
                    event.bank_id,
                    {
                        "total_spent": payload.get("amount", 0),
                        "risk_score": payload.get("risk_score", 0),
                        "bank_name": payload.get("bank_name", event.bank_id),
                    },
                )
                graph_engine.register_entity(cust_entity)

                # 2. Register merchant entity if present
                merchant = payload.get("merchant_category")
                if merchant:
                    merch_entity = entity_svc.create_entity(
                        EntityType.MERCHANT, merchant, event.bank_id, {"category": merchant}
                    )
                    graph_engine.register_entity(merch_entity)

                    # Add relationship: Customer TRANSACTS_WITH Merchant
                    rel = entity_svc.add_relationship(
                        cust_entity.id,
                        merch_entity.id,
                        RelationshipType.TRANSACTS_WITH,
                        confidence=1.0,
                    )
                    graph_engine.add_relationship(rel)

                # 3. Register device entity if present
                device = payload.get("device_type")
                if device:
                    dev_entity = entity_svc.create_entity(
                        EntityType.DEVICE, device, event.bank_id, {"device_type": device}
                    )
                    graph_engine.register_entity(dev_entity)

                    # Add relationship: Customer USES Device
                    rel = entity_svc.add_relationship(
                        cust_entity.id, dev_entity.id, RelationshipType.USES, confidence=1.0
                    )
                    graph_engine.add_relationship(rel)

        elif event.event_type == "alert":
            # Generate and store a new alert
            severity_str = payload.get("severity", "medium").upper()
            severity = getattr(AlertSeverity, severity_str, AlertSeverity.MEDIUM)

            # Find a customer entity from the same bank to associate with
            cust_id = None
            entities = entity_svc.get_entities(
                entity_type=EntityType.CUSTOMER, bank_id=event.bank_id
            )
            if entities:
                cust_entity = entities[0]
                cust_id = cust_entity.id
                entity_svc.increment_alert_count(cust_entity.id)
                # Elevate risk level
                if severity == AlertSeverity.CRITICAL:
                    entity_svc.update_risk_level(cust_entity.id, RiskLevel.CRITICAL)
                elif severity == AlertSeverity.HIGH:
                    entity_svc.update_risk_level(cust_entity.id, RiskLevel.HIGH)
                else:
                    entity_svc.update_risk_level(cust_entity.id, RiskLevel.MEDIUM)

            alert = Alert(
                bank_id=event.bank_id,
                transaction_id=str(uuid.uuid4())[:8],
                risk_score=payload.get("confidence", 0.5) * 1000,
                severity=severity,
                status=AlertStatus.NEW,
                reason_codes=payload.get("reason_codes", ["SUSP-PATTERN"]),
                confidence=payload.get("confidence", 0.5),
                involved_entity_ids=[cust_id] if cust_id else [],
                model_confidence=payload.get("confidence", 0.5),
                top_features=[{"feature": "velocity", "value": 0.85}],
                risk_factors=[payload.get("description", "Suspicious pattern")],
            )
            alert_svc._alert_store[alert.id] = alert

            # Automatically create a Case for High/Critical alerts
            if alert.is_actionable:
                priority = (
                    CasePriority.P1_HIGH
                    if severity == AlertSeverity.CRITICAL
                    else CasePriority.P2_HIGH
                )
                case_svc.create_case(
                    title=f"Potential Fraud Ring: {payload.get('description', 'Suspicious activity')}",
                    priority=priority,
                    alert_ids=[alert.id],
                )

        elif event.event_type == "intelligence":
            # Share intelligence across banks
            privacy_hash = payload.get("shared_device_hash", str(uuid.uuid4())[:8])

            intel = SharedIntelligence(
                source_bank_id=event.bank_id,
                intelligence_type=IntelligenceType.FRAUD_ALERT,
                privacy_hash=privacy_hash,
                risk_indicator=payload.get("combined_confidence", 0.8),
                description=payload.get("description", "Cross-institution match"),
                entity_type=EntityType.CUSTOMER,
                related_alert_count=payload.get("cards_identified", 2),
            )
            alert_svc._intelligence_store.append(intel)

            # Link matching entities across institutions in the graph
            all_entities = list(entity_svc._entities.values())
            customers = [e for e in all_entities if e.entity_type == EntityType.CUSTOMER]
            if len(customers) >= 2:
                for i in range(len(customers) - 1):
                    rel = entity_svc.add_relationship(
                        customers[i].id,
                        customers[i + 1].id,
                        RelationshipType.SHARES_DEVICE,
                        confidence=payload.get("combined_confidence", 0.9),
                    )
                    graph_engine.add_relationship(rel)

        elif event.event_type == "escalation":
            # Find open cases and escalate them to critical
            for case in list(case_svc._cases.values()):
                if case.is_open:
                    case.priority = CasePriority.P1_HIGH
                    case.timeline.append(
                        CaseEvent(
                            event_type="status_changed",
                            description=f"Escalated to High: {payload.get('reason', 'Cross-institution intelligence')}",
                            actor="system",
                        )
                    )
