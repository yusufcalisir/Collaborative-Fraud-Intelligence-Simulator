"""Encrypted Local Storage Vault for Bank Client Enclave State Persistence."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class LocalVault:
    """Provides AES-256 encrypted local storage for session tokens, local gradient states,

    and training round checkpoints inside the bank client enclave.
    """

    def __init__(
        self, vault_dir: str | Path, secret_passphrase: str = "default_vault_secret"
    ) -> None:
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self._fernet = self._derive_fernet_key(secret_passphrase)

    def _derive_fernet_key(self, passphrase: str) -> Fernet:
        """Derives a Fernet key from a passphrase using PBKDF2HMAC."""
        salt = b"cfi_bank_local_vault_salt_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
        return Fernet(key)

    def save_secret(self, key: str, value: Any) -> Path:
        """Encrypts and saves a key-value pair to disk."""
        target_file = self.vault_dir / f"{key}.enc"
        json_data = json.dumps(value).encode("utf-8")
        encrypted_bytes = self._fernet.encrypt(json_data)

        target_file.write_bytes(encrypted_bytes)
        logger.debug("Encrypted secret saved to local vault: %s", target_file)
        return target_file

    def load_secret(self, key: str, default: Any = None) -> Any:
        """Loads and decrypts a key-value pair from disk."""
        target_file = self.vault_dir / f"{key}.enc"
        if not target_file.exists():
            return default

        try:
            encrypted_bytes = target_file.read_bytes()
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode("utf-8"))
        except Exception as e:
            logger.error("Failed to decrypt secret %s from local vault: %s", key, e)
            return default

    def save_checkpoint(self, round_id: int, checkpoint_data: dict[str, Any]) -> Path:
        """Saves an encrypted training round checkpoint."""
        return self.save_secret(f"checkpoint_round_{round_id}", checkpoint_data)

    def load_checkpoint(self, round_id: int) -> dict[str, Any] | None:
        """Loads an encrypted training round checkpoint."""
        return self.load_secret(f"checkpoint_round_{round_id}", default=None)

    def save_session_token(self, token: str) -> Path:
        """Saves encrypted session token."""
        return self.save_secret("active_session_token", {"session_token": token})

    def load_session_token(self) -> str | None:
        """Loads active session token if present."""
        data = self.load_secret("active_session_token", default=None)
        return data.get("session_token") if data else None
