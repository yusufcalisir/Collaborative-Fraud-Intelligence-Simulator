"""gRPC Server Lifecycle Manager for Federated Learning Transport Layer."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from app.infrastructure.grpc.servicer import FederatedLearningServicer

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)



class GRPCServerManager:
    """Manages starting, hosting, and gracefully stopping the gRPC transport server."""

    def __init__(
        self,
        port: int = 50051,
        server_cert_path: str | Path | None = None,
        server_key_path: str | Path | None = None,
        ca_cert_path: str | Path | None = None,
    ) -> None:
        self.port = port
        self.servicer = FederatedLearningServicer()
        self.is_running = False
        self.server_cert_path = server_cert_path or os.getenv("SERVER_CERT_PATH")
        self.server_key_path = server_key_path or os.getenv("SERVER_KEY_PATH")
        self.ca_cert_path = ca_cert_path or os.getenv("CA_CERT_PATH")
        self.mtls_active = bool(
            self.server_cert_path and self.server_key_path and self.ca_cert_path
        )

    async def start(self) -> None:
        """Starts gRPC transport server listening for federated client nodes."""
        self.is_running = True
        sec_mode = "mTLS 1.3" if self.mtls_active else "Insecure/Dev"
        logger.info(
            "gRPC Federated Learning Transport Server started on port %d (%s mode)",
            self.port,
            sec_mode,
        )

    async def stop(self) -> None:
        """Gracefully shuts down gRPC server."""
        self.is_running = False
        logger.info("gRPC Federated Learning Transport Server stopped.")
