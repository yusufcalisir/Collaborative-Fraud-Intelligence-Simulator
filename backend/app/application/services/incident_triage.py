"""SRE Incident Triage and Classification Engine Service."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.domain.incident_playbook import (
    IncidentCategory,
    IncidentRecord,
    IncidentSeverity,
    PlaybookAction,
)

logger = logging.getLogger(__name__)


class IncidentTriageEngine:
    """Classifies incident severity (SEV1-SEV4) and attaches exact SRE playbook mitigation steps."""

    def __init__(self) -> None:
        self._incidents: dict[str, IncidentRecord] = {}

    def triage_and_classify(
        self,
        category: IncidentCategory,
        description: str,
        metrics: dict[str, Any] | None = None,
    ) -> IncidentRecord:
        """Triage incident alert, classifies severity, and attaches recommended SRE playbook actions."""
        severity: IncidentSeverity
        actions: list[PlaybookAction] = []

        if category in (IncidentCategory.PRIVACY_LEAK_ALERT, IncidentCategory.CONSENSUS_FAILURE):
            severity = IncidentSeverity.SEV1_CRITICAL
            actions = [
                PlaybookAction(
                    step_number=1,
                    action_name="Isolate Compromised Node",
                    command_hint="kubectl quarantine node <node-id>",
                    automated=True,
                ),
                PlaybookAction(
                    step_number=2,
                    action_name="Trigger Emergency Failover",
                    command_hint="python -m app.infrastructure.disaster_recovery.region_failover",
                    automated=True,
                ),
            ]
        elif category in (IncidentCategory.SLA_BREACH, IncidentCategory.DATA_CORRUPTION):
            severity = IncidentSeverity.SEV2_MAJOR
            actions = [
                PlaybookAction(
                    step_number=1,
                    action_name="Run Sandbox Restore Probe",
                    command_hint="python -m app.infrastructure.disaster_recovery.backup_verifier",
                    automated=True,
                ),
                PlaybookAction(
                    step_number=2,
                    action_name="Issue SLA Penalty Billing Credit",
                    command_hint="python -m app.application.services.sla_contract_engine",
                    automated=True,
                ),
            ]
        elif category == IncidentCategory.PSI_DRIFT_SPIKE:
            severity = IncidentSeverity.SEV3_MODERATE
            actions = [
                PlaybookAction(
                    step_number=1,
                    action_name="Trigger Automated Retraining Pipeline",
                    command_hint="python -m app.application.services.automated_retraining",
                    automated=True,
                ),
            ]
        else:
            severity = IncidentSeverity.SEV4_MINOR
            actions = [
                PlaybookAction(
                    step_number=1,
                    action_name="Log Audit Event",
                    command_hint="logger.info(...)",
                    automated=True,
                ),
            ]

        incident_id = f"inc_{uuid.uuid4().hex[:8]}"
        record = IncidentRecord(
            incident_id=incident_id,
            title=f"[{severity.value}] {description}",
            severity=severity,
            category=category,
            status="OPEN",
            recommended_actions=actions,
        )
        self._incidents[incident_id] = record

        logger.critical(
            "CLASSIFIED INCIDENT %s: Severity=%s, Category=%s ('%s')",
            incident_id,
            severity.value,
            category.value,
            description,
        )
        return record

    def resolve_incident(self, incident_id: str, notes: str) -> IncidentRecord:
        """Resolves an open incident with SRE resolution notes."""
        if incident_id not in self._incidents:
            raise KeyError(f"Incident '{incident_id}' does not exist.")

        record = self._incidents[incident_id]
        record.status = "RESOLVED"
        record.resolution_notes = notes

        logger.info("RESOLVED INCIDENT %s: %s", incident_id, notes)
        return record

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        """Retrieves incident record by ID."""
        return self._incidents.get(incident_id)
