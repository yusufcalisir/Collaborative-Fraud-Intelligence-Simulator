"""Bank information endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
from fastapi import APIRouter, HTTPException
from scipy import stats

if TYPE_CHECKING:
    from numpy.typing import NDArray

from app.application.services.data_generator import DataGenerator

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
        "fraud_pattern": "Card testing - repeated small amounts followed by a large charge",
        "characteristics": [
            "Concentrated geographic footprint",
            "Longer average account age",
            "POS-dominant transaction mix",
            "Moderate fraud rate with distinct testing patterns",
        ],
    },
]

# Cached distributions data (computed once on first request)
_distributions_cache: dict[str, Any] | None = None


@router.get("")
async def list_banks() -> list[dict]:
    """List all bank configurations (reference data)."""
    return BANK_CONFIGS


@router.get("/distributions")
async def get_bank_distributions() -> dict[str, Any]:
    """Get distribution data for all banks to visualize Non-IID data drift.

    Generates a small sample (1000 txns/bank) and computes:
    - Transaction amount histograms (15 bins, log-scale)
    - Hourly fraud rate distributions (24h)
    - Merchant category risk profiles (top 8)
    - KS divergence statistics between bank pairs
    """
    global _distributions_cache  # noqa: PLW0603

    if _distributions_cache is not None:
        return _distributions_cache

    generator = DataGenerator(seed=42)
    datasets = generator.generate_bank_datasets(
        bank_a_size=1000,
        bank_b_size=1000,
        bank_c_size=1000,
    )

    banks_data: dict[str, Any] = {}
    amount_arrays: dict[str, NDArray[Any]] = {}

    for bank_id, (df, labels) in datasets.items():
        amounts: NDArray[Any] = df["transaction_amount"].to_numpy()
        amount_arrays[bank_id] = amounts
        hours: NDArray[Any] = df["hour_of_day"].to_numpy()
        merchants: NDArray[Any] = df["merchant_category"].to_numpy()
        is_fraud: NDArray[Any] = labels.to_numpy().astype(bool)

        # 1) Transaction amount histogram (log-scale bins)
        log_bins = np.logspace(
            np.log10(max(amounts.min(), 0.01)),
            np.log10(amounts.max() + 1),
            16,
        )
        total_counts, bin_edges = np.histogram(amounts, bins=log_bins)
        fraud_counts, _ = np.histogram(amounts[is_fraud], bins=log_bins)

        amount_histogram = {
            "bins": [round(float(b), 2) for b in bin_edges],
            "counts": [int(c) for c in total_counts],
            "fraud_counts": [int(c) for c in fraud_counts],
        }

        # 2) Hourly fraud rate
        hourly_total = np.zeros(24, dtype=int)
        hourly_fraud = np.zeros(24, dtype=int)
        for h in range(24):
            mask = hours == h
            hourly_total[h] = int(mask.sum())
            hourly_fraud[h] = int((mask & is_fraud).sum())

        hourly_fraud_rate = {
            "hours": list(range(24)),
            "total": [int(t) for t in hourly_total],
            "fraud": [int(f) for f in hourly_fraud],
        }

        # 3) Merchant category risk (top 8 by volume)
        unique_merchants, merchant_counts = np.unique(merchants, return_counts=True)
        top_idx = np.argsort(-merchant_counts)[:8]
        top_merchants = unique_merchants[top_idx]
        top_counts = merchant_counts[top_idx]

        merchant_fraud_rates = []
        for m in top_merchants:
            m_mask = merchants == m
            m_total = int(m_mask.sum())
            m_fraud = int((m_mask & is_fraud).sum())
            merchant_fraud_rates.append(round(m_fraud / m_total, 4) if m_total > 0 else 0.0)

        merchant_risk = {
            "categories": [str(m) for m in top_merchants],
            "fraud_rates": merchant_fraud_rates,
            "counts": [int(c) for c in top_counts],
        }

        banks_data[bank_id] = {
            "amount_histogram": amount_histogram,
            "hourly_fraud_rate": hourly_fraud_rate,
            "merchant_risk": merchant_risk,
        }

    # 4) KS divergence between bank pairs
    pairs = [("bank_a", "bank_b"), ("bank_a", "bank_c"), ("bank_b", "bank_c")]
    ks_stats: dict[str, float] = {}
    for b1, b2 in pairs:
        ks_stat, _ = stats.ks_2samp(amount_arrays[b1], amount_arrays[b2])
        key = f"{b1.split('_')[1]}_vs_{b2.split('_')[1]}"
        ks_stats[key] = round(float(ks_stat), 4)

    overall_score = round(sum(ks_stats.values()) / len(ks_stats), 4)

    result: dict[str, Any] = {
        "banks": banks_data,
        "divergence_summary": {
            "amount_ks_statistic": ks_stats,
            "overall_non_iid_score": overall_score,
        },
    }

    _distributions_cache = result
    return result


@router.get("/{bank_id}")
async def get_bank(bank_id: str) -> dict:
    """Get details for a specific bank."""
    for bank in BANK_CONFIGS:
        if bank["id"] == bank_id:
            return bank
    raise HTTPException(status_code=404, detail=f"Bank {bank_id} not found")
