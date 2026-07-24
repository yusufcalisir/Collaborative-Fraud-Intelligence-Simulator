"""Label Privacy Guard for Zero-PII Leak Enforcement."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class LabelPrivacyViolationError(Exception):
    """Raised when unmasked PII or non-compliant DP parameters are detected."""

    pass


# Unhashed PII regex patterns (raw IBAN, SSN, email, clear text account IDs)
UNHASHED_PII_PATTERNS = [
    re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{12,30}$", re.IGNORECASE),  # Raw IBAN
    re.compile(r"^\d{3}-\d{2}-\d{4}$"),  # Raw SSN
    re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$"),  # Raw Email
]


class LabelPrivacyGuard:
    """Enforces zero-PII leak constraints and Differential Privacy parameter bounds."""

    def validate_feedback_identifier(
        self,
        transaction_id_hash: str,
        raw_attributes: dict[str, Any] | None = None,
    ) -> None:
        """Validates that transaction identifier is properly hashed and no raw PII exists."""
        # 1. Identifier length check (Hex-encoded hash should be >= 32 chars)
        if len(transaction_id_hash) < 32:
            raise LabelPrivacyViolationError(
                f"Transaction identifier '{transaction_id_hash}' is too short; must be an HMAC-SHA256 hash (>= 32 chars)."
            )

        # 2. Check for cleartext PII patterns
        for pattern in UNHASHED_PII_PATTERNS:
            if pattern.match(transaction_id_hash):
                raise LabelPrivacyViolationError(
                    f"Transaction identifier '{transaction_id_hash}' matches raw PII format. Cleartext PII is strictly forbidden!"
                )

        # 3. Inspect raw attributes dictionary if provided
        if raw_attributes:
            forbidden_keys = {"iban", "ssn", "email", "customer_name", "credit_card"}
            for key in raw_attributes:
                if key.lower() in forbidden_keys:
                    raise LabelPrivacyViolationError(
                        f"Forbidden raw PII key '{key}' found in label feedback attributes!"
                    )

    def validate_gradient_privacy(self, epsilon: float, max_epsilon: float = 2.0) -> None:
        """Validates Differential Privacy budget parameter epsilon."""
        if epsilon <= 0.0 or epsilon > max_epsilon:
            raise LabelPrivacyViolationError(
                f"Differential Privacy epsilon {epsilon} is invalid. Must be in range (0.0, {max_epsilon}]."
            )
