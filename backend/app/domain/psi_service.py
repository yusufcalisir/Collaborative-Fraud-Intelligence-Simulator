"""Diffie-Hellman Private Set Intersection (DH-PSI) Domain Module.

Re-exports core DH-PSI protocol constants, exponentiation functions, and PSIService
to satisfy domain-layer clean architecture boundaries.
"""

from __future__ import annotations

from app.application.services.psi_service import (
    PRIME_BIT_LENGTH,
    PSI_PRIME,
    PSIService,
    _extract_fuzzy_features,
)

__all__ = [
    "PSI_PRIME",
    "PRIME_BIT_LENGTH",
    "PSIService",
    "_extract_fuzzy_features",
]
