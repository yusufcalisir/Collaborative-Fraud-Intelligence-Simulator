# ruff: noqa: E402
"""Automated Unit Test Suite for Low-Latency Real-Time Inference Gateway & Fallback Engine."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.inference_fallback import (
    InferenceDecision,
    InferenceFallbackEngine,
)
from app.presentation.routers.realtime_inference import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_heuristic_fallback_engine_evaluations() -> None:
    """Test deterministic heuristic fallback decisions and risk score bounds."""
    engine = InferenceFallbackEngine()

    # 1. Low risk general retail transaction -> ALLOW
    dec_low, score_low, _ = engine.evaluate_heuristic_fallback(
        amount=100.0,
        velocity_1h=1,
        merchant_category="general_retail",
    )
    assert dec_low == InferenceDecision.ALLOW
    assert score_low < 0.35

    # 2. Medium risk elevated velocity -> REVIEW
    dec_med, score_med, _ = engine.evaluate_heuristic_fallback(
        amount=15000.0,
        velocity_1h=6,
        merchant_category="general_retail",
    )
    assert dec_med in (InferenceDecision.REVIEW, InferenceDecision.BLOCK)
    assert score_med >= 0.30

    # 3. High risk merchant + velocity spike -> BLOCK
    dec_high, score_high, expl_high = engine.evaluate_heuristic_fallback(
        amount=75000.0,
        velocity_1h=12,
        merchant_category="crypto_exchange",
    )
    assert dec_high == InferenceDecision.BLOCK
    assert score_high >= 0.70
    assert "High-risk merchant" in expl_high


def test_realtime_inference_api_endpoint_scoring() -> None:
    """Test POST /v1/inference/score endpoint for low-latency ML scoring."""
    payload = {
        "transaction_id": "tx_test_9988",
        "amount": 450.0,
        "currency": "USD",
        "source_account": "acc_src_1",
        "target_account": "acc_dst_2",
        "merchant_category": "electronics",
        "velocity_1h": 2,
    }

    response = client.post("/v1/inference/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["transaction_id"] == "tx_test_9988"
    assert data["decision"] == "ALLOW"
    assert data["evaluated_by"] == "ML_MODEL"
    assert data["latency_ms"] < 100.0  # SLA <100ms check


def test_realtime_inference_api_endpoint_fallback_triggering() -> None:
    """Test fallback triggering when model execution encounters an error/timeout."""
    payload = {
        "transaction_id": "tx_test_fallback_77",
        "amount": 60000.0,
        "currency": "USD",
        "source_account": "acc_src_1",
        "target_account": "acc_dst_2",
        "merchant_category": "crypto_exchange",
        "velocity_1h": 15,
        "force_fallback": True,  # Forces fallback branch
    }

    response = client.post("/v1/inference/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["transaction_id"] == "tx_test_fallback_77"
    assert data["decision"] == "BLOCK"
    assert data["evaluated_by"] == "HEURISTIC_FALLBACK"
    assert data["latency_ms"] < 100.0
