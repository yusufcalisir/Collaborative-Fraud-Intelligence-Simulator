"""Streaming Feature Store Service Engine."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.domain.data_validator import DataContractValidator
from app.infrastructure.feature_store.bloom_filter import BloomFilterDeduplicator
from app.infrastructure.feature_store.rolling_aggregators import RollingFeatureAggregator

if TYPE_CHECKING:
    from app.infrastructure.connectors.base_connector import NormalizedTransaction

logger = logging.getLogger(__name__)


class StreamingFeatureStore:
    """Real-Time Streaming Feature Store Engine.

    Maintains sliding-window behavioral aggregations and entity features
    across high-frequency payment streams.
    """

    def __init__(self) -> None:
        self.validator = DataContractValidator()
        self.deduplicator = BloomFilterDeduplicator()
        self.aggregator = RollingFeatureAggregator()
        # In-memory feature vectors store per transaction_id & account_id
        self._tx_feature_store: dict[str, dict[str, Any]] = {}
        self._account_latest_features: dict[str, dict[str, Any]] = {}

    def ingest_transaction(self, tx: NormalizedTransaction) -> dict[str, Any]:
        """Executes full ingestion pipeline sequence:

        1. Schema Validation via Data Contracts
        2. Transaction Deduplication via Bloom Filter
        3. Feature Extraction & Rolling Aggregations
        4. Persistence to Feature Store
        """
        # Step 1: Validate Schema Data Contract
        self.validator.validate_transaction(tx)

        # Step 2: Deduplication Check
        if self.deduplicator.contains_or_add(tx.transaction_id):
            logger.warning(
                "Duplicate transaction ID detected: %s. Skipping duplicate processing.",
                tx.transaction_id,
            )
            return self._tx_feature_store.get(tx.transaction_id, {"status": "DUPLICATE"})

        # Step 3: Extract Rolling Features
        features = self.aggregator.compute_features(tx)

        # Step 4: Assemble Payload
        feature_vector = {
            "transaction_id": tx.transaction_id,
            "account_id": tx.account_id,
            "timestamp": tx.timestamp.isoformat(),
            "amount": tx.amount,
            "features": features,
            "status": "PROCESSED",
        }

        # Step 5: Persist Feature Vector
        self._tx_feature_store[tx.transaction_id] = feature_vector
        self._account_latest_features[tx.account_id] = feature_vector

        logger.debug("Successfully ingested and extracted features for tx: %s", tx.transaction_id)
        return feature_vector

    def get_feature_vector(self, transaction_id: str) -> dict[str, Any] | None:
        """Retrieves stored feature vector by transaction ID."""
        return self._tx_feature_store.get(transaction_id)

    def get_latest_account_features(self, account_id: str) -> dict[str, Any] | None:
        """Retrieves latest feature vector for an account."""
        return self._account_latest_features.get(account_id)

    def clear(self) -> None:
        """Clears stored feature vectors and deduplication history."""
        self._tx_feature_store.clear()
        self._account_latest_features.clear()
        self.deduplicator = BloomFilterDeduplicator()
        self.aggregator = RollingFeatureAggregator()
