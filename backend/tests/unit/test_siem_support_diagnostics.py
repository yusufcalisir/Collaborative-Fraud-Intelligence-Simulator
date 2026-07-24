# ruff: noqa: E402, TC003
"""Automated Unit Test Suite for SIEM Log Exporter & Support Diagnostics."""

from __future__ import annotations

from pathlib import Path

from app.application.services.support_diagnostics import (
    SupportDiagnosticCompiler,
)
from app.infrastructure.logging.siem_exporter import (
    SIEMAuditEvent,
    SIEMFormat,
    SIEMLogExporter,
)


def test_siem_cef_and_json_formatting() -> None:
    """Test SIEM CEF syslog and Splunk/Datadog JSON log formatting."""
    exporter = SIEMLogExporter()
    event = SIEMAuditEvent(
        event_id="evt_889900",
        event_type="MODEL_PROMOTED",
        severity="HIGH",
        source_bank="bank_alpha",
        message="Model version model_v2.0.0 promoted to active champion.",
    )

    # 1. CEF Syslog format
    cef_str = exporter.export_event(event, format_type=SIEMFormat.CEF_SYSLOG)
    assert cef_str.startswith("CEF:0|CFI|Simulator|2.0|MODEL_PROMOTED|")
    assert "eventId=evt_889900" in cef_str
    assert "srcBank=bank_alpha" in cef_str

    # 2. Datadog JSON format
    datadog_str = exporter.export_event(event, format_type=SIEMFormat.JSON_DATADOG)
    assert '"ddsource": "cfi_simulator"' in datadog_str
    assert '"event_id": "evt_889900"' in datadog_str

    # 3. Splunk HEC format
    splunk_str = exporter.export_event(event, format_type=SIEMFormat.SPLUNK_HEC)
    assert '"sourcetype": "cfi:audit:json"' in splunk_str


def test_support_diagnostic_bundle_compilation_and_pii_redaction(tmp_path: Path) -> None:
    """Test support diagnostic bundle compilation and PII redaction."""
    compiler = SupportDiagnosticCompiler()

    # 1. PII Redaction check
    raw = "Contact admin@bank.com regarding IBAN TR100000000000000000000001."
    redacted = compiler.redact_pii_content(raw)
    assert "[REDACTED]" in redacted
    assert "admin@bank.com" not in redacted
    assert "TR100000000000000000000001" not in redacted

    # 2. Bundle compilation
    bundle = compiler.compile_diagnostic_bundle(output_dir=tmp_path, redact_pii=True)
    assert bundle.bundle_id.startswith("diag_")
    assert len(bundle.checksum_sha256) == 64
    assert Path(bundle.bundle_filepath).exists()
