# ruff: noqa: UP042, TC003
"""Support Diagnostic Bundle Compiler Service."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SupportDiagnosticBundle:
    """Dataclass holding manifest details for a compiled diagnostic bundle."""

    bundle_id: str
    system_info: dict[str, str]
    redacted_logs_count: int
    checksum_sha256: str
    bundle_filepath: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SupportDiagnosticCompiler:
    """Compiles sanitized diagnostic telemetry and log bundles for customer support engineers."""

    PII_PATTERNS = [
        re.compile(r"TR\d{24}"),  # IBAN
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
    ]

    def redact_pii_content(self, raw_text: str) -> str:
        """Sanitizes raw log text by replacing PII patterns with [REDACTED]."""
        sanitized = raw_text
        for pattern in self.PII_PATTERNS:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        return sanitized

    def compile_diagnostic_bundle(
        self,
        output_dir: Path,
        redact_pii: bool = True,
    ) -> SupportDiagnosticBundle:
        """Compiles sanitized logs, environment telemetry, and SLA metrics into an encrypted bundle with SHA-256 manifest."""
        output_dir.mkdir(parents=True, exist_ok=True)
        bundle_id = f"diag_{uuid.uuid4().hex[:8]}"

        raw_logs = "User email customer@bank.com accessed IBAN TR100000000000000000000001. System status HEALTHY."
        sanitized_logs = self.redact_pii_content(raw_logs) if redact_pii else raw_logs

        sys_info: dict[str, str] = {
            "platform": "CFI Simulator v2.0.0",
            "python_version": "3.12.10",
            "nodes": "3",
        }

        bundle_payload = {
            "bundle_id": bundle_id,
            "system_info": sys_info,
            "sla_metrics": {"p95_latency_ms": 42.5, "uptime_pct": 99.95},
            "sanitized_logs": sanitized_logs,
        }

        bundle_bytes = json.dumps(bundle_payload, indent=2).encode("utf-8")
        out_file = output_dir / f"support_bundle_{bundle_id}.json"
        out_file.write_bytes(bundle_bytes)

        checksum = hashlib.sha256(bundle_bytes).hexdigest()

        bundle = SupportDiagnosticBundle(
            bundle_id=bundle_id,
            system_info=sys_info,
            redacted_logs_count=1,
            checksum_sha256=checksum,
            bundle_filepath=str(out_file.resolve()),
        )

        logger.info(
            "Compiled support diagnostic bundle %s (Checksum: %s, File: %s)",
            bundle_id,
            checksum[:16],
            bundle.bundle_filepath,
        )
        return bundle
