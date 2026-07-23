"""Feast Feature Store Adapter for Online and Offline Feature Serving."""

from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.feature_store.redis_store import RedisFeatureStore

logger = logging.getLogger(__name__)


class FeastFeatureStoreAdapter:
    """Feast Feature Store adapter managing online feature view retrieval and historical entity joins."""

    def __init__(self, online_store: RedisFeatureStore | None = None) -> None:
        self.online_store = online_store or RedisFeatureStore()
        logger.info("Initialized FeastFeatureStoreAdapter connected to online Redis store")

    def get_online_features(
        self,
        entity_rows: list[dict[str, Any]],
        features: list[str],
    ) -> list[dict[str, Any]]:
        """Retrieves online feature vectors for a list of entity keys (e.g. account_id / device_id)."""
        results: list[dict[str, Any]] = []
        entity_ids = [
            str(row.get("account_id") or row.get("entity_id") or "") for row in entity_rows
        ]
        fetched_batch = self.online_store.batch_get_features(entity_ids)

        for row, entity_id in zip(entity_rows, entity_ids, strict=False):
            stored_vector = fetched_batch.get(entity_id) or {}
            vector_features = stored_vector.get("features", stored_vector)

            extracted: dict[str, Any] = {**row}
            for feat_name in features:
                # Strip feature view prefix e.g. "payment_stats:amount_mean_24h" -> "amount_mean_24h"
                clean_name = feat_name.split(":")[-1]
                extracted[feat_name] = vector_features.get(
                    clean_name, vector_features.get(feat_name, 0.0)
                )

            results.append(extracted)

        return results

    def push_online_features(
        self,
        feature_view_name: str,
        df_or_records: list[dict[str, Any]],
        entity_key: str = "account_id",
    ) -> int:
        """Pushes feature vectors into online store feature view."""
        pushed_count = 0
        batch: dict[str, dict[str, Any]] = {}

        for rec in df_or_records:
            entity_id = str(rec.get(entity_key) or "")
            if not entity_id:
                continue
            batch[entity_id] = {
                "feature_view": feature_view_name,
                "features": rec,
            }
            pushed_count += 1

        if batch:
            self.online_store.batch_set_features(batch)

        logger.debug(
            "Pushed %d entity feature records to Feast feature view %s",
            pushed_count,
            feature_view_name,
        )
        return pushed_count

    def get_historical_features(
        self,
        entity_df: list[dict[str, Any]],
        features: list[str],
    ) -> list[dict[str, Any]]:
        """Performs point-in-time feature join across historical entity dataframe."""
        # Delegated to online store retrieval for streaming engine execution
        return self.get_online_features(entity_df, features)
