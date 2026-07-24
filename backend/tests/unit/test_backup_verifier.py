# ruff: noqa: E402
"""Automated Unit Test Suite for Backup Verification & Restore Probes."""

from __future__ import annotations

from app.domain.backup_record import BackupStatus
from app.infrastructure.disaster_recovery.backup_verifier import BackupVerifier


def test_backup_artifact_creation_and_checksum_verification() -> None:
    """Test backup artifact creation and valid SHA-256 checksum verification."""
    verifier = BackupVerifier()
    payload = b"DATABASE_SNAPSHOT_BINARY_DATA_12345"

    artifact = verifier.create_backup_artifact(
        tenant_id="bank_alpha",
        file_path="storage/backups/bank_alpha_20260724.db",
        data_bytes=payload,
    )
    assert artifact.status == BackupStatus.CREATED
    assert artifact.size_bytes == len(payload)
    assert len(artifact.sha256_checksum) == 64

    # Verify checksum
    assert verifier.verify_checksum(artifact.backup_id) is True
    assert artifact.status == BackupStatus.VERIFIED


def test_corrupted_backup_detection() -> None:
    """Test detection and flagging of corrupted/tampered backup files."""
    verifier = BackupVerifier()
    payload = b"MODEL_REGISTRY_BACKUP_WEIGHTS_V2"

    artifact = verifier.create_backup_artifact(
        tenant_id="bank_beta",
        file_path="storage/backups/model_v2.pt",
        data_bytes=payload,
    )

    # Simulate byte corruption
    verifier.corrupt_backup_simulation(artifact.backup_id)

    # Verify checksum fails and marks CORRUPTED
    assert verifier.verify_checksum(artifact.backup_id) is False
    assert artifact.status == BackupStatus.CORRUPTED


def test_sandbox_restore_probe_execution() -> None:
    """Test sandbox restore probe dry-run execution."""
    verifier = BackupVerifier()
    payload = b"SANITY_RESTORE_PROBE_VALID_SNAPSHOT"

    artifact = verifier.create_backup_artifact(
        tenant_id="bank_gamma",
        file_path="storage/backups/bank_gamma_probe.db",
        data_bytes=payload,
    )

    # Execute sandbox restore probe
    probe = verifier.run_sandbox_restore_probe(artifact.backup_id)
    assert probe.backup_id == artifact.backup_id
    assert probe.success is True
    assert probe.checksum_matched is True
    assert probe.restore_duration_ms > 0
    assert artifact.status == BackupStatus.RESTORED
