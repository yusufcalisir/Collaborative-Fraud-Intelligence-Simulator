# ruff: noqa: UP042
"""Developer Webhook Notification Service."""

from __future__ import annotations

import hmac
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Event types available for developer webhook subscriptions."""

    ALERT_CREATED = "ALERT_CREATED"
    CASE_RESOLVED = "CASE_RESOLVED"
    MODEL_PROMOTED = "MODEL_PROMOTED"
    DRIFT_DETECTED = "DRIFT_DETECTED"


@dataclass
class WebhookSubscription:
    """Dataclass representing a developer webhook subscription."""

    subscription_id: str
    tenant_id: str
    target_url: str
    secret_key: str
    events: list[WebhookEventType]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class WebhookDeliveryPayload:
    """Dataclass tracking an outgoing signed webhook payload."""

    event_id: str
    event_type: WebhookEventType
    payload: dict[str, Any]
    signature: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class WebhookService:
    """Manages developer webhook subscriptions and HMAC-SHA256 payload signing."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[WebhookSubscription]] = {}

    def register_subscription(
        self,
        tenant_id: str,
        target_url: str,
        events: list[WebhookEventType],
    ) -> WebhookSubscription:
        """Registers a developer webhook subscription endpoint and generates a secret key."""
        subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
        secret_key = f"whsec_{uuid.uuid4().hex[:16]}"

        subscription = WebhookSubscription(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            target_url=target_url,
            secret_key=secret_key,
            events=events,
        )

        if tenant_id not in self._subscriptions:
            self._subscriptions[tenant_id] = []
        self._subscriptions[tenant_id].append(subscription)

        logger.info(
            "Registered webhook subscription '%s' for tenant '%s' (Target: %s, Events: %s)",
            subscription_id,
            tenant_id,
            target_url,
            [e.value for e in events],
        )
        return subscription

    def compute_hmac_signature(self, secret_key: str, payload_bytes: bytes) -> str:
        """Computes HMAC-SHA256 signature string for payload authentication."""
        signature = hmac.new(
            secret_key.encode("utf-8"),
            payload_bytes,
            digestmod="sha256",
        ).hexdigest()
        return f"sha256={signature}"

    def dispatch_event(
        self,
        tenant_id: str,
        event_type: WebhookEventType,
        payload: dict[str, Any],
    ) -> list[WebhookDeliveryPayload]:
        """Signs and dispatches event notification payloads to matching subscribers."""
        tenant_subs = self._subscriptions.get(tenant_id, [])
        delivered: list[WebhookDeliveryPayload] = []

        payload_json_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

        for sub in tenant_subs:
            if event_type in sub.events:
                event_id = f"evt_{uuid.uuid4().hex[:8]}"
                signature = self.compute_hmac_signature(
                    secret_key=sub.secret_key,
                    payload_bytes=payload_json_bytes,
                )

                delivery = WebhookDeliveryPayload(
                    event_id=event_id,
                    event_type=event_type,
                    payload=payload,
                    signature=signature,
                )
                delivered.append(delivery)

                logger.info(
                    "Dispatched webhook event %s (%s) to %s (Signature: %s)",
                    event_id,
                    event_type.value,
                    sub.target_url,
                    signature[:16],
                )

        return delivered

    def get_subscriptions(self, tenant_id: str) -> list[WebhookSubscription]:
        """Retrieves tenant active webhook subscriptions."""
        return list(self._subscriptions.get(tenant_id, []))
