"""Unit tests for ParquetConnector & Public Financial Dataset Pipeline (Section 8.1)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

from app.infrastructure.connectors.parquet_connector import ParquetConnector

# Add project root to sys.path for scripts module import
project_root = str(Path(__file__).resolve().parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.benchmark_prepare_datasets import (  # noqa: E402 # type: ignore # pyright: ignore[reportMissingImports]
    prepare_benchmark_datasets,
)


def test_parquet_connector_yields_transaction_events() -> None:
    """Verifies that ParquetConnector parses DataFrames into NormalizedTransaction streams."""
    df = pd.DataFrame(
        {
            "transaction_id": ["tx_001", "tx_002"],
            "account_id": ["acc_100", "acc_200"],
            "counterparty_account_id": ["merchant_1", "merchant_2"],
            "amount": [150.50, 89.99],
            "currency": ["USD", "EUR"],
            "timestamp": ["2026-07-23T10:00:00+00:00", "2026-07-23T10:05:00+00:00"],
            "merchant_category_code": ["5999", "5411"],
            "origin_country": ["US", "FR"],
            "destination_country": ["US", "FR"],
            "channel_type": ["ONLINE", "POS"],
        }
    )

    connector = ParquetConnector()
    txs = connector.parse_batch(df)

    assert len(txs) == 2
    assert txs[0].transaction_id == "tx_001"
    assert txs[0].amount == 150.50
    assert txs[1].currency == "EUR"

    streamed = list(connector.consume_stream())
    assert len(streamed) == 2
    assert streamed[0].transaction_id == "tx_001"


def test_feature_schema_validates_against_contract() -> None:
    """Verifies schema fallback handling for missing/partial row attributes."""
    df = pd.DataFrame(
        {
            "amount": [42.0],
        }
    )

    connector = ParquetConnector()
    txs = connector.parse_batch(df)

    assert len(txs) == 1
    assert txs[0].transaction_id == "parquet_tx_0"
    assert txs[0].account_id == "UNKNOWN_DEBTOR"
    assert txs[0].counterparty_account_id == "UNKNOWN_CREDITOR"
    assert txs[0].amount == 42.0
    assert txs[0].currency == "USD"
    assert txs[0].channel_type == "BENCHMARK_PARQUET"


def test_dataset_preparation_script_output() -> None:
    """Verifies benchmark_prepare_datasets script generates files and dataset_manifest.json."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        manifest = prepare_benchmark_datasets(samples=50, out_dir=tmp_dir)

        assert "banks" in manifest
        assert "bank_a" in manifest["banks"]
        assert "bank_b" in manifest["banks"]
        assert "bank_c" in manifest["banks"]

        manifest_path = Path(tmp_dir) / "dataset_manifest.json"
        assert manifest_path.exists()

        csv_a = Path(tmp_dir) / "bank_a.csv"
        assert csv_a.exists()

        connector = ParquetConnector(filepath=csv_a)
        streamed = list(connector.consume_stream())
        assert len(streamed) == 50
