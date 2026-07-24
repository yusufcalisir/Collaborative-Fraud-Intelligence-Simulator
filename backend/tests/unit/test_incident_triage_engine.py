# ruff: noqa: E402
"""Automated Unit Test Suite for SRE Incident Triage Engine & Playbooks."""

from __future__ import annotations

from app.application.services.incident_triage import IncidentTriageEngine
from app.domain.incident_playbook import IncidentCategory, IncidentSeverity


def test_incident_triage_and_sev1_classification() -> None:
    """Test incident triage and SEV1_CRITICAL classification for privacy leaks."""
    engine = IncidentTriageEngine()

    record = engine.triage_and_classify(
        category=IncidentCategory.PRIVACY_LEAK_ALERT,
        description="Differential Privacy epsilon budget exhausted on node bank_alpha",
    )
    assert record.severity == IncidentSeverity.SEV1_CRITICAL
    assert record.status == "OPEN"
    assert len(record.recommended_actions) >= 2
    assert "Isolate Compromised Node" in record.recommended_actions[0].action_name


def test_incident_triage_and_sev2_classification() -> None:
    """Test incident triage and SEV2_MAJOR classification for SLA breaches."""
    engine = IncidentTriageEngine()

    record = engine.triage_and_classify(
        category=IncidentCategory.SLA_BREACH,
        description="Monthly uptime dropped to 99.5%",
    )
    assert record.severity == IncidentSeverity.SEV2_MAJOR
    assert record.status == "OPEN"
    assert len(record.recommended_actions) >= 1


def test_incident_resolution_lifecycle() -> None:
    """Test incident lifecycle state resolution."""
    engine = IncidentTriageEngine()

    record = engine.triage_and_classify(
        category=IncidentCategory.PSI_DRIFT_SPIKE,
        description="PSI score exceeded 0.25 on merchant_category feature",
    )
    assert record.status == "OPEN"

    # Resolve incident
    resolved = engine.resolve_incident(
        incident_id=record.incident_id,
        notes="Automated retraining pipeline successfully deployed candidate model_v2.1.0",
    )
    assert resolved.status == "RESOLVED"
    assert resolved.resolution_notes is not None
