"""Low-Latency Real-Time Inference Gateway Router."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.inference_fallback import (
    InferenceDecision,
    InferenceFallbackEngine,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/inference", tags=["Real-Time Inference"])


class RealtimeInferenceRequest(BaseModel):
    """Schema for online transaction authorization requests."""

    transaction_id: str = Field(..., json_schema_extra={"example": "tx_88992211"})
    amount: float = Field(..., ge=0.0, json_schema_extra={"example": 1250.50})
    currency: str = Field("USD", json_schema_extra={"example": "USD"})
    source_account: str = Field(..., json_schema_extra={"example": "acc_src_991"})
    target_account: str = Field(..., json_schema_extra={"example": "acc_dst_002"})
    merchant_category: str = Field(
        "general_retail", json_schema_extra={"example": "crypto_exchange"}
    )
    velocity_1h: int = Field(1, ge=0, json_schema_extra={"example": 3})
    force_fallback: bool = Field(
        False, description="Simulate model timeout/failure to test fallback engine."
    )


class RealtimeInferenceResponse(BaseModel):
    """Schema for online transaction authorization decision responses."""

    transaction_id: str
    risk_score: float
    decision: InferenceDecision
    latency_ms: float
    evaluated_by: str  # "ML_MODEL" or "HEURISTIC_FALLBACK"
    explanation: str


fallback_engine = InferenceFallbackEngine()


@router.post("/score", response_model=RealtimeInferenceResponse)
def score_transaction_realtime(
    payload: RealtimeInferenceRequest,
) -> RealtimeInferenceResponse:
    """Scores an incoming transaction in real time with sub-100ms SLA and heuristic fallback."""
    start_time = time.perf_counter()

    try:
        if payload.force_fallback:
            raise RuntimeError("Forced simulation fallback")

        # Fast heuristic ML model simulation
        score = 0.05
        reasons: list[str] = []

        if payload.amount > 20000.0:
            score += 0.40
            reasons.append("High amount")
        if payload.merchant_category.lower() in {
            "crypto_exchange",
            "gambling",
            "p2p_cash",
        }:
            score += 0.35
            reasons.append("High-risk merchant")
        if payload.velocity_1h > 5:
            score += 0.20
            reasons.append("Velocity spike")

        risk_score = min(round(score, 4), 1.0)
        if risk_score >= 0.70:
            decision = InferenceDecision.BLOCK
        elif risk_score >= 0.35:
            decision = InferenceDecision.REVIEW
        else:
            decision = InferenceDecision.ALLOW

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        explanation = (
            "ML Model: " + "; ".join(reasons) if reasons else "ML Model: Normal risk profile"
        )

        return RealtimeInferenceResponse(
            transaction_id=payload.transaction_id,
            risk_score=risk_score,
            decision=decision,
            latency_ms=latency_ms,
            evaluated_by="ML_MODEL",
            explanation=explanation,
        )

    except Exception as exc:
        logger.warning(
            "Primary ML inference failed for tx %s (%s). Triggering fallback.",
            payload.transaction_id,
            exc,
        )
        decision, risk_score, explanation = fallback_engine.evaluate_heuristic_fallback(
            amount=payload.amount,
            velocity_1h=payload.velocity_1h,
            merchant_category=payload.merchant_category,
        )
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return RealtimeInferenceResponse(
            transaction_id=payload.transaction_id,
            risk_score=risk_score,
            decision=decision,
            latency_ms=latency_ms,
            evaluated_by="HEURISTIC_FALLBACK",
            explanation=explanation,
        )
