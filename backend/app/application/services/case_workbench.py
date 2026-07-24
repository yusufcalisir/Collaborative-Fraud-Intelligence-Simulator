"""Investigator Case Workbench Service."""

from __future__ import annotations

import logging
import uuid

from app.domain.case_management import (
    CaseLifecycleStateMachine,
    FraudCaseRecord,
    InvestigatorCaseStatus,
)

logger = logging.getLogger(__name__)


class InvestigatorCaseWorkbenchService:
    """Service handling case creation, analyst assignment, escalation, and resolution."""

    def __init__(self) -> None:
        self.state_machine = CaseLifecycleStateMachine()
        self._cases: dict[str, FraudCaseRecord] = {}

    def create_case(
        self,
        title: str,
        alert_ids: list[str],
        actor_id: str = "SYSTEM",
    ) -> FraudCaseRecord:
        """Opens a new fraud investigation case from linked alert IDs."""
        case_id = f"case_{uuid.uuid4().hex[:8]}"
        record = FraudCaseRecord(
            case_id=case_id,
            title=title,
            alert_ids=alert_ids,
            status=InvestigatorCaseStatus.NEW,
        )
        self._cases[case_id] = record
        logger.info("Opened new case %s ('%s') with %d alerts", case_id, title, len(alert_ids))
        return record

    def assign_investigator(
        self,
        case_id: str,
        investigator_id: str,
        actor_id: str = "LEAD_ANALYST",
    ) -> FraudCaseRecord:
        """Assigns an investigator analyst to a case and transitions status."""
        if case_id not in self._cases:
            raise KeyError(f"Case '{case_id}' does not exist.")

        record = self._cases[case_id]
        record.assigned_to = investigator_id

        if record.status == InvestigatorCaseStatus.NEW:
            self.state_machine.transition_case(
                record=record,
                target_status=InvestigatorCaseStatus.ASSIGNED,
                actor_id=actor_id,
                notes=f"Assigned investigator {investigator_id}",
            )
        return record

    def transition_to_investigation(self, case_id: str, investigator_id: str) -> FraudCaseRecord:
        """Transitions case status to UNDER_INVESTIGATION."""
        if case_id not in self._cases:
            raise KeyError(f"Case '{case_id}' does not exist.")

        record = self._cases[case_id]
        return self.state_machine.transition_case(
            record=record,
            target_status=InvestigatorCaseStatus.UNDER_INVESTIGATION,
            actor_id=investigator_id,
            notes="Started active investigation",
        )

    def escalate_case(self, case_id: str, reason: str, actor_id: str) -> FraudCaseRecord:
        """Escalates a case for supervisor or compliance officer review."""
        if case_id not in self._cases:
            raise KeyError(f"Case '{case_id}' does not exist.")

        record = self._cases[case_id]
        return self.state_machine.transition_case(
            record=record,
            target_status=InvestigatorCaseStatus.ESCALATED,
            actor_id=actor_id,
            notes=f"Escalated: {reason}",
        )

    def resolve_case(
        self,
        case_id: str,
        determination: InvestigatorCaseStatus,
        supervisor_signature: str,
        actor_id: str,
        notes: str = "Final resolution determination",
    ) -> FraudCaseRecord:
        """Resolves a case with Four-Eyes supervisor dual-authorization signature."""
        if case_id not in self._cases:
            raise KeyError(f"Case '{case_id}' does not exist.")

        record = self._cases[case_id]
        return self.state_machine.transition_case(
            record=record,
            target_status=determination,
            actor_id=actor_id,
            supervisor_signature=supervisor_signature,
            notes=notes,
        )

    def get_case(self, case_id: str) -> FraudCaseRecord | None:
        """Retrieves case record by ID."""
        return self._cases.get(case_id)
