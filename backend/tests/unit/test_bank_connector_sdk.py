# ruff: noqa: E402
"""Unit test suite for Bank Connector SDK adapters and client daemon."""

from __future__ import annotations

import os
import sys
from typing import Any

# Add sdk/python to path for testing importability
sdk_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "sdk", "python")
)
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from cfi_connector_sdk import (
    BaseEntityAdapter,
    BaseFeatureAdapter,
    BaseTransactionAdapter,
    LocalFLClient,
    NormalizedTransaction,
)


class SampleBankTransactionAdapter(BaseTransactionAdapter):
    """Concrete sample transaction adapter for testing."""

    def parse_native_payload(self, payload: dict[str, Any]) -> NormalizedTransaction:
        return NormalizedTransaction(
            transaction_id=str(payload["tx_id"]),
            account_id=str(payload["debtor"]),
            counterparty_account_id=str(payload["creditor"]),
            amount=float(payload["val"]),
            currency=str(payload.get("ccy", "USD")),
            channel_type=str(payload.get("channel", "ONLINE")),
        )


def test_transaction_adapter_parsing_and_validation() -> None:
    """Test custom transaction adapter payload parsing and validation rules."""
    adapter = SampleBankTransactionAdapter()
    native_payload = {
        "tx_id": "TX-10092",
        "debtor": "ACC-001",
        "creditor": "ACC-002",
        "val": 1500.50,
        "ccy": "EUR",
        "channel": "MOBILE",
    }

    tx = adapter.parse_native_payload(native_payload)

    assert isinstance(tx, NormalizedTransaction)
    assert tx.transaction_id == "TX-10092"
    assert tx.account_id == "ACC-001"
    assert tx.counterparty_account_id == "ACC-002"
    assert tx.amount == 1500.50
    assert tx.currency == "EUR"
    assert tx.channel_type == "MOBILE"
    assert adapter.validate_schema(tx) is True


def test_entity_adapter_hmac_privacy_masking() -> None:
    """Test entity adapter HMAC-SHA256 privacy hashing."""
    adapter = BaseEntityAdapter(bank_salt="test_bank_salt_123")
    raw_id = "ACC-998877"

    hashed_1 = adapter.hash_customer_id(raw_id)
    hashed_2 = adapter.hash_customer_id(raw_id)

    assert len(hashed_1) == 64
    assert hashed_1 == hashed_2  # Deterministic HMAC
    assert hashed_1 != raw_id

    # Test payload masking
    payload = {"customer_id": "ACC-998877", "account_number": "ACC-998877", "name": "John"}
    masked = adapter.mask_entity_payload(payload)

    assert masked["customer_id"] == hashed_1
    assert masked["account_number"] == hashed_1
    assert masked["name"] == "John"


def test_feature_adapter_velocity_calculation() -> None:
    """Test velocity feature extraction calculations."""
    feature_adapter = BaseFeatureAdapter()
    adapter = SampleBankTransactionAdapter()

    tx_current = adapter.parse_native_payload(
        {"tx_id": "TX-03", "debtor": "A", "creditor": "B", "val": 200.0}
    )
    tx_past_1 = adapter.parse_native_payload(
        {"tx_id": "TX-01", "debtor": "A", "creditor": "B", "val": 100.0}
    )
    tx_past_2 = adapter.parse_native_payload(
        {"tx_id": "TX-02", "debtor": "A", "creditor": "B", "val": 100.0}
    )

    history = [tx_past_1, tx_past_2]
    feats = feature_adapter.extract_velocity_features(tx_current, history)

    assert feats["amount"] == 200.0
    assert feats["tx_count_1h"] == 2.0
    assert feats["tx_count_24h"] == 2.0
    assert feats["amount_sum_24h"] == 200.0
    assert feats["amount_ratio_24h"] == 2.0  # 200 / (200 / 2) = 2.0


def test_local_fl_client_connection_and_submission() -> None:
    """Test local FL client daemon connection and weight submission."""
    client = LocalFLClient(bank_id="bank-a", coordinator_url="localhost:50051")
    assert not client.is_connected

    assert client.connect()
    assert client.is_connected

    res = client.submit_local_weights(
        round_id=1,
        weights={"w": [0.1, 0.2]},
        dp_epsilon=0.5,
        num_samples=500,
    )
    assert res["status"] == "ACCEPTED"
    assert res["bank_id"] == "bank-a"
    assert res["round_id"] == 1
    assert res["samples"] == 500
