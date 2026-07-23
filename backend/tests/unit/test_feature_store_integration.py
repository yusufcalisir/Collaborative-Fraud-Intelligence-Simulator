"""Unit tests for Real-Time Streaming Feature Store Integration (Section 11.3)."""

from __future__ import annotations

import time

from app.infrastructure.feature_store.feast_store import FeastFeatureStoreAdapter
from app.infrastructure.feature_store.redis_store import RedisFeatureStore


def test_redis_store_connection_pooling_and_pipeline_batch() -> None:
    """Verifies RedisFeatureStore pipeline batch SET and GET operations."""
    store = RedisFeatureStore()

    batch_data = {
        "ACC_001": {"tx_count_24h": 5, "amount_sum_24h": 1200.0, "risk_score": 0.12},
        "ACC_002": {"tx_count_24h": 22, "amount_sum_24h": 8900.0, "risk_score": 0.85},
    }

    store.batch_set_features(batch_data)

    retrieved = store.batch_get_features(["ACC_001", "ACC_002", "ACC_NONEXISTENT"])
    assert retrieved["ACC_001"] == batch_data["ACC_001"]
    assert retrieved["ACC_002"] == batch_data["ACC_002"]
    assert retrieved["ACC_NONEXISTENT"] is None


def test_feast_feature_store_adapter_online_retrieval() -> None:
    """Verifies FeastFeatureStoreAdapter push_online_features and get_online_features."""
    redis_store = RedisFeatureStore()
    feast_adapter = FeastFeatureStoreAdapter(online_store=redis_store)

    records = [
        {"account_id": "BANK_ACC_101", "amount_mean_7d": 450.0, "velocity_1h": 3},
        {"account_id": "BANK_ACC_102", "amount_mean_7d": 12000.0, "velocity_1h": 18},
    ]

    pushed_count = feast_adapter.push_online_features(
        feature_view_name="account_fraud_features",
        df_or_records=records,
        entity_key="account_id",
    )
    assert pushed_count == 2

    entity_rows = [{"account_id": "BANK_ACC_101"}, {"account_id": "BANK_ACC_102"}]
    requested_features = [
        "account_fraud_features:amount_mean_7d",
        "account_fraud_features:velocity_1h",
    ]

    results = feast_adapter.get_online_features(entity_rows, requested_features)
    assert len(results) == 2
    assert results[0]["account_fraud_features:amount_mean_7d"] == 450.0
    assert results[1]["account_fraud_features:velocity_1h"] == 18


def test_redis_feature_key_ttl_expiration() -> None:
    """Verifies RedisFeatureStore TTL key expiration."""
    store = RedisFeatureStore()
    store.set_feature_vector("TTL_ACC_999", {"temp_feat": 1.0}, ttl_seconds=1)

    cached_before = store.get_feature_vector("TTL_ACC_999")
    assert cached_before == {"temp_feat": 1.0}

    time.sleep(1.1)
    cached_after = store.get_feature_vector("TTL_ACC_999")
    assert cached_after is None
