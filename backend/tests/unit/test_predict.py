"""Unit and integration tests for the real-time Serving Prediction REST API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_predict_low_risk_transaction() -> None:
    """Verify that a normal low-risk transaction returns low scores and no alert."""
    payload = {
        "transaction_amount": 25.50,
        "merchant_category": "grocery",
        "country_code": "US",
        "device_type": "web_browser",
        "velocity": 1.0,
        "hour_of_day": 14,
        "merchant_risk_score": 0.03,
        "customer_history_score": 0.98,
        "chargeback_count": 0,
        "account_age_days": 500,
        "bank_id": "bank_a",
    }

    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "fraud_probability" in data
    assert "risk_score" in data
    assert "is_fraud_suspected" in data
    assert "risk_level" in data
    assert "breakdown" in data

    assert data["is_fraud_suspected"] is False
    assert data["risk_score"] < 600.0
    assert data["alert_details"] is None


def test_predict_high_risk_transaction() -> None:
    """Verify that a high-risk transaction flags fraud and registers an alert."""
    payload = {
        "transaction_amount": 4900.0,
        "merchant_category": "crypto",
        "country_code": "NG",
        "device_type": "mobile_app",
        "velocity": 18.0,
        "hour_of_day": 3,
        "merchant_risk_score": 0.85,
        "customer_history_score": 0.10,
        "chargeback_count": 5,
        "account_age_days": 5,
        "bank_id": "bank_b",
    }

    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["is_fraud_suspected"] is True
    assert data["risk_score"] >= 600.0
    assert data["alert_details"] is not None

    alert = data["alert_details"]
    assert "alert_id" in alert
    assert alert["severity"] in ["medium", "high", "critical"]
    assert len(alert["reason_codes"]) > 0
    assert "explanation" in alert
    assert len(alert["top_features"]) > 0


def test_predict_validation_errors() -> None:
    """Verify that invalid inputs are rejected with validation status code 422."""
    # Test invalid amount
    payload_invalid_amt = {
        "transaction_amount": -100.0,
        "merchant_category": "grocery",
    }
    response = client.post("/api/v1/predict", json=payload_invalid_amt)
    assert response.status_code == 422

    # Test invalid hour_of_day
    payload_invalid_hour = {
        "transaction_amount": 10.0,
        "hour_of_day": 25,
    }
    response = client.post("/api/v1/predict", json=payload_invalid_hour)
    assert response.status_code == 422
