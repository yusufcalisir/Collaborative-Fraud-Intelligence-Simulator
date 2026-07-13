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

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_type == "apikey" and self.api_key:
            headers["X-API-KEY"] = self.api_key
        elif self.auth_type == "oauth2":
            token = self._get_oauth2_token()
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _get_oauth2_token(self) -> str:
        if self._token:
            return self._token
        logger.info("Requesting OAuth2 client credentials token from %s", self.oauth_token_url)
        # Authentication token endpoint fetch placeholder
        self._token = "mock_oauth2_access_token_placeholder"
        return self._token

    def _get_client(self) -> httpx.Client:
        # Mutual TLS support hook
        if self.auth_type == "mtls" and self.client_cert_path and self.client_key_path:
            logger.info("Configuring Mutual TLS with cert: %s", self.client_cert_path)
            return httpx.Client(cert=(self.client_cert_path, self.client_key_path))
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
        headers = self._get_headers()
        with self._get_client() as client:
            resp = client.post(url, json=payload, headers=headers, timeout=30.0)
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
        }
        headers = self._get_headers()
        with self._get_client() as client:
            resp = client.post(url, json=payload, headers=headers, timeout=120.0)
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
        headers = self._get_headers()
        with self._get_client() as client:
            resp = client.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            res_data = resp.json()
            res_data["correlation_id"] = correlation_id
            return res_data
