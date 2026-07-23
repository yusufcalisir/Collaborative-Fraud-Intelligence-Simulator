# ruff: noqa: E402
"""Automated Unit Test Suite for Federated Protocol Compatibility Negotiator."""

from __future__ import annotations

from app.domain.protocol_versioning import (
    ProtocolVersion,
    VersionCompatibilityMatrix,
    VersionNegotiationStatus,
)
from app.infrastructure.grpc.version_interceptor import (
    PROTOCOL_VERSION_HEADER_KEY,
    SCHEMA_HASH_HEADER_KEY,
    ProtocolVersionInterceptor,
)


def test_protocol_version_parsing_and_semver_comparison() -> None:
    """Test semantic version parsing and comparison operators."""
    v1 = ProtocolVersion.parse("1.0.0")
    v2 = ProtocolVersion.parse("v1.2.5")
    v3 = ProtocolVersion.parse("2.0.0")

    assert str(v1) == "1.0.0"
    assert str(v2) == "1.2.5"
    assert v1 < v2
    assert v2 < v3
    assert v3 >= v1


def test_version_compatibility_negotiation() -> None:
    """Test protocol version negotiation against matrix bounds."""
    matrix = VersionCompatibilityMatrix(
        min_supported_version=ProtocolVersion(1, 2, 0),
        max_supported_version=ProtocolVersion(1, 99, 99),
        supported_schema_hashes={"hash_abc123"},
    )

    # 1. Compatible client version
    status_ok, reason_ok = matrix.negotiate_protocol_version("1.3.0", "hash_abc123")
    assert status_ok == VersionNegotiationStatus.COMPATIBLE
    assert reason_ok == "OK"

    # 2. Out-of-bounds lower client version (v1.0.0 < v1.2.0)
    status_low, reason_low = matrix.negotiate_protocol_version("1.0.0")
    assert status_low == VersionNegotiationStatus.INCOMPATIBLE
    assert "is below minimum supported" in reason_low

    # 3. Major version mismatch
    status_major, reason_major = matrix.negotiate_protocol_version("2.0.0")
    assert status_major == VersionNegotiationStatus.INCOMPATIBLE
    assert "does not match server major" in reason_major

    # 4. Unknown schema hash yields DEGRADED_COMPATIBLE
    status_deg, reason_deg = matrix.negotiate_protocol_version("1.3.0", "unknown_schema_xyz")
    assert status_deg == VersionNegotiationStatus.DEGRADED_COMPATIBLE
    assert "differs from server registry" in reason_deg


def test_grpc_protocol_version_interceptor_metadata_extraction() -> None:
    """Test gRPC interceptor header extraction and negotiation call."""
    interceptor = ProtocolVersionInterceptor()

    class FakeHandlerCallDetails:
        def __init__(self, headers: list[tuple[str, str]]) -> None:
            self.invocation_metadata = headers

    # 1. Call details with valid header
    details_valid = FakeHandlerCallDetails(
        [(PROTOCOL_VERSION_HEADER_KEY, "1.0.0"), (SCHEMA_HASH_HEADER_KEY, "hash_123")]
    )

    called = False

    def fake_continuation(details: FakeHandlerCallDetails) -> str:
        nonlocal called
        called = True
        return "RPC_SUCCESS"

    result = interceptor.intercept_service(fake_continuation, details_valid)  # type: ignore[arg-type]
    assert called is True
    assert result == "RPC_SUCCESS"
