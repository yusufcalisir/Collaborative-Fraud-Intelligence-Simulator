"""Graph API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.application.schemas.phase2 import GraphResponse, GraphStatsResponse
from app.application.services.graph_engine import GraphEngine
from app.domain.enums import EntityType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

_graph_engine = GraphEngine()


def get_graph_engine() -> GraphEngine:
    return _graph_engine


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
