"""Data Contract Validation Engine for Ingested Payment Streams."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
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

VALID_CURRENCIES = {
    "USD",
    "EUR",
    "GBP",
    "TRY",
    "CAD",
    "AUD",
    "JPY",
    "CHF",
    "SEK",
    "NOK",
    "DKK",
    "CNY",
    "SGD",
    "BRL",
    "INR",
}


class DataValidationError(ValueError):
    """Raised when an ingested transaction violates data contract specifications."""


class DataContractValidator:
    """Validates incoming NormalizedTransaction events against strict banking data contracts."""

    @staticmethod
    def validate_iban(iban: str) -> bool:
        """Validates an IBAN according to ISO 13616 mod-97 specification."""
        clean_iban = re.sub(r"\s+", "", iban).upper()
        if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}$", clean_iban):
            return False

        rearranged = clean_iban[4:] + clean_iban[:4]
        numeric_str = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearranged)
        return int(numeric_str) % 97 == 1

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

        now = datetime.now(UTC)
        tx_ts = (
            tx.timestamp.astimezone(UTC)
            if tx.timestamp.tzinfo
            else tx.timestamp.replace(tzinfo=UTC)
        )
        if tx_ts > now + timedelta(minutes=10):
            raise DataValidationError(f"Transaction timestamp is in the future: {tx.timestamp}.")

        origin_upper = tx.origin_country.upper()
        dest_upper = tx.destination_country.upper()
        if origin_upper not in VALID_COUNTRY_CODES:
            logger.debug("Non-standard origin country code: %s", tx.origin_country)
        if dest_upper not in VALID_COUNTRY_CODES:
            logger.debug("Non-standard destination country code: %s", tx.destination_country)

        return True
