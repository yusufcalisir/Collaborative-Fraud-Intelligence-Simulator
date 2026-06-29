"""Case management API endpoints.

CRUD operations for investigation cases with status transitions,
notes, alert linking, and timeline.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.application.schemas.phase2 import (
    CaseCreateRequest,
    CaseEventResponse,
    CaseLinkAlertRequest,
    CaseNoteRequest,
    CaseNoteResponse,
    CaseResponse,
    CaseStatusRequest,
    CaseSummaryResponse,
)
from app.application.services.case_service import CaseManagementService
from app.domain.enums import CasePriority, CaseStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

_case_service = CaseManagementService()


def get_case_service() -> CaseManagementService:
    return _case_service


@router.get("", response_model=list[CaseSummaryResponse])
async def list_cases(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[CaseSummaryResponse]:
    """List investigation cases."""
    stat = CaseStatus(status) if status else None
    pri = CasePriority(priority) if priority else None

    cases = _case_service.get_cases(status=stat, priority=pri, limit=limit)
    return [
        CaseSummaryResponse(
            id=c.id,
            title=c.title,
            status=c.status.value,
            priority=c.priority.value,
            assigned_to=c.assigned_to,
            alert_count=len(c.alert_ids),
            created_at=c.created_at.isoformat(),
            is_open=c.is_open,
        )
        for c in cases
    ]


@router.post("", response_model=CaseResponse)
async def create_case(req: CaseCreateRequest) -> CaseResponse:
    """Create a new investigation case."""
    priority = CasePriority(req.priority)
    case = _case_service.create_case(
        title=req.title, priority=priority, alert_ids=req.alert_ids,
    )
    return _serialize_case(case)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str) -> CaseResponse:
    """Get case detail."""
    case = _case_service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _serialize_case(case)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case_status(case_id: str, req: CaseStatusRequest) -> CaseResponse:
    """Update case status."""
    try:
        new_status = CaseStatus(req.status)
        case = _case_service.change_status(case_id, new_status, actor=req.actor)
        return _serialize_case(case)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/notes", response_model=CaseNoteResponse)
async def add_note(case_id: str, req: CaseNoteRequest) -> CaseNoteResponse:
    """Add an investigation note."""
    try:
        note = _case_service.add_note(case_id, author=req.author, content=req.content)
        return CaseNoteResponse(
            id=note.id,
            case_id=note.case_id,
            author=note.author,
            content=note.content,
            created_at=note.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{case_id}/alerts", response_model=CaseResponse)
async def link_alert(case_id: str, req: CaseLinkAlertRequest) -> CaseResponse:
    """Link an alert to a case."""
    try:
        case = _case_service.link_alert(case_id, req.alert_id)
        return _serialize_case(case)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{case_id}/timeline", response_model=list[CaseEventResponse])
async def get_timeline(case_id: str) -> list[CaseEventResponse]:
    """Get investigation timeline."""
    try:
        events = _case_service.get_timeline(case_id)
        return [
            CaseEventResponse(
                event_type=e.event_type,
                description=e.description,
                actor=e.actor,
                timestamp=e.timestamp.isoformat(),
                metadata=e.metadata,
            )
            for e in events
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{case_id}/export")
async def export_case(case_id: str) -> dict:
    """Export investigation summary as markdown."""
    try:
        summary = _case_service.export_summary(case_id)
        return {"case_id": case_id, "format": "markdown", "content": summary}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _serialize_case(case) -> CaseResponse:
    return CaseResponse(
        id=case.id,
        title=case.title,
        status=case.status.value,
        priority=case.priority.value,
        assigned_to=case.assigned_to,
        alert_ids=case.alert_ids,
        notes=[
            CaseNoteResponse(
                id=n.id, case_id=n.case_id, author=n.author,
                content=n.content, created_at=n.created_at.isoformat(),
            )
            for n in case.notes
        ],
        timeline=[
            CaseEventResponse(
                event_type=e.event_type, description=e.description,
                actor=e.actor, timestamp=e.timestamp.isoformat(),
                metadata=e.metadata,
            )
            for e in case.timeline
        ],
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
        closed_at=case.closed_at.isoformat() if case.closed_at else None,
        total_risk_score=case.total_risk_score,
        duration_hours=case.duration_hours,
        is_open=case.is_open,
    )
