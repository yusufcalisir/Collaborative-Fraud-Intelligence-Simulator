"""Unit tests for Enterprise Data Cleaning, Validation & Schema Normalization (Section 11.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from app.domain.data_validator import DataContractValidator, DataValidationError
from app.infrastructure.connectors.base_connector import NormalizedTransaction
from app.infrastructure.connectors.parquet_connector import ParquetConnector

if TYPE_CHECKING:
    from pathlib import Path


def test_iban_iso13616_checksum_validation() -> None:
    """Verifies ISO 13616 IBAN mod-97 checksum validation."""
    valid_german_iban = "DE89370400440532013000"
    valid_french_iban = "FR1420041010050500013M02606"
    invalid_iban = "DE89370400440532013001"

    assert DataContractValidator.validate_iban(valid_german_iban) is True
    assert DataContractValidator.validate_iban(valid_french_iban) is True
    assert DataContractValidator.validate_iban(invalid_iban) is False
    assert DataContractValidator.validate_iban("INVALID_FORMAT_123") is False


def test_currency_iso4217_and_timestamp_bounds_validation() -> None:
    """Verifies ISO 4217 currency checks and timestamp bounds validation."""
    valid_tx = NormalizedTransaction(
        transaction_id="tx_100",
        account_id="ACC_001",
        counterparty_account_id="ACC_002",
        amount=150.0,
        currency="EUR",
        timestamp=datetime.now(UTC),
        merchant_category_code="6012",
        origin_country="DE",
        destination_country="FR",
    )
    assert DataContractValidator.validate_transaction(valid_tx) is True

    future_tx = NormalizedTransaction(
        transaction_id="tx_future",
        account_id="ACC_001",
        counterparty_account_id="ACC_002",
        amount=150.0,
        currency="USD",
        timestamp=datetime.now(UTC) + timedelta(days=2),
        merchant_category_code="6012",
        origin_country="US",
        destination_country="GB",
    )
    with pytest.raises(DataValidationError, match="timestamp is in the future"):
        DataContractValidator.validate_transaction(future_tx)


def test_pyarrow_parquet_zero_copy_batch_ingestion(tmp_path: Path) -> None:
    """Verifies PyArrow zero-copy batch streaming on Parquet dataset files."""
    df = pd.DataFrame(
        [
            {
                "transaction_id": f"batch_tx_{i}",
                "account_id": f"DEBTOR_{i}",
                "counterparty_account_id": f"CREDITOR_{i}",
                "amount": 100.0 + i,
                "currency": "EUR",
                "merchant_category_code": "6012",
                "origin_country": "DE",
                "destination_country": "FR",
            }
            for i in range(25)
        ]
    )

    parquet_file = tmp_path / "test_dataset.parquet"

    df.to_parquet(parquet_file)

    connector = ParquetConnector()
    batch_generator = connector.read_parquet_batches(parquet_file, batch_size=10)

    batches = list(batch_generator)
    assert len(batches) == 3
    assert len(batches[0]) == 10
    assert len(batches[1]) == 10
    assert len(batches[2]) == 5
    assert batches[0][0].transaction_id == "batch_tx_0"
