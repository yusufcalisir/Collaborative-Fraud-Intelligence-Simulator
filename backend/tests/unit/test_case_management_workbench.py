# ruff: noqa: E402
"""Automated Unit Test Suite for Alert Lifecycle & Investigator Case Workbench."""

from __future__ import annotations

import pytest

from app.application.services.case_workbench import InvestigatorCaseWorkbenchService
from app.domain.case_management import (
    InvalidCaseTransitionError,
    InvestigatorCaseStatus,
)


def test_investigator_case_lifecycle_and_assignment() -> None:
    """Test 6-stage case lifecycle progression and analyst assignment."""
    service = InvestigatorCaseWorkbenchService()

    # 1. Create case from alerts
    record = service.create_case(
        title="Suspicious Structuring Batch",
        alert_ids=["alt_101", "alt_102"],
    )
    assert record.status == InvestigatorCaseStatus.NEW
    assert record.assigned_to is None

    # 2. Assign investigator -> ASSIGNED
    service.assign_investigator(record.case_id, "analyst_john")
    assert record.status == InvestigatorCaseStatus.ASSIGNED
    assert record.assigned_to == "analyst_john"

    # 3. Transition to active investigation -> UNDER_INVESTIGATION
    service.transition_to_investigation(record.case_id, "analyst_john")
    assert record.status == InvestigatorCaseStatus.UNDER_INVESTIGATION

    # 4. Escalate case -> ESCALATED
    service.escalate_case(
        record.case_id,
        reason="Cross-border wire exceeding threshold",
        actor_id="analyst_john",
    )
    assert record.status == InvestigatorCaseStatus.ESCALATED


def test_case_resolution_requires_four_eyes_supervisor_signature() -> None:
    """Test blocking case resolution when Four-Eyes supervisor signature is missing."""
    service = InvestigatorCaseWorkbenchService()
    record = service.create_case(
        title="Card Testing Ring",
        alert_ids=["alt_501"],
    )
    service.assign_investigator(record.case_id, "analyst_sarah")
    service.transition_to_investigation(record.case_id, "analyst_sarah")

    # 1. Attempt resolution without valid supervisor signature -> Fails
    with pytest.raises(InvalidCaseTransitionError) as exc_info:
        service.resolve_case(
            case_id=record.case_id,
            determination=InvestigatorCaseStatus.RESOLVED_CONFIRMED_FRAUD,
            supervisor_signature="INVALID_SIG",
            actor_id="analyst_sarah",
        )
    assert "Four-Eyes supervisor dual-authorization signature required" in str(exc_info.value)

    # 2. Resolution with valid supervisor signature -> Succeeds
    resolved = service.resolve_case(
        case_id=record.case_id,
        determination=InvestigatorCaseStatus.RESOLVED_CONFIRMED_FRAUD,
        supervisor_signature="SIG_SUPERVISOR_99001",
        actor_id="supervisor_mike",
    )
    assert resolved.status == InvestigatorCaseStatus.RESOLVED_CONFIRMED_FRAUD
    assert resolved.supervisor_signature == "SIG_SUPERVISOR_99001"


def test_case_blocks_illegal_stage_jumps() -> None:
    """Test blocking illegal direct status jumps (e.g. NEW directly to RESOLVED)."""
    service = InvestigatorCaseWorkbenchService()
    record = service.create_case(
        title="Direct Jump Test",
        alert_ids=["alt_999"],
    )

    with pytest.raises(InvalidCaseTransitionError) as exc_info:
        service.resolve_case(
            case_id=record.case_id,
            determination=InvestigatorCaseStatus.RESOLVED_FALSE_POSITIVE,
            supervisor_signature="SIG_SUPERVISOR_123",
            actor_id="analyst_bob",
        )
    assert "Illegal transition for case" in str(exc_info.value)
