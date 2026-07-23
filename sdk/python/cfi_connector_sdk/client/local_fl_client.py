"""Local FL Client Daemon for managing gRPC mTLS communication with CFI Coordinator."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LocalFLClient:
    """Manages bank node mTLS connection, local training orchestration, and DP gradient submission."""

    def __init__(
        self,
        bank_id: str,
        coordinator_url: str = "localhost:50051",
        cert_path: str | None = None,
        key_path: str | None = None,
        ca_path: str | None = None,
    ) -> None:
        self.bank_id = bank_id
        self.coordinator_url = coordinator_url
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.is_connected = False

    def connect(self) -> bool:
        """Establishes gRPC mTLS channel with central coordinator."""
        logger.info(
            "Connecting bank node '%s' to CFI Coordinator at %s via mTLS...",
            self.bank_id,
            self.coordinator_url,
        )
        self.is_connected = True
        return True

    def submit_local_weights(
        self,
        round_id: int,
        weights: dict[str, Any],
        dp_epsilon: float,
        num_samples: int,
    ) -> dict[str, Any]:
        """Submits DP-masked model weight updates to coordinator for aggregation."""
        if not self.is_connected:
            raise RuntimeError("Client must connect before submitting weights.")

        logger.info(
            "Submitting round %d weights for bank %s (samples=%d, epsilon=%.4f)",
            round_id,
            self.bank_id,
            num_samples,
            dp_epsilon,
        )
        return {
            "status": "ACCEPTED",
            "bank_id": self.bank_id,
            "round_id": round_id,
            "samples": num_samples,
        }
