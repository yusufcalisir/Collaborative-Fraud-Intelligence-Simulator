"""Bank information endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/banks", tags=["banks"])

# Default bank configurations (static reference data)
BANK_CONFIGS = [
    {
        "id": "bank_a",
        "name": "Meridian National",
        "tier": "large",
        "description": "Large retail bank with broad domestic presence",
        "default_fraud_ratio": 0.008,
        "default_transactions": 50000,
        "fraud_pattern": "Velocity spikes during late-night hours with unusual merchant categories",
        "characteristics": [
            "High transaction volume",
            "Predominantly domestic transactions",
            "POS-heavy with growing mobile adoption",
            "Low baseline fraud rate",
        ],
    },
    {
        "id": "bank_b",
        "name": "Nexus Digital",
        "tier": "medium",
        "description": "Digital-only bank with international customer base",
        "default_fraud_ratio": 0.025,
        "default_transactions": 30000,
        "fraud_pattern": "New accounts from high-risk countries using crypto and wire transfers",
        "characteristics": [
            "Mobile-first platform",
            "High international transaction ratio",
            "Younger account age distribution",
            "Higher baseline fraud rate due to onboarding velocity",
        ],
    },
    {
        "id": "bank_c",
        "name": "Heritage Regional",
        "tier": "small",
        "description": "Traditional regional bank with concentrated geography",
        "default_fraud_ratio": 0.012,
        "default_transactions": 20000,
        "fraud_pattern": "Card testing — repeated small amounts followed by a large charge",
        "characteristics": [
            "Concentrated geographic footprint",
            "Longer average account age",
            "POS-dominant transaction mix",
            "Moderate fraud rate with distinct testing patterns",
        ],
    },
]


@router.get("")
async def list_banks() -> list[dict]:
    """List all bank configurations (reference data)."""
    return BANK_CONFIGS


@router.get("/{bank_id}")
async def get_bank(bank_id: str) -> dict:
    """Get details for a specific bank."""
    for bank in BANK_CONFIGS:
        if bank["id"] == bank_id:
            return bank
    raise HTTPException(status_code=404, detail=f"Bank {bank_id} not found")
