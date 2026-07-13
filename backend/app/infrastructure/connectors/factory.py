"""Bank Connector Factory resolving connector types dynamically."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.infrastructure.connectors.mock_connector import MockBankConnector
from app.infrastructure.connectors.mq_skeleton_connector import MQSkeletonBankConnector
from app.infrastructure.connectors.redis_connector import RedisBankConnector
from app.infrastructure.connectors.rest_connector import RESTBankConnector

if TYPE_CHECKING:
    from app.application.interfaces.bank_connector import BankConnectorInterface
    from app.config import Settings

logger = logging.getLogger(__name__)


class BankConnectorFactory:
    """Factory creating concrete BankConnector instances based on configuration settings."""

    @staticmethod
    def get_connector(
        bank_id: str,
        settings: Settings,
        model_service: Any = None,
        data_generator: Any = None,
    ) -> BankConnectorInterface:
        """Resolve and instantiate a concrete connector implementation for the specified bank."""
        # Convert bank-a to bank_a to lookup attributes
        key = bank_id.replace("-", "_")

        connector_type = getattr(settings, f"{key}_connector_type", "mock")
        auth_type = getattr(settings, f"{key}_auth_type", "none")
        api_key = getattr(settings, f"{key}_api_key", "")

        logger.info(
            "Resolving connector for %s: type=%s, auth=%s",
            bank_id,
            connector_type,
            auth_type,
        )

        if connector_type == "rest":
            base_url = settings.bank_urls.get(bank_id) or "http://localhost:8000"
            return RESTBankConnector(
                base_url=base_url,
                auth_type=auth_type,
                api_key=api_key,
                oauth_token_url=getattr(settings, "oauth_token_url", ""),
                client_cert_path=getattr(settings, "client_cert_path", ""),
                client_key_path=getattr(settings, "client_key_path", ""),
            )
        elif connector_type == "redis":
            redis_url = settings.redis_url or "redis://localhost:6379/0"
            return RedisBankConnector(redis_url=redis_url)
        elif connector_type == "mq_skeleton":
            broker_uri = getattr(settings, "mq_broker_uri", "amqp://guest:guest@localhost:5672//")
            return MQSkeletonBankConnector(broker_uri=broker_uri)
        else:
            if model_service is None or data_generator is None:
                raise ValueError("model_service and data_generator are required for mock connector.")
            return MockBankConnector(model_service=model_service, data_generator=data_generator)
