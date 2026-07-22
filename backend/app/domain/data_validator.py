"""Data Contract Validation Engine for Ingested Payment Streams."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.connectors.base_connector import NormalizedTransaction

logger = logging.getLogger(__name__)

# Standard ISO 3166-1 alpha-2 country code set
VALID_COUNTRY_CODES = {
    "US",
    "GB",
    "DE",
    "FR",
    "TR",
    "CA",
    "AU",
    "JP",
    "CH",
    "NL",
    "SE",
    "SG",
    "HK",
    "BR",
    "IN",
    "CN",
    "ZA",
    "AE",
    "EE",
    "MX",
    "IT",
    "ES",
    "PL",
    "AT",
    "BE",
    "DK",
    "FI",
    "NO",
    "PT",
    "IE",
}

VALID_CURRENCIES = {"USD", "EUR", "GBP", "TRY", "CAD", "AUD", "JPY", "CHF"}


class DataValidationError(ValueError):
    """Raised when an ingested transaction violates data contract specifications."""


class DataContractValidator:
    """Validates incoming NormalizedTransaction events against strict banking data contracts."""

    @staticmethod
    def validate_transaction(tx: NormalizedTransaction) -> bool:
        """Validates a NormalizedTransaction instance.

        Raises:
            DataValidationError: If any field fails schema/range checks.

        Returns:
            True if valid.
        """
        if not tx.transaction_id or not tx.transaction_id.strip():
            raise DataValidationError("Transaction ID cannot be empty.")

        if not tx.account_id or not tx.account_id.strip():
            raise DataValidationError("Account ID cannot be empty.")

        if tx.amount <= 0:
            raise DataValidationError(f"Invalid transaction amount: {tx.amount}. Must be > 0.")

        currency_upper = tx.currency.upper()
        if currency_upper not in VALID_CURRENCIES:
            logger.warning(
                "Unrecognized currency code %s for tx %s", tx.currency, tx.transaction_id
            )

        origin_upper = tx.origin_country.upper()
        dest_upper = tx.destination_country.upper()
        if origin_upper not in VALID_COUNTRY_CODES:
            logger.debug("Non-standard origin country code: %s", tx.origin_country)
        if dest_upper not in VALID_COUNTRY_CODES:
            logger.debug("Non-standard destination country code: %s", tx.destination_country)

        return True
