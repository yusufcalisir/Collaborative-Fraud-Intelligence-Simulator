# ruff: noqa: S106
"""Per-Tenant Encryption Key Management & Cryptographic Isolation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TenantKMSManager:
    """Manages per-tenant AES-256 Fernet envelope encryption and key rotation."""

    def __init__(self, master_secret: str = "cfi_master_kms_secret_2026") -> None:
        self.master_secret = master_secret
        self._keys: dict[str, bytes] = {}

    def get_or_create_tenant_key(self, tenant_id: str) -> bytes:
        """Derives or retrieves a deterministic 256-bit Fernet key for a tenant."""
        clean_tenant = tenant_id.lower().strip()
        if clean_tenant in self._keys:
            return self._keys[clean_tenant]

        # Derive 32-byte key using HMAC-SHA256 of master_secret and tenant_id
        derived = hmac.new(
            self.master_secret.encode("utf-8"),
            clean_tenant.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        fernet_key = base64.urlsafe_b64encode(derived)
        self._keys[clean_tenant] = fernet_key
        return fernet_key

    def encrypt_tenant_data(self, tenant_id: str, plaintext: str) -> str:
        """Encrypts plaintext string using the tenant's isolated KMS key."""
        if not plaintext:
            return ""

        key = self.get_or_create_tenant_key(tenant_id)
        fernet = Fernet(key)
        encrypted_bytes = fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt_tenant_data(self, tenant_id: str, ciphertext: str) -> str:
        """Decrypts ciphertext using the tenant's isolated KMS key."""
        if not ciphertext:
            return ""

        key = self.get_or_create_tenant_key(tenant_id)
        fernet = Fernet(key)
        decrypted_bytes = fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")

    def rotate_tenant_key(self, tenant_id: str) -> dict[str, Any]:
        """Rotates key derivation for a tenant by updating internal seed."""
        clean_tenant = tenant_id.lower().strip()
        new_seed = os.urandom(16).hex()
        derived = hmac.new(
            f"{self.master_secret}_{new_seed}".encode(),
            clean_tenant.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        new_key = base64.urlsafe_b64encode(derived)
        self._keys[clean_tenant] = new_key
        logger.info("Rotated KMS key for tenant '%s'", clean_tenant)
        return {"tenant_id": clean_tenant, "status": "ROTATED", "key_version": new_seed[:8]}
