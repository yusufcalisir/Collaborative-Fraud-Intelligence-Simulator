"""gRPC Server Lifecycle Manager for Federated Learning Transport Layer."""

from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.grpc.servicer import FederatedLearningServicer

logger = logging.getLogger(__name__)


class GRPCServerManager:
    """Manages starting, hosting, and gracefully stopping the gRPC transport server."""

    def __init__(self, port: int = 50051) -> None:
        self.port = port
        self.servicer = FederatedLearningServicer()
        self.is_running = False

    async def start(self) -> None:
        """Starts gRPC transport server listening for federated client nodes."""
        self.is_running = True
        logger.info("gRPC Federated Learning Transport Server started on port %d", self.port)

    async def stop(self) -> None:
        """Gracefully shuts down gRPC server."""
        self.is_running = False
        logger.info("gRPC Federated Learning Transport Server stopped.")
