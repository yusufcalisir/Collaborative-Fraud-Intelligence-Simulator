"""Alert and intelligence API endpoints.

Manages fraud alerts and shared cross-institution intelligence.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.application.schemas.phase2 import (
    AlertResponse,
    ExplainabilityResponse,
    IntelligenceStatsResponse,
    SharedIntelligenceResponse,
)
from app.application.services.alert_service import AlertIntelligenceService
from app.application.services.explainability_service import ExplainabilityService
from app.domain.enums import AlertSeverity, AlertStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["alerts"])

# Shared service instances (singleton pattern matching Phase 1)
_alert_service = AlertIntelligenceService()
_explainability_service = ExplainabilityService()


def get_alert_service() -> AlertIntelligenceService:
    return _alert_service


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    bank_id: str | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[AlertResponse]:
    """List fraud alerts with optional filters."""
    sev = AlertSeverity(severity) if severity else None
    stat = AlertStatus(status) if status else None

    alerts = _alert_service.get_alerts(
        bank_id=bank_id,
        severity=sev,
        status=stat,
        limit=limit,
    )

    return [
        AlertResponse(
            id=a.id,
            bank_id=a.bank_id,
            transaction_id=a.transaction_id,
            risk_score=a.risk_score,
            severity=a.severity.value,
            status=a.status.value,
            reason_codes=a.reason_codes,
            confidence=a.confidence,
            involved_entity_ids=a.involved_entity_ids,
            created_at=a.created_at.isoformat(),
            top_features=a.top_features,
            risk_factors=a.risk_factors,
            model_confidence=a.model_confidence,
        )
        for a in alerts
    ]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str) -> AlertResponse:
    """Get alert detail."""
    alert = _alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertResponse(
        id=alert.id,
        bank_id=alert.bank_id,
        transaction_id=alert.transaction_id,
        risk_score=alert.risk_score,
        severity=alert.severity.value,
        status=alert.status.value,
        reason_codes=alert.reason_codes,
        confidence=alert.confidence,
        involved_entity_ids=alert.involved_entity_ids,
        created_at=alert.created_at.isoformat(),
        top_features=alert.top_features,
        risk_factors=alert.risk_factors,
        model_confidence=alert.model_confidence,
    )


@router.get("/alerts/{alert_id}/explain", response_model=ExplainabilityResponse)
async def explain_alert(alert_id: str) -> ExplainabilityResponse:
    """Get explainability report for an alert."""
    alert = _alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    report = _explainability_service.explain_alert(alert)

    total_weighted = sum(s.weighted_score for s in report.risk_score_breakdown)

    return ExplainabilityResponse(
        alert_id=report.alert_id,
        top_features=report.top_features,
        risk_factors=report.risk_factors,
        historical_evidence=report.historical_evidence,
        model_confidence=report.model_confidence,
        risk_score_breakdown=[
            {
                "signal_name": s.signal_name,
                "weight": s.weight,
                "raw_value": s.raw_value,
                "normalized_score": s.normalized_score,
                "explanation": s.explanation,
                "contribution": s.weighted_score / total_weighted if total_weighted > 0 else 0.0,
            }
            for s in report.risk_score_breakdown
        ],
        explanation_text=report.explanation_text,
    )


@router.get("/intelligence", response_model=list[SharedIntelligenceResponse])
async def list_intelligence(
    bank_id: str | None = Query(None, description="Filter intelligence NOT from this bank"),
) -> list[SharedIntelligenceResponse]:
    """Get shared intelligence feed."""
    if bank_id:
        items = _alert_service.consume_intelligence(bank_id)
    else:
        items = _alert_service.get_all_intelligence()

    return [
        SharedIntelligenceResponse(
            id=i.id,
            source_bank_id=i.source_bank_id,
            intelligence_type=i.intelligence_type.value,
            privacy_hash=i.privacy_hash,
            risk_indicator=i.risk_indicator,
            description=i.description,
            entity_type=i.entity_type.value if i.entity_type else None,
            related_alert_count=i.related_alert_count,
            created_at=i.created_at.isoformat(),
        )
        for i in items
    ]


@router.get("/intelligence/stats", response_model=IntelligenceStatsResponse)
async def intelligence_stats() -> IntelligenceStatsResponse:
    """Get shared intelligence statistics."""
    stats = _alert_service.get_intelligence_stats()
    return IntelligenceStatsResponse(**stats)
