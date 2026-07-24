"""Developer Webhook Gateway Router."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.application.services.webhook_service import (
    WebhookEventType,
    WebhookService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks", tags=["Developer Webhooks"])


class WebhookSubscriptionRequest(BaseModel):
    """Schema for registering a developer webhook subscription."""

    tenant_id: str = Field(..., json_schema_extra={"example": "bank_alpha"})
    target_url: str = Field(
        ..., json_schema_extra={"example": "https://api.bank-alpha.com/webhooks/cfi"}
    )
    events: list[WebhookEventType] = Field(
        ...,
        json_schema_extra={"example": ["ALERT_CREATED", "CASE_RESOLVED"]},
    )


class WebhookSubscriptionResponse(BaseModel):
    """Schema for webhook registration response with secret key."""

    subscription_id: str
    tenant_id: str
    target_url: str
    secret_key: str
    events: list[WebhookEventType]


class WebhookTestDispatchResponse(BaseModel):
    """Schema for test dispatch payload execution."""

    dispatched_count: int
    event_type: str
    sample_signature: str | None = None


webhook_service = WebhookService()


@router.post("/subscriptions", response_model=WebhookSubscriptionResponse)
def register_webhook_subscription(
    payload: WebhookSubscriptionRequest,
) -> WebhookSubscriptionResponse:
    """Registers a developer webhook subscription endpoint for real-time notifications."""
    sub = webhook_service.register_subscription(
        tenant_id=payload.tenant_id,
        target_url=payload.target_url,
        events=payload.events,
    )
    return WebhookSubscriptionResponse(
        subscription_id=sub.subscription_id,
        tenant_id=sub.tenant_id,
        target_url=sub.target_url,
        secret_key=sub.secret_key,
        events=sub.events,
    )


@router.post("/test-dispatch", response_model=WebhookTestDispatchResponse)
def dispatch_test_webhook(
    tenant_id: str = "bank_alpha",
    event_type: WebhookEventType = WebhookEventType.ALERT_CREATED,
) -> WebhookTestDispatchResponse:
    """Dispatches a test event notification to registered tenant webhook endpoints."""
    payload = {
        "test": True,
        "message": "CFI Simulator Webhook Dispatch Test",
        "sample_tx": "tx_test_1001",
    }
    deliveries = webhook_service.dispatch_event(
        tenant_id=tenant_id,
        event_type=event_type,
        payload=payload,
    )
    sample_sig = deliveries[0].signature if deliveries else None

    return WebhookTestDispatchResponse(
        dispatched_count=len(deliveries),
        event_type=event_type.value,
        sample_signature=sample_sig,
    )
