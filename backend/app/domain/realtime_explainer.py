"""Sub-Millisecond Fast Real-Time Decision Explainer."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RealtimeFeatureAttribution:
    """Attribution vector item for real-time inference decision explanation."""

    feature_name: str
    contribution_score: float
    direction: str  # "INCREASES_RISK" or "DECREASES_RISK"


class FastInferenceExplainer:
    """Provides sub-millisecond feature attributions without heavy explainer overhead."""

    def explain_realtime_score(
        self,
        amount: float,
        velocity_1h: int,
        merchant_category: str,
        risk_score: float,
    ) -> list[RealtimeFeatureAttribution]:
        """Calculates fast feature contribution vectors for online scoring."""
        attributions: list[RealtimeFeatureAttribution] = []
        clean_mcc = merchant_category.lower().strip()

        # 1. Merchant category attribution
        if clean_mcc in {"crypto_exchange", "gambling", "p2p_cash"}:
            attributions.append(
                RealtimeFeatureAttribution(
                    feature_name="merchant_category",
                    contribution_score=0.35,
                    direction="INCREASES_RISK",
                )
            )

        # 2. Transaction velocity attribution
        if velocity_1h >= 5:
            attributions.append(
                RealtimeFeatureAttribution(
                    feature_name="velocity_1h",
                    contribution_score=0.25,
                    direction="INCREASES_RISK",
                )
            )
        elif velocity_1h <= 2:
            attributions.append(
                RealtimeFeatureAttribution(
                    feature_name="velocity_1h",
                    contribution_score=0.10,
                    direction="DECREASES_RISK",
                )
            )

        # 3. Transaction amount attribution
        if amount >= 20000.0:
            attributions.append(
                RealtimeFeatureAttribution(
                    feature_name="amount",
                    contribution_score=0.40,
                    direction="INCREASES_RISK",
                )
            )
        elif amount < 500.0:
            attributions.append(
                RealtimeFeatureAttribution(
                    feature_name="amount",
                    contribution_score=0.15,
                    direction="DECREASES_RISK",
                )
            )

        return attributions
