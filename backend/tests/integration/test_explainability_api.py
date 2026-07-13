"""Integration tests for explainability endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.application.services.alert_service import AlertIntelligenceService
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_alert_store() -> None:
    alert_service = AlertIntelligenceService()
    alert_service._alert_store.clear()


def test_explain_transaction_endpoint() -> None:
    alert_service = AlertIntelligenceService()

    # 1. Create a mock alert in storage
    sample_txn = [
        {
            "transaction_id": "txn_explain_test_999",
            "customer_id": "cust_123",
            "transaction_amount": 5000.0,
            "velocity": 2.0,
            "merchant_risk_score": 0.5,
            "merchant_category": "crypto",
            "country_code": "US",
            "account_age_days": 30,
            "chargeback_count": 1,
            "hour_of_day": 12,
            "device_type": "mobile_app",
        }
    ]
    alerts = alert_service.generate_alerts(
        bank_id="bank_a",
        transactions=sample_txn,
        predictions=[0.95],
    )
    assert len(alerts) == 1
    alert_id = alerts[0].id
    transaction_id = alerts[0].transaction_id

    # 2. Test explain by alert ID
    response_alert = client.get(f"/api/v1/alerts/{alert_id}/explain")
    assert response_alert.status_code == 200
    data_alert = response_alert.json()
    assert data_alert["alert_id"] == alert_id
    assert len(data_alert["top_features"]) > 0

    # 3. Test explain by transaction ID
    response_txn = client.get(f"/api/v1/explanation/{transaction_id}")
    assert response_txn.status_code == 200
    data_txn = response_txn.json()
    assert data_txn["alert_id"] == alert_id
    assert len(data_txn["top_features"]) > 0

    # 4. Test explain for nonexistent transaction ID returns 404
    response_nonexistent = client.get("/api/v1/explanation/nonexistent_txn_id")
    assert response_nonexistent.status_code == 404
