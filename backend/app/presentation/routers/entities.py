"""Entity and resolution API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.application.schemas.phase2 import (
    EntityProfileResponse,
    EntityResolveRequest,
    EntityResponse,
    PSIRequest,
    PSIResponse,
)
from app.application.services.entity_resolution import EntityResolutionService
from app.application.services.psi_service import PSIService
from app.domain.enums import EntityType, RiskLevel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/entities", tags=["entities"])

_entity_service = EntityResolutionService()


def get_entity_service() -> EntityResolutionService:
    return _entity_service


@router.get("", response_model=list[EntityResponse])
async def list_entities(
    entity_type: str | None = Query(None),
    bank_id: str | None = Query(None),
    risk_level: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[EntityResponse]:
    """List entities with optional filters."""
    et = EntityType(entity_type) if entity_type else None
    rl = RiskLevel(risk_level) if risk_level else None

    entities = _entity_service.get_entities(
        entity_type=et,
        bank_id=bank_id,
        risk_level=rl,
        limit=limit,
    )
    return [
        EntityResponse(
            id=e.id,
            entity_type=e.entity_type.value,
            privacy_id=e.privacy_id,
            bank_id=e.bank_id,
            display_label=e.display_label,
            attributes=e.attributes,
            risk_level=e.risk_level.value,
            alert_count=e.alert_count,
            first_seen=e.first_seen.isoformat(),
            last_seen=e.last_seen.isoformat(),
        )
        for e in entities
    ]


@router.get("/{entity_id}", response_model=EntityProfileResponse)
async def get_entity_profile(entity_id: str) -> EntityProfileResponse:
    """Get entity profile with cross-institution data."""
    try:
        profile = _entity_service.build_entity_profile(entity_id)
        return EntityProfileResponse(**profile)
    except ValueError:
        raise HTTPException(status_code=404, detail="Entity not found")


@router.get("/{entity_id}/relationships")
async def get_entity_relationships(entity_id: str) -> list[dict]:
    """Get direct relationships for an entity."""
    entity = _entity_service.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    rels = [
        r
        for r in _entity_service.get_relationships()
        if r.source_entity_id == entity_id or r.target_entity_id == entity_id
    ]
    return [
        {
            "id": r.id,
            "source_entity_id": r.source_entity_id,
            "target_entity_id": r.target_entity_id,
            "relationship_type": r.relationship_type.value,
            "confidence": r.confidence,
            "evidence": r.evidence,
            "created_at": r.created_at.isoformat(),
        }
        for r in rels
    ]


@router.post("/resolve", response_model=list[EntityResponse])
async def resolve_entity(req: EntityResolveRequest) -> list[EntityResponse]:
    """Find entities matching a privacy hash across institutions."""
    entities = _entity_service.resolve_cross_institution(req.privacy_hash)
    return [
        EntityResponse(
            id=e.id,
            entity_type=e.entity_type.value,
            privacy_id=e.privacy_id,
            bank_id=e.bank_id,
            display_label=e.display_label,
            attributes=e.attributes,
            risk_level=e.risk_level.value,
            alert_count=e.alert_count,
            first_seen=e.first_seen.isoformat(),
            last_seen=e.last_seen.isoformat(),
        )
        for e in entities
    ]


_psi_service = PSIService(_entity_service)


@router.post("/psi", response_model=PSIResponse)
async def run_entities_psi(req: PSIRequest) -> PSIResponse:
    """Run simulated Private Set Intersection (PSI) protocol between two banks."""
    et = EntityType(req.entity_type) if req.entity_type else None
    result = _psi_service.run_psi(req.bank_a_id, req.bank_b_id, entity_type=et)
    return PSIResponse(**result)
