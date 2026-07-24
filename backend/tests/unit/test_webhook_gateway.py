# ruff: noqa: E402
"""Automated Unit Test Suite for Public Product API & Developer Webhooks Gateway."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.services.webhook_service import (
    WebhookService,
)
from app.presentation.routers.webhook_gateway import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_webhook_subscription_registration() -> None:
    """Test registering a new developer webhook subscription via REST API."""
    payload = {
        "tenant_id": "bank_alpha",
        "target_url": "https://api.bank-alpha.com/webhooks/cfi",
        "events": ["ALERT_CREATED", "CASE_RESOLVED"],
    }

    response = client.post("/v1/webhooks/subscriptions", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "bank_alpha"
    assert data["target_url"] == "https://api.bank-alpha.com/webhooks/cfi"
    assert data["subscription_id"].startswith("sub_")
    assert data["secret_key"].startswith("whsec_")
    assert len(data["events"]) == 2


def test_hmac_sha256_payload_signature_generation() -> None:
    """Test HMAC-SHA256 signature computation and payload verification."""
    service = WebhookService()
    secret = "whsec_test_secret_key_123"
    body = b'{"event":"ALERT_CREATED","id":"123"}'

    signature = service.compute_hmac_signature(secret, body)
    assert signature.startswith("sha256=")
    assert len(signature) == 7 + 64  # sha256= + 64 hex characters


def test_webhook_event_dispatching_and_signing() -> None:
    """Test dispatching signed webhook events to registered tenant subscribers."""
    # 1. Register subscription via API endpoint
    reg_resp = client.post(
        "/v1/webhooks/subscriptions",
        json={
            "tenant_id": "bank_beta",
            "target_url": "https://api.bank-beta.com/webhooks",
            "events": ["MODEL_PROMOTED"],
        },
    )
    assert reg_resp.status_code == 200

    # 2. Test API test-dispatch endpoint
    resp = client.post(
        "/v1/webhooks/test-dispatch",
        params={"tenant_id": "bank_beta", "event_type": "MODEL_PROMOTED"},
    )
    assert resp.status_code == 200
    assert resp.json()["dispatched_count"] >= 1
    assert resp.json()["sample_signature"].startswith("sha256=")
