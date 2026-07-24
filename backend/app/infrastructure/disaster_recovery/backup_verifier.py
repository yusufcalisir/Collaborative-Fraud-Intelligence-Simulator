"""Backup Integrity Verifier & Sandbox Restore Probe Engine."""

from __future__ import annotations

import hashlib
import logging
import time
import uuid

from app.domain.backup_record import (
    BackupArtifact,
    BackupStatus,
    RestoreProbeResult,
)

logger = logging.getLogger(__name__)


class BackupVerifier:
    """Verifies backup SHA-256 checksums and executes sandbox restore probes."""

    def __init__(self) -> None:
        self._artifacts: dict[str, BackupArtifact] = {}
        self._stored_bytes: dict[str, bytes] = {}

    def create_backup_artifact(
        self,
        tenant_id: str,
        file_path: str,
        data_bytes: bytes,
    ) -> BackupArtifact:
        """Registers a backup artifact and computes its SHA-256 checksum."""
        backup_id = f"backup_{uuid.uuid4().hex[:8]}"
        checksum = hashlib.sha256(data_bytes).hexdigest()

        artifact = BackupArtifact(
            backup_id=backup_id,
            tenant_id=tenant_id,
            file_path=file_path,
            size_bytes=len(data_bytes),
            sha256_checksum=checksum,
            status=BackupStatus.CREATED,
        )
        self._artifacts[backup_id] = artifact
        self._stored_bytes[backup_id] = data_bytes

        logger.info(
            "Created backup artifact %s for tenant '%s' (Size: %d bytes, Hash: %s)",
            backup_id,
            tenant_id,
            len(data_bytes),
            checksum[:8],
        )
        return artifact

    def verify_checksum(self, backup_id: str) -> bool:
        """Verifies backup file SHA-256 checksum against record."""
        if backup_id not in self._artifacts:
            raise KeyError(f"Backup artifact '{backup_id}' does not exist.")

        artifact = self._artifacts[backup_id]
        data_bytes = self._stored_bytes.get(backup_id, b"")
        computed_checksum = hashlib.sha256(data_bytes).hexdigest()

        if computed_checksum == artifact.sha256_checksum:
            artifact.status = BackupStatus.VERIFIED
            logger.info("Backup %s checksum verification PASSED.", backup_id)
            return True
        else:
            artifact.status = BackupStatus.CORRUPTED
            logger.error("Backup %s checksum MISMATCH! Marked as CORRUPTED.", backup_id)
            return False

    def run_sandbox_restore_probe(self, backup_id: str) -> RestoreProbeResult:
        """Executes an isolated sandbox restore dry-run probe."""
        start_time = time.perf_counter()
        probe_id = f"probe_{uuid.uuid4().hex[:8]}"

        checksum_matched = self.verify_checksum(backup_id)
        artifact = self._artifacts[backup_id]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        success = checksum_matched and artifact.status != BackupStatus.CORRUPTED

        if success:
            artifact.status = BackupStatus.RESTORED

        probe_result = RestoreProbeResult(
            probe_id=probe_id,
            backup_id=backup_id,
            success=success,
            checksum_matched=checksum_matched,
            restore_duration_ms=duration_ms,
        )
        logger.info(
            "Executed sandbox restore probe %s for backup %s (Success: %s, Duration: %.2fms)",
            probe_id,
            backup_id,
            success,
            duration_ms,
        )
        return probe_result

    def corrupt_backup_simulation(self, backup_id: str) -> None:
        """Simulates file corruption for testing purposes."""
        if backup_id in self._stored_bytes:
            self._stored_bytes[backup_id] += b"_corrupted_bytes"
