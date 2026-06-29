"""Investigation dashboard API endpoints.

Aggregates data from alerts, cases, entities, and intelligence
into dashboard statistics and visualizations.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import APIRouter

from app.application.schemas.phase2 import (
    DashboardStatsResponse,
    RiskWeightsResponse,
    RiskWeightsUpdateRequest,
)
from app.application.services.risk_engine import RiskScoringEngine
from app.domain.value_objects_phase2 import RiskWeightConfig
from app.presentation.routers.alerts import get_alert_service
from app.presentation.routers.cases import get_case_service
from app.presentation.routers.entities import get_entity_service
from app.presentation.routers.graph import get_graph_engine
from app.presentation.routers.scenarios import get_streaming_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

_risk_engine = RiskScoringEngine()


@router.get("/stats", response_model=DashboardStatsResponse)
async def dashboard_stats() -> DashboardStatsResponse:
    """Get aggregated dashboard statistics."""
    alert_svc = get_alert_service()
    case_svc = get_case_service()
    entity_svc = get_entity_service()
    graph = get_graph_engine()
    streaming = get_streaming_engine()

    all_alerts = alert_svc.get_alerts(limit=1000)
    critical_alerts = [a for a in all_alerts if a.severity.value == "critical"]
    open_cases = [c for c in case_svc.get_cases(limit=1000) if c.is_open]
    all_entities = entity_svc.get_entities(limit=1000)
    intel_stats = alert_svc.get_intelligence_stats()
    clusters = graph.detect_clusters(min_size=3)
    active = streaming.get_active_scenarios()

    return DashboardStatsResponse(
        total_alerts=len(all_alerts),
        critical_alerts=len(critical_alerts),
        open_cases=len(open_cases),
        total_entities=len(all_entities),
        shared_intelligence_items=intel_stats["total_items"],
        cross_institution_matches=0,  # Computed on demand
        active_scenarios=len(active),
        graph_clusters=len(clusters),
    )


@router.get("/alerts-by-severity")
async def alerts_by_severity() -> dict[str, int]:
    """Alert count grouped by severity."""
    alert_svc = get_alert_service()
    alerts = alert_svc.get_alerts(limit=1000)
    counts: dict[str, int] = defaultdict(int)
    for a in alerts:
        counts[a.severity.value] += 1
    return dict(counts)


@router.get("/alerts-by-bank")
async def alerts_by_bank() -> dict[str, int]:
    """Alert count grouped by bank."""
    alert_svc = get_alert_service()
    alerts = alert_svc.get_alerts(limit=1000)
    counts: dict[str, int] = defaultdict(int)
    for a in alerts:
        counts[a.bank_id] += 1
    return dict(counts)


@router.get("/entities-by-risk")
async def entities_by_risk() -> dict[str, int]:
    """Entity count grouped by risk level."""
    entity_svc = get_entity_service()
    entities = entity_svc.get_entities(limit=1000)
    counts: dict[str, int] = defaultdict(int)
    for e in entities:
        counts[e.risk_level.value] += 1
    return dict(counts)


@router.get("/top-risky-merchants")
async def top_risky_merchants() -> list[dict]:
    """Top merchants by alert involvement."""
    alert_svc = get_alert_service()
    alerts = alert_svc.get_alerts(limit=500)
    merchant_counts: dict[str, int] = defaultdict(int)
    for a in alerts:
        for code in a.reason_codes:
            if code == "MERCH-RISK":
                merchant_counts["high_risk_merchant"] += 1
    return [
        {"merchant": k, "alert_count": v}
        for k, v in sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]


@router.get("/risk-weights", response_model=RiskWeightsResponse)
async def get_risk_weights() -> RiskWeightsResponse:
    """Get current risk scoring weights."""
    w = _risk_engine.weights
    return RiskWeightsResponse(**w.to_dict())


@router.put("/risk-weights", response_model=RiskWeightsResponse)
async def update_risk_weights(req: RiskWeightsUpdateRequest) -> RiskWeightsResponse:
    """Update risk scoring weights."""
    new_weights = RiskWeightConfig(
        ml_prediction=req.ml_prediction,
        velocity_rules=req.velocity_rules,
        merchant_reputation=req.merchant_reputation,
        country_risk=req.country_risk,
        device_anomaly=req.device_anomaly,
        customer_history=req.customer_history,
        previous_alerts=req.previous_alerts,
        chargeback_history=req.chargeback_history,
        behavior_anomaly=req.behavior_anomaly,
    )
    _risk_engine.update_weights(new_weights)
    return RiskWeightsResponse(**new_weights.to_dict())
