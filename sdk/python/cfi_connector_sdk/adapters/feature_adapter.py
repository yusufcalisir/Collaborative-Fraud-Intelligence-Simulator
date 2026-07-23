"""Base Feature Adapter for online velocity feature extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cfi_connector_sdk.adapters.transaction_adapter import NormalizedTransaction


class BaseFeatureAdapter:
    """Computes streaming transaction velocity features for local ML model training."""

    def extract_velocity_features(
        self,
        tx: NormalizedTransaction,
        history: list[NormalizedTransaction],
    ) -> dict[str, float]:
        """Calculates rolling velocity features (1h count, 24h count, 24h amount sum)."""
        tx_time = tx.timestamp.timestamp()
        one_hour_ago = tx_time - 3600
        twenty_four_hours_ago = tx_time - 86400

        tx_count_1h = 0
        tx_count_24h = 0
        amount_sum_24h = 0.0

        for past_tx in history:
            past_time = past_tx.timestamp.timestamp()
            if past_time >= twenty_four_hours_ago:
                tx_count_24h += 1
                amount_sum_24h += past_tx.amount
                if past_time >= one_hour_ago:
                    tx_count_1h += 1

        avg_amount_24h = amount_sum_24h / max(tx_count_24h, 1)
        amount_ratio = tx.amount / max(avg_amount_24h, 1.0)

        return {
            "amount": float(tx.amount),
            "tx_count_1h": float(tx_count_1h),
            "tx_count_24h": float(tx_count_24h),
            "amount_sum_24h": float(amount_sum_24h),
            "amount_ratio_24h": float(amount_ratio),
        }
