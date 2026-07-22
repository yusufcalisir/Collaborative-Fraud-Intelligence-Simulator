"""Base Bank Connector Abstract Class and Data Contracts for Transaction Streams."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.application.interfaces.bank_connector import BankConnectorInterface

if TYPE_CHECKING:
    from collections.abc import Generator

    from app.domain.value_objects import ModelWeights


class NormalizedTransaction(BaseModel):
    """Standardized payment transaction schema across all bank connectors."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    account_id: str = Field(..., description="Debtor / Originating account identifier")
    counterparty_account_id: str = Field(
        ..., description="Creditor / Destination account identifier"
    )
    amount: float = Field(..., gt=0, description="Transaction monetary amount")
    currency: str = Field(default="USD", description="ISO 4217 currency code")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="UTC transaction timestamp"
    )
    merchant_category_code: str = Field(
        default="0000", description="ISO 18245 Merchant Category Code"
    )
    origin_country: str = Field(default="US", description="ISO 3166-1 alpha-2 origin country code")
    destination_country: str = Field(
        default="US", description="ISO 3166-1 alpha-2 destination country code"
    )
    device_fingerprint: str = Field(
        default="", description="Cryptographic device or browser fingerprint"
    )
    ip_subnet: str = Field(default="", description="Masked IP subnet (e.g. 192.168.1.0/24)")
    channel_type: str = Field(
        default="ONLINE", description="Transaction channel (ONLINE, MOBILE, ATM, POS, SWIFT)"
    )


class BaseBankConnector(BankConnectorInterface, ABC):
    """Abstract base class defining standardized ingestion interface for core bank systems."""

    def initialize(
        self,
        bank_id: str,
        num_transactions: int,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Default initialization stub for stream/file ingestion connectors."""
        return {"bank_id": bank_id, "status": "initialized", "num_transactions": num_transactions}

    def train(
        self,
        bank_id: str,
        weights: ModelWeights,
        learning_rate: float,
        batch_size: int,
        epochs: int,
        enable_dp: bool,
        dp_epsilon: float,
        dp_delta: float,
        dp_max_grad_norm: float,
        correlation_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Default train stub for stream/file ingestion connectors."""
        return {"bank_id": bank_id, "status": "completed", "weights": weights}

    def evaluate(
        self,
        bank_id: str,
        weights: ModelWeights,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Default evaluate stub for stream/file ingestion connectors."""
        return {"bank_id": bank_id, "loss": 0.0, "accuracy": 1.0}

    @abstractmethod
    def consume_stream(self) -> Generator[NormalizedTransaction, None, None]:
        """Streams real-time payment transactions continuously."""
        pass

    @abstractmethod
    def parse_batch(self, payload: Any) -> list[NormalizedTransaction]:
        """Parses batch payloads from EOD files, bulk drops, or REST webhooks."""
        pass
