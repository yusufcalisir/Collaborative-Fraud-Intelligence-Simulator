"""Tests for the case management service."""

import pytest

from app.application.services.case_service import CaseManagementService
from app.domain.enums import CasePriority, CaseStatus


@pytest.fixture
def case_service() -> CaseManagementService:
    return CaseManagementService()


class TestCaseCreation:
    def test_create_case(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Suspicious activity at Meridian")
        assert case.title == "Suspicious activity at Meridian"
        assert case.status == CaseStatus.OPEN
        assert case.priority == CasePriority.P3_MEDIUM
        assert case.is_open is True
        assert len(case.timeline) == 1  # "created" event

    def test_create_with_priority(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Critical fraud ring", priority=CasePriority.P1_CRITICAL)
        assert case.priority == CasePriority.P1_CRITICAL

    def test_create_with_alert_ids(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test", alert_ids=["a1", "a2", "a3"])
        assert len(case.alert_ids) == 3


class TestStatusTransitions:
    def test_valid_transition(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        updated = case_service.change_status(case.id, CaseStatus.INVESTIGATING)
        assert updated.status == CaseStatus.INVESTIGATING

    def test_invalid_transition_raises(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        # Cannot go from OPEN directly to CLOSED_CONFIRMED
        with pytest.raises(ValueError, match="Invalid transition"):
            case_service.change_status(case.id, CaseStatus.CLOSED_CONFIRMED)

    def test_closed_case_cannot_transition(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        case_service.change_status(case.id, CaseStatus.INVESTIGATING)
        case_service.change_status(case.id, CaseStatus.CLOSED_CONFIRMED)

        with pytest.raises(ValueError, match="Invalid transition"):
            case_service.change_status(case.id, CaseStatus.OPEN)

    def test_closing_sets_closed_at(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        case_service.change_status(case.id, CaseStatus.INVESTIGATING)
        closed = case_service.change_status(case.id, CaseStatus.CLOSED_CONFIRMED)
        assert closed.closed_at is not None
        assert closed.is_open is False


class TestNotes:
    def test_add_note(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        note = case_service.add_note(case.id, "analyst", "Reviewed transaction logs")
        assert note.author == "analyst"
        assert note.content == "Reviewed transaction logs"
        retrieved = case_service.get_case(case.id)
        assert retrieved is not None
        assert len(retrieved.notes) == 1

    def test_add_note_appends_timeline_event(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        case_service.add_note(case.id, "analyst", "Some note")
        updated = case_service.get_case(case.id)
        assert updated is not None
        note_events = [e for e in updated.timeline if e.event_type == "note_added"]
        assert len(note_events) == 1


class TestAlertLinking:
    def test_link_alert(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        case_service.link_alert(case.id, "alert_001")
        updated = case_service.get_case(case.id)
        assert updated is not None
        assert "alert_001" in updated.alert_ids

    def test_duplicate_link_ignored(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Test case")
        case_service.link_alert(case.id, "alert_001")
        case_service.link_alert(case.id, "alert_001")
        updated = case_service.get_case(case.id)
        assert updated is not None
        assert updated.alert_ids.count("alert_001") == 1


class TestExport:
    def test_export_summary_markdown(self, case_service: CaseManagementService) -> None:
        case = case_service.create_case("Fraud ring investigation")
        case_service.add_note(case.id, "analyst", "Initial review")
        md = case_service.export_summary(case.id)
        assert "# Investigation Summary" in md
        assert "Fraud ring investigation" in md
        assert "Initial review" in md


class TestCaseNotFound:
    def test_get_nonexistent_case(self, case_service: CaseManagementService) -> None:
        assert case_service.get_case("nonexistent") is None

    def test_change_status_nonexistent(self, case_service: CaseManagementService) -> None:
        with pytest.raises(ValueError, match="Case not found"):
            case_service.change_status("nonexistent", CaseStatus.INVESTIGATING)
