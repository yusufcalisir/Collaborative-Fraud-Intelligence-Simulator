"""High-performance gRPC client driver for bank node operations."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from app.infrastructure.grpc.servicer import FederatedLearningServicer
from app.infrastructure.grpc.types import (
    AggregationAck,
    ClientHeartbeat,
    ClientRegisterRequest,
    ClientRegisterResponse,
    CoordinatorStatus,
    ModelChunk,
    ModelDownloadRequest,
    ParameterChunk,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterable

logger = logging.getLogger(__name__)


class GRPCBankClient:
    """High-performance gRPC client transport driver for federated bank nodes."""

    def __init__(self, servicer: FederatedLearningServicer | None = None) -> None:
        self.servicer = servicer or FederatedLearningServicer()
        self.session_token: str | None = None

    async def register(
        self,
        bank_id: str,
        bank_name: str,
        cert_fingerprint: str = "SHA256:abcd1234efgh5678",
    ) -> ClientRegisterResponse:
        """Registers bank node with gRPC coordinator servicer."""
        req = ClientRegisterRequest(
            bank_id=bank_id,
            bank_name=bank_name,
            certificate_fingerprint=cert_fingerprint,
        )
        res = await self.servicer.RegisterClient(req)
        if res.is_accepted:
            self.session_token = res.session_token
        return res

    async def send_heartbeats(
        self,
        heartbeat_stream: AsyncIterable[ClientHeartbeat],
    ) -> AsyncGenerator[CoordinatorStatus, None]:
        """Streams client heartbeats and receives coordinator command stream."""
        async for status in self.servicer.Heartbeat(heartbeat_stream):
            yield status

    async def upload_model_parameters(
        self,
        bank_id: str,
        round_id: int,
        encrypted_weights_bytes: bytes,
        chunk_size: int = 1024,
    ) -> AggregationAck:
        """Splits model parameters into chunks and streams over gRPC transport layer."""
        total_chunks = (len(encrypted_weights_bytes) + chunk_size - 1) // chunk_size

        async def chunk_generator() -> AsyncGenerator[ParameterChunk, None]:
            for idx in range(total_chunks):
                start = idx * chunk_size
                end = min(start + chunk_size, len(encrypted_weights_bytes))
                chunk_payload = encrypted_weights_bytes[start:end]
                signature = hashlib.sha256(chunk_payload).digest()

                yield ParameterChunk(
                    bank_id=bank_id,
                    round_id=round_id,
                    chunk_index=idx,
                    total_chunks=total_chunks,
                    encrypted_payload=chunk_payload,
                    digital_signature=signature,
                )

        return await self.servicer.StreamModelParameters(chunk_generator())

    async def download_global_model(
        self,
        bank_id: str,
        version: str = "latest",
    ) -> bytes:
        """Downloads global model binary over server-streaming gRPC channel and verifies checksums."""
        req = ModelDownloadRequest(bank_id=bank_id, target_version=version)
        downloaded_chunks: list[ModelChunk] = []

        async for chunk in self.servicer.DownloadGlobalModel(req):
            expected_checksum = hashlib.sha256(chunk.chunk_data).hexdigest()
            if chunk.sha256_checksum != expected_checksum:
                raise ValueError(f"Checksum mismatch on gRPC model chunk {chunk.chunk_index}")
            downloaded_chunks.append(chunk)

        downloaded_chunks.sort(key=lambda c: c.chunk_index)
        return b"".join(c.chunk_data for c in downloaded_chunks)
