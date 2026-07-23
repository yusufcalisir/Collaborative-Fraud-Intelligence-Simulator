"""Configuration schema for Standalone Bank Client Daemon (cfi-bank-client)."""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003

from pydantic import BaseModel, Field


class ClientDaemonConfig(BaseModel):
    """Configuration model for cfi-bank-client daemon."""

    bank_id: str = Field(
        default_factory=lambda: os.getenv("BANK_ID", "bank_alpha"),
        description="Unique identifier for participating bank node",
    )
    bank_name: str = Field(
        default="Alpha Bank Corp", description="Human readable bank institution name"
    )
    coordinator_host: str = Field(
        default_factory=lambda: os.getenv("COORDINATOR_URL", "localhost:50051").split(":")[0],
        description="Central coordinator gRPC hostname",
    )
    coordinator_port: int = Field(
        default_factory=lambda: int(
            os.getenv("COORDINATOR_URL", "localhost:50051").split(":")[1]
            if ":" in os.getenv("COORDINATOR_URL", "")
            else "50051"
        ),
        description="Central coordinator gRPC target port",
    )
    mtls_enabled: bool = Field(default=True, description="Enable mutual TLS X.509 authentication")
    client_cert_path: str | Path | None = Field(
        default_factory=lambda: os.getenv("BANK_CERT_PATH", None),
        description="Path to client certificate file",
    )
    client_key_path: str | Path | None = Field(
        default_factory=lambda: os.getenv("BANK_KEY_PATH", None),
        description="Path to client private key file",
    )
    ca_cert_path: str | Path | None = Field(
        default_factory=lambda: os.getenv("CA_CERT_PATH", None),
        description="Path to trusted root CA certificate",
    )
    vault_dir: str | Path = Field(
        default="./data/vault", description="Encrypted local storage vault directory"
    )
    vault_passphrase: str = Field(
        default="cfi_secure_vault_phrase_2026", description="Passphrase for local vault"
    )
    max_retries: int = Field(
        default=10, description="Max reconnection retries for exponential backoff"
    )
    initial_backoff_sec: float = Field(default=1.0, description="Initial backoff delay in seconds")
    max_backoff_sec: float = Field(default=60.0, description="Max backoff ceiling in seconds")
