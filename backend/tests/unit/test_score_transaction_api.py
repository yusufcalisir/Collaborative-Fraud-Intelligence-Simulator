"""Unit tests for Low-Latency Real-Time Risk Decision API (POST /v1/transactions/score)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_score_transaction_api_schema_compliance() -> None:
    """Verifies POST /v1/transactions/score returns expected JSON schema and response headers."""
    payload = {
        "transaction_id": "tx_8941203",
        "account_id": "acc_de_91823",
        "amount": 12500.00,
        "currency": "EUR",
        "merchant_id": "merchant_9912",
        "country": "EE",
        "device_id": "dev_fp_4491a",
    }

    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    assert "risk_score" in data
    assert 0 <= data["risk_score"] <= 1000
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert data["decision"] in ("ALLOW", "REVIEW", "BLOCK")
    assert "model_version" in data
    assert isinstance(data["explanations"], list)
    assert isinstance(data["related_entities"], list)
    assert "latency_ms" in data
    assert data["latency_ms"] >= 0.0


def test_score_transaction_api_high_risk_crypto() -> None:
    """Verifies high-risk crypto transaction triggers HIGH risk_level and REVIEW/BLOCK decision."""
    payload = {
        "transaction_id": "tx_crypto_999",
        "account_id": "acc_suspect_1",
        "amount": 95000.00,
        "currency": "USD",
        "merchant_id": "crypto_exchange_binance",
        "country": "KP",
        "device_id": "dev_tor_node_88",
    }

    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["risk_score"] >= 100, (
        f"Expected elevated risk_score >= 100 for crypto/KP transaction, got {data['risk_score']}"
    )
    assert data["decision"] in ("ALLOW", "REVIEW", "BLOCK")
    assert len(data["explanations"]) >= 1
    assert any(item["feature"] == "merchant_velocity_1h" for item in data["explanations"])


def test_score_transaction_api_low_risk_grocery() -> None:
    """Verifies normal low-amount grocery transaction returns LOW risk_level and ALLOW decision."""
    payload = {
        "transaction_id": "tx_normal_001",
        "account_id": "acc_legit_55",
        "amount": 42.50,
        "currency": "EUR",
        "merchant_id": "rewe_supermarket",
        "country": "DE",
        "device_id": "dev_ios_phone_12",
    }

    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["risk_score"] < 700
    assert data["decision"] in ("ALLOW", "REVIEW")
