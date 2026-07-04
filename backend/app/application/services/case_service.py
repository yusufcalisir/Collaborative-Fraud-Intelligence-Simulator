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
from typing import Any

from app.domain.entities_phase2 import Case, CaseEvent, CaseNote
from app.domain.enums import CasePriority, CaseStatus
from app.infrastructure.redis_store import RedisStore

logger = logging.getLogger(__name__)


def _case_to_dict(c: Case) -> dict[str, Any]:
    return {
        "id": c.id,
        "title": c.title,
        "status": c.status.value,
        "priority": c.priority.value,
        "assigned_to": c.assigned_to,
        "alert_ids": c.alert_ids,
        "notes": [
            {
                "id": n.id,
                "case_id": n.case_id,
                "author": n.author,
                "content": n.content,
                "created_at": n.created_at.isoformat(),
            }
            for n in c.notes
        ],
        "timeline": [
            {
                "event_type": e.event_type,
                "description": e.description,
                "actor": e.actor,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.metadata,
            }
            for e in c.timeline
        ],
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "closed_at": c.closed_at.isoformat() if c.closed_at else None,
        "total_risk_score": c.total_risk_score,
    }


def _dict_to_case(d: dict[str, Any]) -> Case:
    from datetime import datetime

    d_copy = d.copy()
    d_copy["status"] = CaseStatus(d_copy["status"])
    d_copy["priority"] = CasePriority(d_copy["priority"])
    d_copy["created_at"] = datetime.fromisoformat(d_copy["created_at"])
    if d_copy.get("updated_at"):
        d_copy["updated_at"] = datetime.fromisoformat(d_copy["updated_at"])
    if d_copy.get("closed_at"):
        d_copy["closed_at"] = datetime.fromisoformat(d_copy["closed_at"])

    notes = []
    for n in d_copy.get("notes", []):
        notes.append(
            CaseNote(
                id=n["id"],
                case_id=n["case_id"],
                author=n["author"],
                content=n["content"],
                created_at=datetime.fromisoformat(n["created_at"]),
            )
        )
    d_copy["notes"] = notes

    timeline = []
    for e in d_copy.get("timeline", []):
        timeline.append(
            CaseEvent(
                event_type=e["event_type"],
                description=e["description"],
                actor=e["actor"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
                metadata=e.get("metadata", {}),
            )
        )
    d_copy["timeline"] = timeline

    return Case(**d_copy)


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
        self._cases = RedisStore("case")

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

        self._cases.set(case.id, _case_to_dict(case))
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
        self._cases.set(case.id, _case_to_dict(case))
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

        self._cases.set(case.id, _case_to_dict(case))
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
        self._cases.set(case.id, _case_to_dict(case))
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

        self._cases.set(case.id, _case_to_dict(case))
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
        val = self._cases.get(case_id)
        return _dict_to_case(val) if val else None

    def get_cases(
        self,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        limit: int = 50,
    ) -> list[Case]:
        """Retrieve cases with optional filters."""
        raw_vals = self._cases.list_values()
        cases = [_dict_to_case(v) for v in raw_vals]
        if status:
            cases = [c for c in cases if c.status == status]
        if priority:
            cases = [c for c in cases if c.priority == priority]
        return sorted(cases, key=lambda c: c.created_at, reverse=True)[:limit]

    # ── Private helpers ────────────────────────

    def _get_case(self, case_id: str) -> Case:
        val = self._cases.get(case_id)
        if not val:
            raise ValueError(f"Case not found: {case_id}")
        return _dict_to_case(val)
