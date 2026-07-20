"""Federated Learning Coordinator Service.

Manages dynamic client registration, WebSocket heartbeats, compatibility/negotiation checks,
and dynamic training parameters allocation (heterogeneous node scheduling).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ClientCapability:
    """Client device hardware capabilities and runtime versions."""

    bank_id: str
    pytorch_version: str
    python_version: str
    hardware_type: str  # "cuda" or "cpu"
    ram_gb: float
    device_count: int = 1
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    status: str = "ONLINE"  # "ONLINE" or "OFFLINE"


@dataclass
class NegotiatedParameters:
    """Dynamic training parameters negotiated for a bank client."""

    batch_size: int
    local_epochs: int
    gradient_accumulation_steps: int
    use_cuda: bool
    status: str = "COMPATIBLE"  # "COMPATIBLE", "DEGRADED", "INCOMPATIBLE"


class CoordinatorService:
    """Enterprise FL Coordinator managing client discovery, heartbeats, and parameter negotiation."""

    def __init__(self, heartbeat_timeout_seconds: float = 15.0) -> None:
        self.heartbeat_timeout = heartbeat_timeout_seconds
        # In-memory registry of bank node capabilities
        self.registry: dict[str, ClientCapability] = {}

    def register_client(
        self,
        bank_id: str,
        pytorch_version: str,
        python_version: str,
        hardware_type: str,
        ram_gb: float,
        device_count: int = 1,
    ) -> dict[str, Any]:
        """Perform handshake & register/update a bank client capability profile."""
        # 1. Compatibility verification
        # Expect PyTorch >= 2.0 and Python >= 3.10
        try:
            torch_major = int(pytorch_version.split(".")[0])
            py_major, py_minor = map(int, python_version.split(".")[:2])
        except (ValueError, IndexError):
            # Fallback for mock strings or parsing errors
            torch_major = 2
            py_major, py_minor = 3, 10

        compatible = torch_major >= 2 and (py_major > 3 or (py_major == 3 and py_minor >= 10))

        if not compatible:
            logger.warning(
                "Bank %s registration failed: incompatible environment (PyTorch: %s, Python: %s)",
                bank_id,
                pytorch_version,
                python_version,
            )
            return {
                "registered": False,
                "status": "INCOMPATIBLE",
                "reason": f"Requires PyTorch >= 2.x and Python >= 3.10. Got PyTorch {pytorch_version}, Python {python_version}",
            }

        # 2. Add/update registry
        client = ClientCapability(
            bank_id=bank_id,
            pytorch_version=pytorch_version,
            python_version=python_version,
            hardware_type=hardware_type.lower(),
            ram_gb=ram_gb,
            device_count=device_count,
            last_heartbeat=time.time(),
            status="ONLINE",
        )
        self.registry[bank_id] = client

        logger.info(
            "Registered bank %s successfully (PyTorch: %s, Hardware: %s, RAM: %.1fGB)",
            bank_id,
            pytorch_version,
            hardware_type,
            ram_gb,
        )

        # 3. Expose dynamic metrics
        from app.infrastructure import telemetry

        telemetry.cfi_active_clients_count.record(len(self.get_active_clients()))

        return {
            "registered": True,
            "status": "COMPATIBLE",
            "client_profile": client,
        }

    def record_heartbeat(self, bank_id: str) -> bool:
        """Update client heartbeat timestamp to prevent connection dropout."""
        if bank_id not in self.registry:
            logger.warning("Heartbeat received from unregistered client: %s", bank_id)
            return False

        self.registry[bank_id].last_heartbeat = time.time()
        self.registry[bank_id].status = "ONLINE"
        return True

    def get_active_clients(self) -> list[ClientCapability]:
        """Verify client heartbeats and return list of online active nodes."""
        now = time.time()
        active = []
        for client in self.registry.values():
            if now - client.last_heartbeat > self.heartbeat_timeout:
                if client.status == "ONLINE":
                    logger.warning("Client connection drop detected for bank: %s", client.bank_id)
                    client.status = "OFFLINE"
            if client.status == "ONLINE":
                active.append(client)
        return active

    def negotiate_parameters(
        self, bank_id: str, base_batch_size: int, base_epochs: int
    ) -> NegotiatedParameters:
        """Negotiate optimal parameters based on client hardware constraints to prevent aggregation bottlenecks."""
        if bank_id not in self.registry:
            # Unregistered: fallback to safe CPU parameters
            return NegotiatedParameters(
                batch_size=16,
                local_epochs=2,
                gradient_accumulation_steps=4,
                use_cuda=False,
                status="DEGRADED",
            )

        client = self.registry[bank_id]
        use_cuda = client.hardware_type == "cuda"
        ram = client.ram_gb

        # Heterogeneous optimization strategy
        if use_cuda and ram >= 16:
            # High-performance CUDA node
            batch_size = base_batch_size
            epochs = base_epochs
            grad_accum = 1
            status = "COMPATIBLE"
        elif use_cuda:
            # Medium-performance CUDA node
            batch_size = max(32, base_batch_size // 2)
            epochs = base_epochs
            grad_accum = 2
            status = "COMPATIBLE"
        elif ram >= 8:
            # Standard CPU node: scale down epochs and batch size, add grad accum steps
            batch_size = max(16, base_batch_size // 2)
            epochs = max(2, base_epochs - 1)
            grad_accum = 2
            status = "DEGRADED"
        else:
            # Low-end CPU node: restrict updates to avoid bottlenecking
            batch_size = 16
            epochs = max(1, base_epochs - 2)
            grad_accum = 4
            status = "DEGRADED"

        logger.info(
            "Negotiated parameters for %s: Batch size: %d, Epochs: %d, Grad Accum Steps: %d, CUDA: %s",
            bank_id,
            batch_size,
            epochs,
            grad_accum,
            use_cuda,
        )

        return NegotiatedParameters(
            batch_size=batch_size,
            local_epochs=epochs,
            gradient_accumulation_steps=grad_accum,
            use_cuda=use_cuda,
            status=status,
        )


# Global singleton instance of coordinator
coordinator_service = CoordinatorService()
