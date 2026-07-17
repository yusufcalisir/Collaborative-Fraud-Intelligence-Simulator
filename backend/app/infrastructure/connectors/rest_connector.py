"""HTTP REST Bank Connector implementing the connector port."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from app.application.interfaces.bank_connector import BankConnectorInterface

if TYPE_CHECKING:
    from app.domain.value_objects import ModelWeights

logger = logging.getLogger(__name__)


class RESTBankConnector(BankConnectorInterface):
    """Sends FL commands to bank nodes over HTTP REST APIs."""

    def __init__(
        self,
        base_url: str,
        auth_type: str = "none",
        api_key: str = "",
        oauth_client_id: str = "",
        oauth_client_secret: str = "",
        oauth_token_url: str = "",
        client_cert_path: str = "",
        client_key_path: str = "",
    ) -> None:
        self.base_url = base_url
        self.auth_type = auth_type
        self.api_key = api_key
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.oauth_token_url = oauth_token_url
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path
        self._token: str | None = None
        from app.config import get_settings

        self.settings = get_settings()

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_type == "apikey" and self.api_key:
            headers["X-API-KEY"] = self.api_key
        elif self.auth_type == "oauth2":
            token = self._get_oauth2_token()
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _sign_payload(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> tuple[bytes, dict[str, str]]:
        import json

        body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        secret = self.settings.payload_signing_secret
        if not secret:
            return body_bytes, headers
        import hashlib
        import hmac
        import time

        timestamp = str(time.time())
        sign_data = timestamp.encode("utf-8") + b"." + body_bytes
        signature = hmac.new(secret.encode("utf-8"), sign_data, hashlib.sha256).hexdigest()
        new_headers = dict(headers)
        new_headers["X-Payload-Signature"] = signature
        new_headers["X-Payload-Timestamp"] = timestamp
        return body_bytes, new_headers

    def _get_oauth2_token(self) -> str:
        if self._token:
            return self._token
        logger.info("Requesting OAuth2 client credentials token from %s", self.oauth_token_url)
        try:
            # Send standard client credentials request
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.settings.oauth_client_id,
                "client_secret": self.settings.oauth_client_secret,
            }
            with httpx.Client() as client:
                resp = client.post(self.oauth_token_url, data=payload, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    self._token = data.get("access_token")
                    if self._token:
                        return self._token
                logger.warning(
                    "OAuth2 server returned status %d. Falling back to placeholder token.",
                    resp.status_code,
                )
        except Exception as exc:
            logger.warning(
                "Failed to fetch OAuth2 token from %s: %s. Falling back to placeholder token.",
                self.oauth_token_url,
                exc,
            )
        self._token = "mock_oauth2_access_token_placeholder"
        return self._token

    def _get_client(self) -> httpx.Client:
        import os

        # Mutual TLS support hook
        if self.auth_type == "mtls" and self.client_cert_path and self.client_key_path:
            if os.path.exists(self.client_cert_path) and os.path.exists(self.client_key_path):
                logger.info("Configuring Mutual TLS with cert: %s", self.client_cert_path)
                return httpx.Client(cert=(self.client_cert_path, self.client_key_path))
            else:
                logger.warning(
                    "mTLS configured but certificate/key files do not exist: %s, %s. Using default client.",
                    self.client_cert_path,
                    self.client_key_path,
                )
        return httpx.Client()

    def initialize(
        self,
        bank_id: str,
        num_transactions: int,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Trigger initialization over HTTP REST endpoint."""
        url = f"{self.base_url}/api/v1/bank-client/initialize"
        payload = {
            "bank_id": bank_id,
            "num_transactions": num_transactions,
            "seed": seed,
        }
        body_bytes, headers = self._sign_payload(payload, self._get_headers())
        with self._get_client() as client:
            resp = client.post(url, content=body_bytes, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    def train(
        self,
        bank_id: str,
        weights: ModelWeights,
        learning_rate: float,
        batch_size: int,
        epochs: int,
        enable_dp: bool,
        dp_epsilon: float,
        dp_delta: float,
        dp_max_grad_norm: float,
        correlation_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Trigger model training over HTTP REST endpoint."""
        url = f"{self.base_url}/api/v1/bank-client/train"
        schema_weights = {
            "layer_shapes": [list(shape) for shape in weights.layer_shapes],
            "flat_weights": weights.flat_weights,
        }
        payload = {
            "weights": schema_weights,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "epochs": epochs,
            "enable_dp": enable_dp,
            "dp_epsilon": dp_epsilon,
            "dp_delta": dp_delta,
            "dp_max_grad_norm": dp_max_grad_norm,
            "fedprox_mu": kwargs.get("fedprox_mu", 0.0),
            "moon_mu": kwargs.get("moon_mu", 0.0),
            "moon_temperature": kwargs.get("moon_temperature", 0.5),
        }

        prev_local_weights = kwargs.get("prev_local_weights")
        if prev_local_weights:
            payload["prev_local_weights"] = {
                "layer_shapes": [list(shape) for shape in prev_local_weights.layer_shapes],
                "flat_weights": prev_local_weights.flat_weights,
            }

        body_bytes, headers = self._sign_payload(payload, self._get_headers())
        with self._get_client() as client:
            resp = client.post(url, content=body_bytes, headers=headers, timeout=120.0)
            resp.raise_for_status()
            res_data = resp.json()
            res_data["correlation_id"] = correlation_id
            return res_data

    def evaluate(
        self,
        bank_id: str,
        weights: ModelWeights,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Trigger model evaluation over HTTP REST endpoint."""
        url = f"{self.base_url}/api/v1/bank-client/evaluate"
        schema_weights = {
            "layer_shapes": [list(shape) for shape in weights.layer_shapes],
            "flat_weights": weights.flat_weights,
        }
        payload = {"weights": schema_weights}
        body_bytes, headers = self._sign_payload(payload, self._get_headers())
        with self._get_client() as client:
            resp = client.post(url, content=body_bytes, headers=headers, timeout=60.0)
            resp.raise_for_status()
            res_data = resp.json()
            res_data["correlation_id"] = correlation_id
            return res_data
