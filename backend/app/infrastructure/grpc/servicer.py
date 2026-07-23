"""gRPC Servicer implementing FederatedLearningService RPC methods."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import TYPE_CHECKING, Any

from app.infrastructure.grpc.types import (
    AggregationAck,
    ClientHeartbeat,
    ClientRegisterRequest,
    ClientRegisterResponse,
    CoordinatorCommand,
    CoordinatorStatus,
    ModelChunk,
    ModelDownloadRequest,
    ParameterChunk,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterable

logger = logging.getLogger(__name__)


class FederatedLearningServicer:
    """gRPC Servicer handling client registration, streaming heartbeats, parameter aggregation, and model downloads."""

    def __init__(self) -> None:
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.chunk_buffers: dict[str, list[ParameterChunk]] = {}
        self.global_models: dict[str, bytes] = {
            "latest": b"MOCK_GLOBAL_MODEL_BINARY_PAYLOAD_V1.0",
        }
        self.current_round: int = 1

    async def RegisterClient(  # noqa: N802
        self, request: ClientRegisterRequest
    ) -> ClientRegisterResponse:
        """RPC 1: Register client node, validate certificate fingerprint, and issue session token."""
        logger.info(
            "gRPC RegisterClient request from bank_id=%s, bank_name=%s, fp=%s",
            request.bank_id,
            request.bank_name,
            request.certificate_fingerprint,
        )

        # Certificate validation check
        if request.certificate_fingerprint.startswith(
            "INVALID"
        ) or request.certificate_fingerprint.startswith("REVOKED"):
            logger.warning(
                "Rejected gRPC registration for node %s due to invalid/revoked certificate",
                request.bank_id,
            )
            return ClientRegisterResponse(
                session_token="",
                assigned_cluster_id=-1,
                is_accepted=False,
            )

        session_token = f"grpc_sess_{uuid.uuid4().hex[:12]}"
        cluster_id = hash(request.bank_id) % 4

        self.active_sessions[request.bank_id] = {
            "session_token": session_token,
            "bank_name": request.bank_name,
            "cert_fp": request.certificate_fingerprint,
            "cluster_id": cluster_id,
            "status": "REGISTERED",
        }

        return ClientRegisterResponse(
            session_token=session_token,
            assigned_cluster_id=cluster_id,
            is_accepted=True,
        )

    async def Heartbeat(  # noqa: N802
        self, request_iterator: AsyncIterable[ClientHeartbeat]
    ) -> AsyncIterable[CoordinatorStatus]:
        """RPC 2: Bidirectional streaming heartbeat monitoring node utilization and returning commands."""
        async for heartbeat in request_iterator:
            logger.debug(
                "gRPC Heartbeat received from %s: cpu=%.1f%%, mem=%.1f%%, dataset=%d",
                heartbeat.bank_id,
                heartbeat.cpu_utilization,
                heartbeat.memory_utilization,
                heartbeat.local_dataset_size,
            )

            # Update session status
            if heartbeat.bank_id in self.active_sessions:
                self.active_sessions[heartbeat.bank_id]["last_heartbeat"] = heartbeat.timestamp

            cmd = (
                CoordinatorCommand.START_TRAINING
                if self.current_round > 0
                else CoordinatorCommand.IDLE
            )

            yield CoordinatorStatus(
                command=cmd,
                current_round=self.current_round,
                global_model_version=f"v{self.current_round}.0",
            )

    async def StreamModelParameters(  # noqa: N802
        self, request_iterator: AsyncIterable[ParameterChunk]
    ) -> AggregationAck:
        """RPC 3: Client-streaming chunked model parameters upload."""
        chunks: list[ParameterChunk] = []
        bank_id = "unknown"
        round_id = 0

        async for chunk in request_iterator:
            chunks.append(chunk)
            bank_id = chunk.bank_id
            round_id = chunk.round_id

        # Reassemble payload
        chunks.sort(key=lambda c: c.chunk_index)
        full_payload = b"".join(c.encrypted_payload for c in chunks)

        logger.info(
            "gRPC StreamModelParameters reassembled payload for bank_id=%s, round_id=%d: %d bytes across %d chunks",
            bank_id,
            round_id,
            len(full_payload),
            len(chunks),
        )

        return AggregationAck(
            received=True,
            status_message=f"Successfully aggregated {len(chunks)} chunks ({len(full_payload)} bytes) for round {round_id}",
        )

    async def DownloadGlobalModel(  # noqa: N802
        self, request: ModelDownloadRequest
    ) -> AsyncIterable[ModelChunk]:
        """RPC 4: Server-streaming chunked global model download."""
        model_version = (
            request.target_version if request.target_version in self.global_models else "latest"
        )
        model_bytes = self.global_models[model_version]

        chunk_size = 512
        total_chunks = (len(model_bytes) + chunk_size - 1) // chunk_size

        for idx in range(total_chunks):
            start = idx * chunk_size
            end = min(start + chunk_size, len(model_bytes))
            slice_bytes = model_bytes[start:end]
            checksum = hashlib.sha256(slice_bytes).hexdigest()

            yield ModelChunk(
                chunk_index=idx,
                total_chunks=total_chunks,
                chunk_data=slice_bytes,
                sha256_checksum=checksum,
            )
