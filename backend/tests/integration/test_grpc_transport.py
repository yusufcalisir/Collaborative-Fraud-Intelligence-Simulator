"""Integration tests for gRPC Transport Layer Activation (Section 7.2)."""

from __future__ import annotations

import pytest

from app.infrastructure.grpc.client import GRPCBankClient
from app.infrastructure.grpc.server import GRPCServerManager
from app.infrastructure.grpc.servicer import FederatedLearningServicer


@pytest.mark.asyncio
async def test_grpc_mtls_handshake_succeeds() -> None:
    """Verifies gRPC client registration and session token issuance under valid mTLS cert."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    res = await client.register(
        bank_id="bank_alpha",
        bank_name="Alpha Bank Corp",
        cert_fingerprint="SHA256:valid_cert_fingerprint_hash_12345",
    )

    assert res.is_accepted
    assert res.session_token.startswith("grpc_sess_")
    assert "bank_alpha" in servicer.active_sessions


@pytest.mark.asyncio
async def test_parameter_streaming_roundtrip() -> None:
    """Verifies chunked parameter update streaming, digital signature verification, and reassembly."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    # 4 KB dummy encrypted payload
    encrypted_weights = b"ENCRYPTED_WEIGHT_PAYLOAD_" * 160

    ack = await client.upload_model_parameters(
        bank_id="bank_alpha",
        round_id=1,
        encrypted_weights_bytes=encrypted_weights,
        chunk_size=512,
    )

    assert ack.received
    assert "Successfully aggregated" in ack.status_message


@pytest.mark.asyncio
async def test_global_model_download_integrity() -> None:
    """Verifies server-side chunked global model streaming and SHA-256 integrity verification."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    model_bytes = await client.download_global_model(bank_id="bank_alpha", version="latest")

    assert model_bytes == b"MOCK_GLOBAL_MODEL_BINARY_PAYLOAD_V1.0"


@pytest.mark.asyncio
async def test_invalid_certificate_rejected() -> None:
    """Verifies that an unauthorized/invalid certificate fingerprint is rejected by the servicer."""
    servicer = FederatedLearningServicer()
    client = GRPCBankClient(servicer=servicer)

    res = await client.register(
        bank_id="bank_malicious",
        bank_name="Malicious Actor Node",
        cert_fingerprint="INVALID:unauthorized_cert_fingerprint",
    )

    assert not res.is_accepted
    assert res.session_token == ""
    assert res.assigned_cluster_id == -1


@pytest.mark.asyncio
async def test_grpc_server_manager_lifecycle() -> None:
    """Verifies GRPCServerManager start/stop lifecycle."""
    server_mgr = GRPCServerManager(port=50051)
    await server_mgr.start()
    assert server_mgr.is_running
    await server_mgr.stop()
    assert not server_mgr.is_running


