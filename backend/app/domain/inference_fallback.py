# ruff: noqa: UP042
"""Inference Fallback Engine for Low-Latency High-Availability Fraud Scoring."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class InferenceDecision(str, Enum):
    """Decision category for real-time transaction screening."""

    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


HIGH_RISK_MERCHANT_CATEGORIES = {
    "crypto_exchange",
    "gambling",
    "wire_transfer",
    "p2p_cash",
    "offshore_gaming",
}


class InferenceFallbackEngine:
    """Provides deterministic heuristic fallbacks when ML model scoring fails or times out."""

    def evaluate_heuristic_fallback(
        self,
        amount: float,
        velocity_1h: int = 1,
        merchant_category: str = "general_retail",
    ) -> tuple[InferenceDecision, float, str]:
        """Evaluates transaction attributes against fallback risk rules.

        Returns (decision, risk_score, explanation).
        """
        clean_mcc = merchant_category.lower().strip()
        reasons: list[str] = []
        score = 0.1

        # 1. High risk merchant check
        if clean_mcc in HIGH_RISK_MERCHANT_CATEGORIES:
            score += 0.45
            reasons.append(f"High-risk merchant category '{clean_mcc}'")

        # 2. Velocity anomaly check
        if velocity_1h >= 10:
            score += 0.35
            reasons.append(f"High hourly transaction velocity ({velocity_1h}/hr)")
        elif velocity_1h >= 5:
            score += 0.15
            reasons.append(f"Elevated velocity ({velocity_1h}/hr)")

        # 3. High transaction amount check
        if amount >= 50000.0:
            score += 0.30
            reasons.append(f"High transaction amount (${amount:,.2f})")
        elif amount >= 10000.0:
            score += 0.15
            reasons.append(f"Elevated transaction amount (${amount:,.2f})")

        risk_score = min(round(score, 4), 1.0)

        if risk_score >= 0.70:
            decision = InferenceDecision.BLOCK
        elif risk_score >= 0.35:
            decision = InferenceDecision.REVIEW
        else:
            decision = InferenceDecision.ALLOW

        explanation = (
            "Heuristic Fallback: " + "; ".join(reasons)
            if reasons
            else "Heuristic Fallback: Standard transaction profile"
        )
        logger.info(
            "Evaluated heuristic fallback (Decision: %s, Score: %.4f, Reasons: %s)",
            decision.value,
            risk_score,
            explanation,
        )
        return decision, risk_score, explanation
