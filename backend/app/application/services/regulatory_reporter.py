"""Regulatory Reporter Service.

Generates Suspicious Activity Report (SAR) XML documents conforming to
FinCEN BSA e-filing specifications.
"""

from __future__ import annotations

import xml.dom.minidom
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.entities_phase2 import Case


class RegulatoryReporterService:
    """Service to compile and serialize regulatory filings in standard formats."""

    @staticmethod
    def generate_fincen_sar_xml(case: Case, alerts: list[Any]) -> str:
        """Generate a FinCEN-compliant Suspicious Activity Report XML payload."""
        # Root element with FinCEN namespace declarations
        root = ET.Element(
            "EFilingSubmission",
            {
                "xmlns": "http://www.fincen.gov/spec/bsa",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "http://www.fincen.gov/spec/bsa bsa_efiling_sar.xsd",
            },
        )

        # Header block
        header = ET.SubElement(root, "SubmissionHeader")
        ET.SubElement(header, "ActivityType").text = "SAR"
        ET.SubElement(header, "SubmissionType").text = "New"
        ET.SubElement(header, "CreatedTimestamp").text = datetime.now(UTC).isoformat()

        # Activity block
        activity = ET.SubElement(root, "Activity")
        ET.SubElement(activity, "ActivityID").text = case.id
        ET.SubElement(activity, "ActivityStatus").text = case.status.value

        # Reporting Institution
        inst = ET.SubElement(activity, "ReportingInstitution")
        ET.SubElement(inst, "InstitutionName").text = "Consortium AML Joint Investigation Unit"
        ET.SubElement(inst, "TINType").text = "EIN"

        # Subject Information
        subjects = ET.SubElement(activity, "Subjects")
        entity_hashes = set()
        for alert in alerts:
            for entity_id in alert.involved_entity_ids:
                entity_hashes.add(entity_id)

        for eh in sorted(list(entity_hashes)):
            subject = ET.SubElement(subjects, "Subject")
            ET.SubElement(subject, "EntityPrivacyHash").text = eh

        # Suspicious Activity Details
        details = ET.SubElement(activity, "SuspiciousActivityDetails")
        ET.SubElement(details, "TotalRiskScore").text = f"{case.total_risk_score:.2f}"
        ET.SubElement(details, "Priority").text = case.priority.value

        alert_ids_elem = ET.SubElement(details, "AlertIds")
        for aid in sorted(case.alert_ids):
            ET.SubElement(alert_ids_elem, "AlertId").text = aid

        # Narrative Summary
        narrative = ET.SubElement(activity, "Narrative")
        ET.SubElement(narrative, "Summary").text = case.title

        # Notes block
        notes_elem = ET.SubElement(narrative, "Notes")
        for note in case.notes:
            n_elem = ET.SubElement(notes_elem, "Note")
            ET.SubElement(n_elem, "Author").text = note.author
            ET.SubElement(n_elem, "Content").text = note.content
            ET.SubElement(n_elem, "Timestamp").text = note.created_at.isoformat()

        # Timeline events block
        timeline_elem = ET.SubElement(narrative, "Timeline")
        for event in sorted(case.timeline, key=lambda e: e.timestamp):
            e_elem = ET.SubElement(timeline_elem, "Event")
            ET.SubElement(e_elem, "Type").text = event.event_type
            ET.SubElement(e_elem, "Description").text = event.description
            ET.SubElement(e_elem, "Actor").text = event.actor
            ET.SubElement(e_elem, "Timestamp").text = event.timestamp.isoformat()

        # Return pretty-formatted XML string
        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = xml.dom.minidom.parseString(raw_xml)
        return parsed.toprettyxml(indent="  ")
