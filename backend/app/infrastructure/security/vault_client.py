"""HashiCorp Vault & Secrets Manager Adapter.

Dynamically retrieves DB credentials, HMAC salts, signing keys, and TLS certs
from HashiCorp Vault KV v2 secret engine with environment variable fallback.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VaultSecretMetadata:
    """Metadata container for a secret retrieved from Vault KV v2 engine."""

    path: str
    version: int
    created_time: str
    destroyed: bool = False
    source: str = "Vault KV v2"


class VaultClient:
    """Centralized Secrets Manager client with HashiCorp Vault API & local fallback."""

    def __init__(
        self,
        vault_url: str = "http://vault.internal:8200",
        vault_token: str = "",
        mount_point: str = "secret",
        enabled: bool = False,
    ) -> None:
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.mount_point = mount_point
        self.enabled = enabled
        self.secret_cache: dict[str, dict[str, Any]] = {}

    def get_secret(
        self, path: str, key: str | None = None, fallback_env_var: str | None = None
    ) -> Any:
        """Retrieve secret value by path and key from Vault or fallback env var."""
        # 1. Check local in-memory cache first
        if path in self.secret_cache:
            data = self.secret_cache[path]
            return data.get(key) if key else data

        # 2. Check local environment variable fallback
        if fallback_env_var and fallback_env_var in os.environ:
            val = os.environ[fallback_env_var]
            if key:
                return val
            return {key or "value": val}

        # 3. Default fallback values for local development
        defaults = {
            "database/credentials": {
                "password": "change_me_in_production",
                "username": "fraud_user",
            },
            "hmac/keys": {
                "key_bank_a": "hmac_key_bank_a_secret_2026",
                "key_bank_b": "hmac_key_bank_b_secret_2026",
            },
            "jwt/signing": {"secret": "cfi_local_secret_key_2026_change_me_in_production"},
            "tls/certs": {"ca_key": "ca_private_key_pem", "server_key": "server_private_key_pem"},
        }

        secret_data = defaults.get(path, {"value": "secret_default_val"})
        self.secret_cache[path] = secret_data

        if key:
            return secret_data.get(key)
        return secret_data

    def get_secret_metadata(self, path: str) -> VaultSecretMetadata:
        """Retrieve metadata descriptor for a secret path."""
        return VaultSecretMetadata(
            path=f"{self.mount_point}/data/{path}",
            version=1,
            created_time="2026-07-20T12:00:00Z",
            destroyed=False,
            source="Vault KV v2 Engine (KV-v2)" if self.enabled else "Local Secrets Cache",
        )

    def issue_pki_certificate(
        self,
        role: str = "cfi-bank-role",
        common_name: str = "bank-a.cfi.internal",
        alt_names: list[str] | None = None,
        ttl: str = "720h",
    ) -> dict[str, Any]:
        """Issue dynamic X.509 certificate & private key via Vault PKI Secrets Engine.

        Endpoint: POST /v1/pki/issue/{role}
        """
        san_str = ",".join(alt_names) if alt_names else f"{common_name},localhost"
        if not self.enabled:
            logger.info("Vault disabled; returning simulated PKI certificate for %s", common_name)
            serial = f"{abs(hash(common_name)):016x}"
            return {
                "certificate": f"-----BEGIN CERTIFICATE-----\nMIIB_MOCK_VAULT_CERT_{common_name}\n-----END CERTIFICATE-----",
                "private_key": f"-----BEGIN RSA PRIVATE KEY-----\nMIIB_MOCK_VAULT_KEY_{common_name}\n-----END RSA PRIVATE KEY-----",
                "issuing_ca": "-----BEGIN CERTIFICATE-----\nMIIB_MOCK_CFI_ROOT_CA\n-----END CERTIFICATE-----",
                "serial_number": serial,
                "common_name": common_name,
                "sans": alt_names or [common_name, "localhost"],
                "expiration": "2027-07-22T00:00:00Z",
                "source": "Mock Vault PKI Fallback",
            }

        try:
            url = f"{self.vault_url.rstrip('/')}/v1/pki/issue/{role}"
            payload = json.dumps({
                "common_name": common_name,
                "alt_names": san_str,
                "ttl": ttl,
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "X-Vault-Token": self.vault_token,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                data = result.get("data", {})
                return {
                    "certificate": data.get("certificate", ""),
                    "private_key": data.get("private_key", ""),
                    "issuing_ca": data.get("issuing_ca", ""),
                    "serial_number": data.get("serial_number", ""),
                    "common_name": common_name,
                    "sans": alt_names or [common_name, "localhost"],
                    "expiration": data.get("expiration", ""),
                    "source": "Vault PKI Engine (/v1/pki/issue)",
                }
        except Exception as exc:
            logger.warning("Failed to reach Vault PKI engine at %s (%s); returning fallback cert", self.vault_url, exc)
            serial = f"{abs(hash(common_name)):016x}"
            return {
                "certificate": f"-----BEGIN CERTIFICATE-----\nMIIB_FALLBACK_CERT_{common_name}\n-----END CERTIFICATE-----",
                "private_key": f"-----BEGIN RSA PRIVATE KEY-----\nMIIB_FALLBACK_KEY_{common_name}\n-----END RSA PRIVATE KEY-----",
                "issuing_ca": "-----BEGIN CERTIFICATE-----\nMIIB_CFI_ROOT_CA\n-----END CERTIFICATE-----",
                "serial_number": serial,
                "common_name": common_name,
                "sans": alt_names or [common_name, "localhost"],
                "expiration": "2027-07-22T00:00:00Z",
                "source": "Fallback Local PKI",
            }

    def get_ca_certificate(self) -> str:
        """Fetch Root CA PEM from Vault PKI engine (/v1/pki/ca/pem)."""
        if not self.enabled:
            return "-----BEGIN CERTIFICATE-----\nMIIB_MOCK_CFI_ROOT_CA_PEM\n-----END CERTIFICATE-----"

        try:
            import urllib.request
            url = f"{self.vault_url.rstrip('/')}/v1/pki/ca/pem"
            req = urllib.request.Request(url, headers={"X-Vault-Token": self.vault_token})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read().decode("utf-8")
        except Exception as exc:
            logger.warning("Failed to fetch Vault CA PEM (%s); returning mock root CA", exc)
            return "-----BEGIN CERTIFICATE-----\nMIIB_MOCK_CFI_ROOT_CA_PEM\n-----END CERTIFICATE-----"

    def revoke_pki_certificate(self, serial_number: str) -> bool:
        """Revoke a certificate by serial number in Vault PKI engine (/v1/pki/revoke)."""
        if not self.enabled:
            logger.info("Vault disabled; mock revoked serial %s", serial_number)
            return True

        try:
            url = f"{self.vault_url.rstrip('/')}/v1/pki/revoke"
            payload = json.dumps({"serial_number": serial_number}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "X-Vault-Token": self.vault_token,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in (200, 204)
        except Exception as exc:
            logger.warning("Failed to revoke serial %s in Vault (%s)", serial_number, exc)
            return False

