"""Unit tests for Standalone Bank Client Daemon (cfi-bank-client) and Local Vault persistence."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

import pytest

from app.infrastructure.client_daemon.config import ClientDaemonConfig
from app.infrastructure.client_daemon.daemon import BankClientDaemon
from app.infrastructure.client_daemon.hardware import detect_hardware_acceleration
from app.infrastructure.client_daemon.reconnector import ExponentialBackoffReconnector
from app.infrastructure.storage.local_vault import LocalVault


def test_local_vault_encryption_and_checkpoint_persistence(tmp_path: Path) -> None:
    """Verifies AES-256 encrypted local vault secret & checkpoint save/load logic."""
    vault = LocalVault(vault_dir=tmp_path, secret_passphrase="test_secret_passphrase")

    # Test secret saving & loading
    vault.save_secret("api_key", {"key": "secret_bank_token_123"})
    loaded = vault.load_secret("api_key")
    assert loaded == {"key": "secret_bank_token_123"}

    # Test round checkpoint save & load
    checkpoint = {"round_id": 1, "loss": 0.15, "params": [0.1, 0.2, 0.3]}
    vault.save_checkpoint(round_id=1, checkpoint_data=checkpoint)
    loaded_checkpoint = vault.load_checkpoint(round_id=1)
    assert loaded_checkpoint == checkpoint

    # Test session token persistence
    vault.save_session_token("session_abc_xyz")
    assert vault.load_session_token() == "session_abc_xyz"


def test_hardware_acceleration_detector() -> None:
    """Verifies PyTorch hardware acceleration detector returns valid hardware profile."""
    hw_info = detect_hardware_acceleration()
    assert "device_type" in hw_info
    assert hw_info["device_type"] in ("cuda", "mps", "cpu")
    assert "device_name" in hw_info
    assert "core_count" in hw_info
    assert hw_info["core_count"] >= 1


def test_exponential_backoff_reconnector() -> None:
    """Verifies backoff delay computation and retry limit behavior."""
    reconnector = ExponentialBackoffReconnector(
        max_retries=3,
        initial_delay=0.1,
        max_delay=1.0,
        backoff_factor=2.0,
    )

    d1 = reconnector.compute_next_delay()
    assert 0.05 <= d1 <= 0.1

    reconnector.current_attempt = 1
    d2 = reconnector.compute_next_delay()
    assert 0.1 <= d2 <= 0.2

    reconnector.reset()
    assert reconnector.current_attempt == 0


@pytest.mark.asyncio
async def test_bank_client_daemon_lifecycle(tmp_path: Path) -> None:
    """Verifies BankClientDaemon initialization, outbound connection, training, and shutdown."""
    config = ClientDaemonConfig(
        bank_id="bank_test",
        bank_name="Test Bank",
        vault_dir=tmp_path / "vault",
    )
    daemon = BankClientDaemon(config=config)

    await daemon.start()
    assert daemon.is_running
    assert daemon.session_token is not None

    # Execute training round
    res = daemon.execute_local_training_round(round_id=1, model_params={"weights": [0.1, 0.2]})
    assert res["round_id"] == 1
    assert res["bank_id"] == "bank_test"

    # Verify checkpoint stored in vault
    checkpoint = daemon.vault.load_checkpoint(round_id=1)
    assert checkpoint is not None
    assert checkpoint["sample_count"] == 1250

    await daemon.stop()
    assert not daemon.is_running
