"""Case management service.

Lightweight investigation workflow for fraud cases. Investigators
can open cases, link alerts, add notes, and track the investigation
timeline. This is intentionally simpler than a full case management
system — it demonstrates the workflow pattern without enterprise
complexity.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.domain.entities_phase2 import Case, CaseEvent, CaseNote
from app.domain.enums import CasePriority, CaseStatus

logger = logging.getLogger(__name__)

# Valid status transitions
_VALID_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.OPEN: {
        CaseStatus.ASSIGNED,
        CaseStatus.INVESTIGATING,
        CaseStatus.CLOSED_FALSE_POSITIVE,
    },
    CaseStatus.ASSIGNED: {CaseStatus.INVESTIGATING, CaseStatus.OPEN},
    CaseStatus.INVESTIGATING: {
        CaseStatus.PENDING_REVIEW,
        CaseStatus.ESCALATED,
        CaseStatus.CLOSED_CONFIRMED,
        CaseStatus.CLOSED_FALSE_POSITIVE,
    },
    CaseStatus.PENDING_REVIEW: {
        CaseStatus.INVESTIGATING,
        CaseStatus.ESCALATED,
        CaseStatus.CLOSED_CONFIRMED,
        CaseStatus.CLOSED_FALSE_POSITIVE,
    },
    CaseStatus.ESCALATED: {CaseStatus.INVESTIGATING, CaseStatus.CLOSED_CONFIRMED},
    CaseStatus.CLOSED_CONFIRMED: set(),
    CaseStatus.CLOSED_FALSE_POSITIVE: set(),
}


class CaseManagementService:
    """Manages investigation cases linking alerts to investigation workflows.

    Cases aggregate multiple alerts into a single investigation unit.
    The service enforces status transition rules and maintains an
    immutable investigation timeline.
    """

    def __init__(self) -> None:
        self._cases: dict[str, Case] = {}

    def create_case(
        self,
        title: str,
        priority: CasePriority = CasePriority.P3_MEDIUM,
        alert_ids: list[str] | None = None,
    ) -> Case:
        """Create a new investigation case."""
        case = Case(
            title=title,
            priority=priority,
            alert_ids=alert_ids or [],
        )

        case.timeline.append(
            CaseEvent(
                event_type="created",
                description=f"Case created: {title}",
                actor="system",
            )
        )

        self._cases[case.id] = case
        logger.info("Created case %s: %s (priority=%s)", case.id[:8], title, priority.value)
        return case

    def assign_case(self, case_id: str, investigator: str) -> Case:
        """Assign a case to an investigator."""
        case = self._get_case(case_id)
        old_assignee = case.assigned_to
        case.assigned_to = investigator
        case.status = CaseStatus.ASSIGNED
        case.updated_at = datetime.now(UTC)

        case.timeline.append(
            CaseEvent(
                event_type="assigned",
                description=f"Assigned to {investigator}"
                + (f" (from {old_assignee})" if old_assignee else ""),
                actor="system",
            )
        )

        logger.info("Assigned case %s to %s", case_id[:8], investigator)
        return case

    def add_note(self, case_id: str, author: str, content: str) -> CaseNote:
        """Add an investigation note to a case."""
        case = self._get_case(case_id)

        note = CaseNote(case_id=case_id, author=author, content=content)
        case.notes.append(note)
        case.updated_at = datetime.now(UTC)

        case.timeline.append(
            CaseEvent(
                event_type="note_added",
                description=f"Note by {author}: {content[:80]}{'...' if len(content) > 80 else ''}",
                actor=author,
            )
        )

        return note

    def change_status(self, case_id: str, new_status: CaseStatus, actor: str = "analyst") -> Case:
        """Change case status with transition validation.

        Raises:
            ValueError: If the transition is not valid.
        """
        case = self._get_case(case_id)
        old_status = case.status

        valid = _VALID_TRANSITIONS.get(old_status, set())
        if new_status not in valid:
            raise ValueError(
                f"Invalid transition: {old_status.value} → {new_status.value}. "
                f"Valid targets: {', '.join(s.value for s in valid)}"
            )

        case.status = new_status
        case.updated_at = datetime.now(UTC)

        if new_status in (CaseStatus.CLOSED_CONFIRMED, CaseStatus.CLOSED_FALSE_POSITIVE):
            case.closed_at = datetime.now(UTC)

        case.timeline.append(
            CaseEvent(
                event_type="status_changed",
                description=f"Status: {old_status.value} → {new_status.value}",
                actor=actor,
                metadata={"from": old_status.value, "to": new_status.value},
            )
        )

        logger.info("Case %s status: %s → %s", case_id[:8], old_status.value, new_status.value)
        return case

    def link_alert(self, case_id: str, alert_id: str) -> Case:
        """Link an additional alert to an existing case."""
        case = self._get_case(case_id)

        if alert_id not in case.alert_ids:
            case.alert_ids.append(alert_id)
            case.updated_at = datetime.now(UTC)

            case.timeline.append(
                CaseEvent(
                    event_type="alert_linked",
                    description=f"Alert {alert_id[:8]} linked to case",
                    actor="system",
                )
            )

        return case

    def get_timeline(self, case_id: str) -> list[CaseEvent]:
        """Get the investigation timeline for a case."""
        case = self._get_case(case_id)
        return sorted(case.timeline, key=lambda e: e.timestamp)

    def export_summary(self, case_id: str) -> str:
        """Export an investigation summary as markdown.

        Returns:
            Markdown-formatted summary suitable for reporting.
        """
        case = self._get_case(case_id)
        lines = [
            f"# Investigation Summary: {case.title}",
            "",
            f"**Case ID:** {case.id}",
            f"**Status:** {case.status.value}",
            f"**Priority:** {case.priority.value}",
            f"**Assigned to:** {case.assigned_to or 'Unassigned'}",
            f"**Created:** {case.created_at.isoformat()}",
        ]

        if case.closed_at:
            lines.append(f"**Closed:** {case.closed_at.isoformat()}")
            if case.duration_hours is not None:
                lines.append(f"**Duration:** {case.duration_hours:.1f} hours")

        lines.extend(
            [
                "",
                f"## Linked Alerts ({len(case.alert_ids)})",
                "",
            ]
        )
        for alert_id in case.alert_ids:
            lines.append(f"- `{alert_id}`")

        if case.notes:
            lines.extend(["", "## Investigation Notes", ""])
            for note in case.notes:
                lines.append(f"### {note.author} — {note.created_at.strftime('%Y-%m-%d %H:%M')}")
                lines.append(f"{note.content}")
                lines.append("")

        lines.extend(["", "## Timeline", ""])
        for event in sorted(case.timeline, key=lambda e: e.timestamp):
            ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"- **{ts}** [{event.event_type}] {event.description}")

        return "\n".join(lines)

    def get_case(self, case_id: str) -> Case | None:
        return self._cases.get(case_id)

    def get_cases(
        self,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        limit: int = 50,
    ) -> list[Case]:
        """Retrieve cases with optional filters."""
        cases = list(self._cases.values())
        if status:
            cases = [c for c in cases if c.status == status]
        if priority:
            cases = [c for c in cases if c.priority == priority]
        return sorted(cases, key=lambda c: c.created_at, reverse=True)[:limit]

    # ── Private helpers ────────────────────────

    def _get_case(self, case_id: str) -> Case:
        case = self._cases.get(case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")
        return case
