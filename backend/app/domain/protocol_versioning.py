# ruff: noqa: UP042
"""Domain models for Semantic Protocol Versioning and Compatibility Matrix."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VersionNegotiationStatus(str, Enum):
    """Status enum for client-server protocol version handshake."""

    COMPATIBLE = "COMPATIBLE"
    DEGRADED_COMPATIBLE = "DEGRADED_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True)
class ProtocolVersion:
    """Semantic version representation (major.minor.patch)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> ProtocolVersion:
        """Parses semver string (e.g. '1.2.0' or 'v1.2.0') into ProtocolVersion."""
        clean = version_str.strip().lstrip("vV")
        parts = clean.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"Invalid semantic version string: '{version_str}'")
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: ProtocolVersion) -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __ge__(self, other: ProtocolVersion) -> bool:
        return not (self < other)


@dataclass
class VersionCompatibilityMatrix:
    """Evaluates client protocol version compatibility against server bounds."""

    min_supported_version: ProtocolVersion = field(default_factory=lambda: ProtocolVersion(1, 0, 0))
    max_supported_version: ProtocolVersion = field(
        default_factory=lambda: ProtocolVersion(1, 99, 99)
    )
    supported_schema_hashes: set[str] = field(default_factory=set)

    def negotiate_protocol_version(
        self,
        client_version_str: str,
        client_schema_hash: str | None = None,
    ) -> tuple[VersionNegotiationStatus, str]:
        """Evaluates client version string and schema hash against server matrix."""
        try:
            client_ver = ProtocolVersion.parse(client_version_str)
        except ValueError as exc:
            return VersionNegotiationStatus.INCOMPATIBLE, str(exc)

        # 1. Check major version incompatibility
        if client_ver.major != self.min_supported_version.major:
            return (
                VersionNegotiationStatus.INCOMPATIBLE,
                f"Client major version v{client_ver.major} does not match server major v{self.min_supported_version.major}",
            )

        # 2. Check lower bound
        if client_ver < self.min_supported_version:
            return (
                VersionNegotiationStatus.INCOMPATIBLE,
                f"Client version v{client_ver} is below minimum supported v{self.min_supported_version}",
            )

        # 3. Check upper bound
        if client_ver > self.max_supported_version:
            return (
                VersionNegotiationStatus.INCOMPATIBLE,
                f"Client version v{client_ver} exceeds maximum supported v{self.max_supported_version}",
            )

        # 4. Check schema hash if supplied
        if (
            client_schema_hash
            and self.supported_schema_hashes
            and client_schema_hash not in self.supported_schema_hashes
        ):
            return (
                VersionNegotiationStatus.DEGRADED_COMPATIBLE,
                f"Client schema hash '{client_schema_hash[:8]}' differs from server registry",
            )

        return VersionNegotiationStatus.COMPATIBLE, "OK"
