# ruff: noqa: UP042
"""Domain models for Automated Backup Verification & Restore Probes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class BackupStatus(str, Enum):
    """Lifecycle status enum for database and model registry backups."""

    CREATED = "CREATED"
    VERIFIED = "VERIFIED"
    CORRUPTED = "CORRUPTED"
    RESTORED = "RESTORED"


@dataclass
class BackupArtifact:
    """Dataclass tracking a database/storage backup artifact."""

    backup_id: str
    tenant_id: str
    file_path: str
    size_bytes: int
    sha256_checksum: str
    status: BackupStatus = BackupStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class RestoreProbeResult:
    """Dataclass storing the result of an isolated sandbox restore dry-run probe."""

    probe_id: str
    backup_id: str
    success: bool
    checksum_matched: bool
    restore_duration_ms: float
    verified_at: datetime = field(default_factory=lambda: datetime.now(UTC))
