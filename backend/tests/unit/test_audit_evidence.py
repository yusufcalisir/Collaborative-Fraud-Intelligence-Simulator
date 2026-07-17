from __future__ import annotations

import pytest

from app.application.services.case_service import (
    AuditService,
    CaseManagementService,
    EvidenceRegistryService,
)
from app.domain.enums import CasePriority, CaseStatus


@pytest.fixture
def case_service():
    service = CaseManagementService()
    service._cases.clear()
    return service


@pytest.fixture
def audit_service():
    service = AuditService()
    service._audit_store.clear()
    return service


@pytest.fixture
def evidence_service():
    service = EvidenceRegistryService()
    service._evidence_store.clear()
    return service


def test_four_eyes_gating_on_case_closure(case_service):
    # Create case
    case = case_service.create_case(title="ATO Investigation", priority=CasePriority.P1_CRITICAL)
    assert case.status == CaseStatus.OPEN

    # Transition to INVESTIGATING
    case = case_service.change_status(case.id, CaseStatus.INVESTIGATING, actor="analyst_1")
    assert case.status == CaseStatus.INVESTIGATING

    # Transition to ESCALATED
    case = case_service.change_status(case.id, CaseStatus.ESCALATED, actor="analyst_1")
    assert case.status == CaseStatus.ESCALATED

    # Attempt to close without supervisor signature
    with pytest.raises(ValueError) as exc:
        case_service.change_status(case.id, CaseStatus.CLOSED_CONFIRMED, actor="analyst_1")
    assert "Case closure requires secondary supervisor signature" in str(exc.value)

    # Attempt to close with same supervisor signature as actor analyst_1
    with pytest.raises(ValueError) as exc:
        case_service.change_status(
            case.id,
            CaseStatus.CLOSED_CONFIRMED,
            actor="analyst_1",
            supervisor_signature="analyst_1",
        )
    assert "Supervisor signature must be different from the analyst actor" in str(exc.value)

    # Close with valid secondary signature
    case = case_service.change_status(
        case.id,
        CaseStatus.CLOSED_CONFIRMED,
        actor="analyst_1",
        supervisor_signature="supervisor_bob",
    )
    assert case.status == CaseStatus.CLOSED_CONFIRMED
    assert case.closed_at is not None

    # Verify timeline metadata contains signature
    last_event = case.timeline[-1]
    assert last_event.metadata.get("supervisor_signature") == "supervisor_bob"


def test_evidence_registry_cryptographic_hash(case_service, evidence_service):
    # Create case
    case = case_service.create_case(title="Entity resolved ring", priority=CasePriority.P2_HIGH)

    # Register evidence
    file_content = "This is a dummy KYC passport scan document binary data"
    ev = evidence_service.register_evidence(
        case_id=case.id,
        evidence_type="document",
        title="Passport Scan",
        file_path="storage/uploads/passport_1.pdf",
        content=file_content,
        uploaded_by="analyst_1",
    )

    # Check generated SHA-256 hash
    import hashlib

    expected_hash = hashlib.sha256(file_content.encode("utf-8")).hexdigest()
    assert ev["content_hash"] == expected_hash
    assert ev["uploaded_by"] == "analyst_1"

    # Verify linked to case
    updated_case = case_service.get_case(case.id)
    assert ev["id"] in updated_case.evidence_ids

    # Verify timeline contains evidence_added event
    evidence_events = [e for e in updated_case.timeline if e.event_type == "evidence_added"]
    assert len(evidence_events) == 1
    assert "evidence_id" in evidence_events[0].metadata


def test_investigator_role_audit_logging(audit_service):
    # Log actions
    audit_service.log_action(
        investigator="analyst_1",
        action="access_case",
        target_id="case_abc",
        metadata={"title": "High Risk Loop"},
    )
    audit_service.log_action(
        investigator="analyst_1",
        action="query_entity",
        target_id="cust_hash_1",
    )
    audit_service.log_action(
        investigator="analyst_1",
        action="session_duration",
        target_id="session",
        session_duration_sec=320.5,
    )

    # Retrieve and verify logs
    logs = audit_service.get_logs()
    assert len(logs) == 3

    # Verify that all logs are recorded correctly
    actions = [log["action"] for log in logs]
    assert "session_duration" in actions
    assert "query_entity" in actions
    assert "access_case" in actions

    # Check details on specific logs
    session_log = next(log for log in logs if log["action"] == "session_duration")
    assert session_log["session_duration_sec"] == 320.5

    query_log = next(log for log in logs if log["action"] == "query_entity")
    assert query_log["target_id"] == "cust_hash_1"

    access_log = next(log for log in logs if log["action"] == "access_case")
    assert access_log["metadata"]["title"] == "High Risk Loop"
