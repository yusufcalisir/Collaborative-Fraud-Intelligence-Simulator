# ruff: noqa: UP042
"""Domain models and registry for SaaS Multi-Tenancy Lifecycle Management."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TenantStatus(str, Enum):
    """Lifecycle state enum for a tenant bank node."""

    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


@dataclass
class TenantRecord:
    """Represents an onboarded financial institution in the SaaS platform."""

    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.PROVISIONING
    db_schema: str = ""
    kms_key_path: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.db_schema:
            self.db_schema = f"tenant_{self.tenant_id.lower()}"
        if not self.kms_key_path:
            self.kms_key_path = f"storage/{self.tenant_id}/kms/"


class TenantRegistry:
    """Central registry tracking active and onboarded tenant institutions."""

    def __init__(self) -> None:
        self._tenants: dict[str, TenantRecord] = {}

    def register_tenant(self, tenant_id: str, name: str) -> TenantRecord:
        """Registers a new tenant record in PROVISIONING state."""
        if tenant_id in self._tenants:
            record = self._tenants[tenant_id]
            if record.status != TenantStatus.DELETED:
                return record

        record = TenantRecord(tenant_id=tenant_id, name=name)
        self._tenants[tenant_id] = record
        logger.info("Registered tenant '%s' (%s) in PROVISIONING state", name, tenant_id)
        return record

    def set_status(self, tenant_id: str, status: TenantStatus) -> TenantRecord:
        """Updates the status of an existing tenant."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Tenant '{tenant_id}' is not registered.")

        record = self._tenants[tenant_id]
        record.status = status
        record.updated_at = datetime.now(UTC)
        logger.info("Tenant '%s' status updated to %s", tenant_id, status.value)
        return record

    def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Retrieves tenant record by ID if active or provisioning."""
        return self._tenants.get(tenant_id)

    def list_active_tenants(self) -> list[TenantRecord]:
        """Returns list of all ACTIVE tenants."""
        return [t for t in self._tenants.values() if t.status == TenantStatus.ACTIVE]

    def is_tenant_active(self, tenant_id: str) -> bool:
        """Returns True if tenant exists and is ACTIVE."""
        tenant = self.get_tenant(tenant_id)
        return tenant is not None and tenant.status == TenantStatus.ACTIVE
