# ruff: noqa: E402
"""Automated Unit Test Suite for Enterprise Security Compliance Engine."""

from __future__ import annotations

from app.application.services.security_compliance import (
    SecurityComplianceEngine,
    SecurityControlStatus,
)


def test_security_controls_auditing() -> None:
    """Test auditing of all enterprise SOC2, ISO27001, and GDPR security controls."""
    engine = SecurityComplianceEngine()

    controls = engine.audit_all_controls()
    assert len(controls) >= 5

    # Check SOC2 control
    soc2_controls = [c for c in controls if c.framework.value == "SOC2_TYPE_II"]
    assert len(soc2_controls) >= 2

    # Check GDPR control
    gdpr_controls = [c for c in controls if c.framework.value == "GDPR_ART_17"]
    assert len(gdpr_controls) >= 1
    assert gdpr_controls[0].status == SecurityControlStatus.PASS


def test_compliance_attestation_report_generation() -> None:
    """Test generating compliance attestation report with 100% pass score."""
    engine = SecurityComplianceEngine()

    report = engine.generate_compliance_attestation_report()
    assert report.total_controls >= 5
    assert report.passed_controls == report.total_controls
    assert report.failed_controls == 0
    assert report.compliance_score_pct == 100.0
