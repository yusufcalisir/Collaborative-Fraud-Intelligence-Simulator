"""Unit tests for Enterprise Zero-Mock Policy Enforcement (Section 10.1)."""

from __future__ import annotations

import pytest

from app.infrastructure.connectors.factory import BankConnectorFactory
from app.infrastructure.connectors.iso20022_connector import ISO20022MessagingConnector
from app.infrastructure.connectors.open_banking_connector import OpenBankingConnector
from app.infrastructure.connectors.parquet_connector import ParquetConnector


class DummySettings:
    """Mock-free settings container for unit testing BankConnectorFactory resolution."""

    def __init__(self, connector_type: str = "parquet") -> None:
        self.bank_a_connector_type = connector_type
        self.bank_urls = {"bank-a": "http://localhost:8000"}
        self.redis_url = "redis://localhost:6379/0"
        self.psd2_base_url = "https://sandbox.berlingroup.org/psd2/v1"
        self.rabbitmq_host = "localhost"
        self.rabbitmq_port = 5672
        self.rabbitmq_user = "guest"
        self.rabbitmq_password = "guest"


def test_factory_rejects_mock_connector_type() -> None:
    """Verifies that BankConnectorFactory raises ValueError when requesting deprecated 'mock' connector type."""
    settings = DummySettings(connector_type="mock")

    with pytest.raises(
        ValueError, match="deprecated and removed under Enterprise Zero-Mock Policy"
    ):
        BankConnectorFactory.get_connector("bank-a", settings)  # type: ignore[arg-type]


def test_factory_rejects_mq_skeleton_type() -> None:
    """Verifies that BankConnectorFactory raises ValueError when requesting deprecated 'mq_skeleton' connector type."""
    settings = DummySettings(connector_type="mq_skeleton")

    with pytest.raises(
        ValueError, match="deprecated and removed under Enterprise Zero-Mock Policy"
    ):
        BankConnectorFactory.get_connector("bank-a", settings)  # type: ignore[arg-type]


def test_zero_mock_policy_enforcement() -> None:
    """Verifies that all valid production connector types resolve to non-mock connector instances."""
    settings_parquet = DummySettings(connector_type="parquet")
    conn_parquet = BankConnectorFactory.get_connector("bank-a", settings_parquet)  # type: ignore[arg-type]
    assert isinstance(conn_parquet, ParquetConnector)

    settings_psd2 = DummySettings(connector_type="open_banking")
    conn_psd2 = BankConnectorFactory.get_connector("bank-a", settings_psd2)  # type: ignore[arg-type]
    assert isinstance(conn_psd2, OpenBankingConnector)

    settings_iso = DummySettings(connector_type="iso20022")
    conn_iso = BankConnectorFactory.get_connector("bank-a", settings_iso)  # type: ignore[arg-type]
    assert isinstance(conn_iso, ISO20022MessagingConnector)
