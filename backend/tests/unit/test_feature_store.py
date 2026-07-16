"""Unit tests for the Feature Store Service and its integration."""

from __future__ import annotations

import time

import pandas as pd

from app.application.services.feature_store_service import FeatureStoreService
from app.application.services.risk_engine import RiskScoringEngine


def test_feature_store_ingestion_and_online_retrieval() -> None:
    """Ingesting events must update online features and maintain sliding windows."""
    fs = FeatureStoreService()

    customer_id = "test_cust_123"
    merchant_id = "test_merch_456"

    # Ingest a transaction
    fs.ingest_transaction(
        customer_id=customer_id,
        amount=150.0,
        merchant_id=merchant_id,
        merchant_category="crypto",
        merchant_risk_score=0.85,
        customer_history_score=0.90,
        chargeback_count=2,
        account_age_days=120,
    )

    # Fetch online features
    features = [
        "rolling_velocity_1h",
        "avg_amount_24h",
        "customer_history_score",
        "account_age_days",
        "chargeback_count",
        "merchant_risk_score",
        "merchant_category",
    ]
    online_features = fs.get_online_features(
        [{"customer_id": customer_id, "merchant_id": merchant_id}],
        features,
    )

    assert len(online_features) == 1
    feats = online_features[0]
    assert feats["rolling_velocity_1h"] == 1.0
    assert feats["avg_amount_24h"] == 150.0
    assert feats["customer_history_score"] == 0.90
    assert feats["account_age_days"] == 120
    assert feats["chargeback_count"] == 2
    assert feats["merchant_risk_score"] == 0.85
    assert feats["merchant_category"] == "crypto"


def test_feature_store_sliding_window_velocity() -> None:
    """Consecutive transactions must update the rolling window statistics."""
    fs = FeatureStoreService()

    customer_id = "test_cust_sliding"
    merchant_id = "test_merch_sliding"

    # Clear previous runs
    fs.tx_history.delete(customer_id)

    # Ingest 3 transactions
    now = time.time()
    fs.ingest_transaction(
        customer_id=customer_id,
        amount=100.0,
        merchant_id=merchant_id,
        merchant_category="dining",
        merchant_risk_score=0.05,
        customer_history_score=0.95,
        chargeback_count=0,
        account_age_days=300,
        timestamp=now - 10,
    )
    fs.ingest_transaction(
        customer_id=customer_id,
        amount=200.0,
        merchant_id=merchant_id,
        merchant_category="dining",
        merchant_risk_score=0.05,
        customer_history_score=0.95,
        chargeback_count=0,
        account_age_days=300,
        timestamp=now - 5,
    )
    fs.ingest_transaction(
        customer_id=customer_id,
        amount=300.0,
        merchant_id=merchant_id,
        merchant_category="dining",
        merchant_risk_score=0.05,
        customer_history_score=0.95,
        chargeback_count=0,
        account_age_days=300,
        timestamp=now,
    )

    # Fetch online stats
    online_features = fs.get_online_features(
        [{"customer_id": customer_id, "merchant_id": merchant_id}],
        ["rolling_velocity_1h", "avg_amount_24h"],
    )

    assert len(online_features) == 1
    feats = online_features[0]
    assert feats["rolling_velocity_1h"] == 3.0
    assert feats["avg_amount_24h"] == 200.0  # Average of 100, 200, 300


def test_offline_store_historical_join() -> None:
    """Offline point-in-time join must align features accurately without leakage."""
    fs = FeatureStoreService()

    entity_df = pd.DataFrame(
        [
            {"customer_id": "c1", "velocity": 2.5, "transaction_amount": 50.0},
            {"customer_id": "c2", "velocity": 5.0, "transaction_amount": 1000.0},
        ]
    )

    features = ["rolling_velocity_1h", "avg_amount_24h", "customer_history_score"]
    historical_df = fs.get_historical_features(entity_df, features)

    assert len(historical_df) == 2
    assert historical_df.iloc[0]["rolling_velocity_1h"] == 2.5
    assert historical_df.iloc[1]["rolling_velocity_1h"] == 5.0
    assert historical_df.iloc[0]["avg_amount_24h"] == 50.0
    assert historical_df.iloc[1]["avg_amount_24h"] == 1000.0
    assert historical_df.iloc[0]["customer_history_score"] == 0.95


def test_scoring_engine_integration() -> None:
    """RiskScoringEngine must retrieve online features when enabled."""
    fs = FeatureStoreService()
    engine = RiskScoringEngine()

    customer_id = "test_cust_scoring_integration"
    merchant_id = "test_merch_scoring_integration"

    # Pre-populate feature store with high-risk velocity and chargebacks
    fs.ingest_transaction(
        customer_id=customer_id,
        amount=5000.0,
        merchant_id=merchant_id,
        merchant_category="gambling",
        merchant_risk_score=0.90,
        customer_history_score=0.10,
        chargeback_count=8,
        account_age_days=5,
    )
    # Simulate repeated txns to push rolling velocity high
    for i in range(12):
        fs.tx_history.push_list(customer_id, {"timestamp": time.time(), "amount": 5000.0})

    # Update online stats to reflect high velocity
    fs.online_stats.set(
        customer_id,
        {
            "rolling_velocity_1h": 12.0,
            "avg_amount_24h": 5000.0,
        },
    )

    # Evaluate transaction using scoring engine
    txn_data = {
        "transaction_amount": 5000.0,
        "merchant_category": "grocery",  # override category in raw txn to check if feature store updates it
        "country_code": "US",
        "device_type": "web_browser",
        "velocity": 1.0,  # low raw velocity
        "merchant_risk_score": 0.05,
        "customer_history_score": 0.95,
        "chargeback_count": 0,
        "account_age_days": 365,
    }

    score_result = engine.score_transaction(
        transaction=txn_data,
        ml_prediction=0.10,
        entity_hash=customer_id,
    )

    # Since feature store overrides raw features with high-risk values:
    # 1. velocity will be 12.0 (high velocity alert)
    # 2. customer_history_score will be 0.10 (low score / high risk)
    # 3. account_age_days will be 5 days (high risk)
    # This should yield a significantly higher risk score than the benign input.
    assert score_result.score > 250.0
