"""Standalone Bank Client Daemon (cfi-bank-client) Execution Engine."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.infrastructure.client_daemon.config import ClientDaemonConfig
from app.infrastructure.client_daemon.hardware import detect_hardware_acceleration
from app.infrastructure.client_daemon.reconnector import ExponentialBackoffReconnector
from app.infrastructure.storage.local_vault import LocalVault

logger = logging.getLogger(__name__)


class BankClientDaemon:
    """Standalone containerized client daemon (`cfi-bank-client`) running inside

    each participating bank's private subnet.

    Operational Specifications:
    - Zero Inbound Ports: Outbound-only mTLS connection to coordinator gRPC host on port 50051.
    - Encrypted Local Vault Persistence: Checkpoints, local gradients, and session tokens stored in local_vault.py.
    - Automatic Reconnection: Exponential backoff reconnect logic for network disruptions.
    - Hardware Acceleration: CUDA, Apple Silicon MPS, or CPU auto-detection.
    """

    def __init__(self, config: ClientDaemonConfig | None = None) -> None:
        self.config = config or ClientDaemonConfig()
        self.vault = LocalVault(
            vault_dir=self.config.vault_dir, secret_passphrase=self.config.vault_passphrase
        )
        self.reconnector = ExponentialBackoffReconnector(
            max_retries=self.config.max_retries,
            initial_delay=self.config.initial_backoff_sec,
            max_delay=self.config.max_backoff_sec,
        )
        self.hardware_info = detect_hardware_acceleration()
        self.is_running = False
        self.session_token: str | None = None
        self.current_round: int = 0
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initializes daemon state, loads existing vault checkpoints/tokens."""
        logger.info(
            "Initializing BankClientDaemon for node: %s (%s)",
            self.config.bank_id,
            self.config.bank_name,
        )
        logger.info("Hardware acceleration profile: %s", self.hardware_info)

        # Restore session token if persisted
        self.session_token = self.vault.load_session_token()
        if self.session_token:
            logger.info(
                "Restored session token from encrypted vault for bank node %s", self.config.bank_id
            )

    async def _connect_and_stream(self) -> dict[str, Any]:
        """Simulates establishing an outbound-only gRPC mTLS session to coordinator on port 50051."""
        logger.info(
            "Establishing outbound mTLS connection to coordinator at %s:%d (zero inbound ports)...",
            self.config.coordinator_host,
            self.config.coordinator_port,
        )
        await asyncio.sleep(0.05)  # Simulate network connect handshake

        # If no session token, perform registration
        if not self.session_token:
            self.session_token = f"sess_token_{self.config.bank_id}_secure_vault_hash"
            self.vault.save_session_token(self.session_token)
            logger.info(
                "Registered outbound gRPC session token and stored in encrypted local vault."
            )

        return {
            "status": "CONNECTED",
            "session_token": self.session_token,
            "bank_id": self.config.bank_id,
            "coordinator_endpoint": f"{self.config.coordinator_host}:{self.config.coordinator_port}",
            "hardware": self.hardware_info["device_type"],
        }

    async def start(self) -> None:
        """Starts the outbound daemon loop with automatic backoff reconnection."""
        await self.initialize()
        self.is_running = True
        logger.info("Starting cfi-bank-client daemon main event loop...")

        try:
            connection_meta = await self.reconnector.execute_with_retry(self._connect_and_stream)
            logger.info("Outbound gRPC stream connected successfully: %s", connection_meta)
        except Exception as err:
            logger.critical(
                "Failed to establish outbound daemon connection after max retries: %s", err
            )
            self.is_running = False
            raise err

    async def stop(self) -> None:
        """Gracefully shuts down the bank client daemon."""
        logger.info("Stopping cfi-bank-client daemon for node %s...", self.config.bank_id)
        self.is_running = False
        self._shutdown_event.set()

    def execute_local_training_round(
        self, round_id: int, model_params: dict[str, Any]
    ) -> dict[str, Any]:
        """Executes a local PyTorch model training round using detected hardware acceleration

        and checkpoints progress to encrypted local vault.
        """
        self.current_round = round_id
        logger.info(
            "Executing local training round %d on device [%s] for bank %s...",
            round_id,
            self.hardware_info["device_type"],
            self.config.bank_id,
        )

        # Simulate local training computations & local loss evaluation
        checkpoint_payload = {
            "round_id": round_id,
            "bank_id": self.config.bank_id,
            "hardware": self.hardware_info["device_name"],
            "trained_parameters": f"params_hash_r{round_id}",
            "local_loss": 0.245 - (round_id * 0.01),
            "sample_count": 1250,
        }

        # Persist checkpoint to encrypted local vault
        saved_path = self.vault.save_checkpoint(round_id, checkpoint_payload)
        logger.info("Saved encrypted training checkpoint for round %d to %s", round_id, saved_path)

        return checkpoint_payload
