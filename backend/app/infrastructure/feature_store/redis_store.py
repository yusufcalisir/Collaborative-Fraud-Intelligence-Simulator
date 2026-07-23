"""Production Redis Online Feature Store Engine."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RedisFeatureStore:
    """Production Redis online feature store with connection pooling and pipeline batching."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "cfi:features:",
        default_ttl_seconds: int = 86400,
    ) -> None:
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl_seconds = default_ttl_seconds
        self._in_memory_store: dict[str, tuple[str, float | None]] = {}
        self._client: Any = None
        self._init_redis_client()

    def _init_redis_client(self) -> None:
        """Attempts to initialize Redis client pool or falls back to internal buffer."""
        try:
            import redis

            pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                decode_responses=True,
            )
            client = redis.Redis(connection_pool=pool)
            client.ping()
            self._client = client
            logger.info("Connected to production Redis cluster at %s", self.redis_url)
        except Exception as err:
            logger.info(
                "Redis cluster unavailable at %s (%s) -> using fallback memory cache",
                self.redis_url,
                err,
            )
            self._client = None

    def _format_key(self, entity_id: str) -> str:
        return f"{self.key_prefix}{entity_id}"

    def set_feature_vector(
        self,
        entity_id: str,
        features: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        """Stores feature vector for an entity with TTL key expiration."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        key = self._format_key(entity_id)
        payload = json.dumps(features)

        if self._client is not None:
            try:
                self._client.set(key, payload, ex=ttl)
                return True
            except Exception as err:
                logger.warning("Redis SET error: %s", err)

        expiry_time = time.time() + ttl if ttl > 0 else None
        self._in_memory_store[key] = (payload, expiry_time)
        return True

    def get_feature_vector(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieves stored feature vector for an entity."""
        key = self._format_key(entity_id)

        if self._client is not None:
            try:
                data = self._client.get(key)
                return json.loads(data) if data else None
            except Exception as err:
                logger.warning("Redis GET error: %s", err)

        if key in self._in_memory_store:
            payload, expiry_time = self._in_memory_store[key]
            if expiry_time is not None and time.time() > expiry_time:
                del self._in_memory_store[key]
                return None
            return json.loads(payload)

        return None

    def batch_set_features(
        self,
        entity_features: dict[str, dict[str, Any]],
        ttl_seconds: int | None = None,
    ) -> bool:
        """Executes pipeline batch SET operation across multiple entities."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

        if self._client is not None:
            try:
                pipe = self._client.pipeline()
                for entity_id, features in entity_features.items():
                    key = self._format_key(entity_id)
                    pipe.set(key, json.dumps(features), ex=ttl)
                pipe.execute()
                return True
            except Exception as err:
                logger.warning("Redis pipeline batch SET error: %s", err)

        for entity_id, features in entity_features.items():
            self.set_feature_vector(entity_id, features, ttl_seconds=ttl)
        return True

    def batch_get_features(self, entity_ids: list[str]) -> dict[str, dict[str, Any] | None]:
        """Executes pipeline batch GET operation for a list of entity IDs."""
        keys = [self._format_key(eid) for eid in entity_ids]
        results: dict[str, dict[str, Any] | None] = {}

        if self._client is not None:
            try:
                pipe = self._client.pipeline()
                for k in keys:
                    pipe.get(k)
                raw_values = pipe.execute()
                for entity_id, raw_val in zip(entity_ids, raw_values, strict=False):
                    results[entity_id] = json.loads(raw_val) if raw_val else None
                return results
            except Exception as err:
                logger.warning("Redis pipeline batch GET error: %s", err)

        for entity_id in entity_ids:
            results[entity_id] = self.get_feature_vector(entity_id)
        return results

    def clear(self) -> None:
        """Flushes stored keys."""
        if self._client is not None:
            try:
                self._client.flushdb()
            except Exception as err:
                logger.warning("Redis FLUSHDB error: %s", err)
        self._in_memory_store.clear()
