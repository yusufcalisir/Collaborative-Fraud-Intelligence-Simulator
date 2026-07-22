"""Unit test suite for High-Performance Bidirectional Streaming gRPC Transport Layer."""

from __future__ import annotations

import time
import pytest

from app.infrastructure.grpc.client import GRPCBankClient
from app.infrastructure.grpc.server import GRPCServerManager
from app.infrastructure.grpc.servicer import FederatedLearningServicer
from app.infrastructure.grpc.types import (
    ClientHeartbeat,
    CoordinatorCommand,
)


@pytest.mark.asyncio
async def test_grpc_client_registration() -> None:
    """Verifies client node gRPC registration and session token issuance."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    response = await client.register(
        bank_id="bank_alpha",
        bank_name="Alpha International Bank",
        cert_fingerprint="SHA256:112233445566",
    )

    assert response.is_accepted is True
    assert response.session_token.startswith("grpc_sess_")
    assert 0 <= response.assigned_cluster_id <= 3
    assert client.session_token == response.session_token


@pytest.mark.asyncio
async def test_grpc_bidirectional_heartbeat_stream() -> None:
    """Verifies bidirectional streaming heartbeats yielding coordinator commands."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    async def sample_heartbeats():
        yield ClientHeartbeat(
            bank_id="bank_alpha",
            timestamp=int(time.time()),
            cpu_utilization=15.4,
            memory_utilization=42.0,
            local_dataset_size=10000,
        )
        yield ClientHeartbeat(
            bank_id="bank_alpha",
            timestamp=int(time.time()) + 1,
            cpu_utilization=22.1,
            memory_utilization=45.5,
            local_dataset_size=10000,
        )

    statuses = []
    async for status in client.send_heartbeats(sample_heartbeats()):
        statuses.append(status)

    assert len(statuses) == 2
    assert statuses[0].command in (CoordinatorCommand.START_TRAINING, CoordinatorCommand.IDLE)
    assert statuses[0].global_model_version == "v1.0"


@pytest.mark.asyncio
async def test_grpc_stream_model_parameters() -> None:
    """Verifies client-streaming chunked parameter uploads and payload reassembly."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    # 3.5 KB mock encrypted weights payload
    mock_payload = b"ENCRYPTED_PYTORCH_WEIGHTS_DATA_BLOCK_" * 100

    ack = await client.upload_model_parameters(
        bank_id="bank_beta",
        round_id=5,
        encrypted_weights_bytes=mock_payload,
        chunk_size=1024,
    )

    assert ack.received is True
    assert "Successfully aggregated" in ack.status_message
    assert str(len(mock_payload)) in ack.status_message


@pytest.mark.asyncio
async def test_grpc_download_global_model_chunks() -> None:
    """Verifies server-streaming global model download and SHA256 chunk validation."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    model_bytes = await client.download_global_model(bank_id="bank_gamma", version="latest")

    assert len(model_bytes) > 0
    assert model_bytes == servicer.global_models["latest"]


@pytest.mark.asyncio
async def test_grpc_server_lifecycle() -> None:
    """Verifies GRPCServerManager start and stop lifecycle calls."""
    server_mgr = GRPCServerManager(port=50055)
    await server_mgr.start()
    assert server_mgr.is_running is True

    await server_mgr.stop()
    assert server_mgr.is_running is False
