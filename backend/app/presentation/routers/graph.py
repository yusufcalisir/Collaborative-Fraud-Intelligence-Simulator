"""Graph API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.application.schemas.phase2 import (
    CommunityAnalyticsResponse,
    GraphResponse,
    GraphStatsResponse,
    RiskPropagationRequest,
    RiskPropagationResponse,
    TemporalAnomalyResponse,
)
from app.application.services.graph_analytics_service import GraphAnalyticsService
from app.application.services.graph_engine import GraphEngine
from app.domain.enums import EntityType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

_graph_engine = GraphEngine()


def get_graph_engine() -> GraphEngine:
    return _graph_engine


@router.get("/clusters/list")
async def get_clusters(min_size: int = Query(3, ge=2, le=20)) -> list[dict]:
    """Get suspicious entity clusters."""
    clusters = _graph_engine.detect_clusters(min_size=min_size)
    return [
        {
            "cluster_id": i,
            "entity_ids": cluster,
            "size": len(cluster),
        }
        for i, cluster in enumerate(clusters)
    ]


@router.get("/search/nodes")
async def search_nodes(
    q: str = Query(..., min_length=1),
    entity_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Search entities in the graph."""
    et = EntityType(entity_type) if entity_type else None
    entities = _graph_engine.search_nodes(q, entity_type=et, limit=limit)
    return [
        {
            "id": e.id,
            "display_label": e.display_label,
            "entity_type": e.entity_type.value,
            "bank_id": e.bank_id,
            "risk_level": e.risk_level.value,
            "alert_count": e.alert_count,
        }
        for e in entities
    ]


@router.get("/stats/summary", response_model=GraphStatsResponse)
async def graph_stats() -> GraphStatsResponse:
    """Get graph statistics."""
    stats = _graph_engine.get_stats()
    return GraphStatsResponse(**stats)


_graph_analytics = GraphAnalyticsService(_graph_engine)


@router.post("/propagate-risk", response_model=RiskPropagationResponse)
async def propagate_risk(req: RiskPropagationRequest) -> RiskPropagationResponse:
    """Propagate risk scores along relationships using decay."""
    res = _graph_analytics.propagate_risk(decay_factor=req.decay_factor)
    return RiskPropagationResponse(**res)


@router.get("/communities/analytics", response_model=list[CommunityAnalyticsResponse])
async def get_communities_analytics(
    min_size: int = Query(3, ge=2, le=20),
) -> list[CommunityAnalyticsResponse]:
    """Get detailed community metrics sorted by fraud/risk density."""
    res = _graph_analytics.get_community_analytics(min_size=min_size)
    return [CommunityAnalyticsResponse(**c) for c in res]


@router.get("/temporal-anomalies", response_model=list[TemporalAnomalyResponse])
async def get_temporal_anomalies(
    window_minutes: int = Query(5, ge=1, le=60),
    min_edges: int = Query(3, ge=2, le=50),
) -> list[TemporalAnomalyResponse]:
    """Get temporal edge velocity anomaly subgraphs."""
    res = _graph_analytics.get_temporal_anomalies(
        window_minutes=window_minutes, min_edges=min_edges
    )
    return [TemporalAnomalyResponse(**a) for a in res]


@router.get("/{entity_id}", response_model=GraphResponse)
async def get_subgraph(
    entity_id: str,
    depth: int = Query(2, ge=1, le=4),
) -> GraphResponse:
    """Get subgraph centered on an entity."""
    subgraph = _graph_engine.get_subgraph(entity_id, radius=depth)
    if not subgraph.nodes:
        raise HTTPException(status_code=404, detail="Entity not found in graph")

    return GraphResponse(
        nodes=subgraph.nodes,
        edges=subgraph.edges,
        clusters=subgraph.clusters,
        center_entity_id=subgraph.center_entity_id,
        depth=subgraph.depth,
    )
