# ruff: noqa: UP042
"""SIEM Log Exporter (Syslog CEF / Splunk HEC / Datadog JSON)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SIEMFormat(str, Enum):
    """Supported SIEM output payload formats."""

    CEF_SYSLOG = "CEF_SYSLOG"
    JSON_DATADOG = "JSON_DATADOG"
    SPLUNK_HEC = "SPLUNK_HEC"


@dataclass
class SIEMAuditEvent:
    """Dataclass holding a structured security audit event for SIEM forwarding."""

    event_id: str
    event_type: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    source_bank: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class SIEMLogExporter:
    """Formats security audit events into Syslog CEF (Common Event Format) and JSON for SIEM ingestion."""

    def format_cef_event(self, event: SIEMAuditEvent) -> str:
        """Formats audit event into Common Event Format (CEF:0|Vendor|Product|Version|SignatureID|Name|Severity|Extension)."""
        severity_map = {"LOW": "1", "MEDIUM": "4", "HIGH": "7", "CRITICAL": "10"}
        cef_sev = severity_map.get(event.severity.upper(), "5")

        ts_str = event.timestamp.isoformat()
        cef_string = (
            f"CEF:0|CFI|Simulator|2.0|{event.event_type}|{event.message}|{cef_sev}|"
            f"eventId={event.event_id} srcBank={event.source_bank} rt={ts_str}"
        )
        return cef_string

    def export_event(
        self,
        event: SIEMAuditEvent,
        format_type: SIEMFormat = SIEMFormat.CEF_SYSLOG,
    ) -> str:
        """Exports audit event in requested SIEM payload format."""
        if format_type == SIEMFormat.CEF_SYSLOG:
            formatted = self.format_cef_event(event)
        elif format_type == SIEMFormat.JSON_DATADOG:
            formatted = json.dumps(
                {
                    "ddsource": "cfi_simulator",
                    "ddtags": f"env:production,bank:{event.source_bank}",
                    "hostname": "cfi-coordinator",
                    "message": event.message,
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "status": event.severity.lower(),
                    "timestamp": event.timestamp.isoformat(),
                },
                indent=2,
            )
        else:  # SPLUNK_HEC
            formatted = json.dumps(
                {
                    "event": {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "message": event.message,
                        "bank": event.source_bank,
                    },
                    "sourcetype": "cfi:audit:json",
                    "source": "cfi_simulator",
                },
                indent=2,
            )

        logger.info("Exported SIEM audit event %s (%s format)", event.event_id, format_type.value)
        return formatted
