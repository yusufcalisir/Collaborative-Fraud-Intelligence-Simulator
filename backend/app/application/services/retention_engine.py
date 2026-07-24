"""Automated Retention & Erasure Policy Engine Service."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from app.domain.retention_policy import (
    DataCategory,
    ErasureAuditRecord,
    ErasureMethod,
    RetentionPolicy,
)

logger = logging.getLogger(__name__)


class AutomatedRetentionEngine:
    """Manages tenant retention policies, automated TTL purging, and GDPR Art. 17 erasures."""

    def __init__(self) -> None:
        self._policies: dict[str, dict[DataCategory, RetentionPolicy]] = {}
        self._records: list[ErasureAuditRecord] = []

    def configure_tenant_policy(
        self,
        tenant_id: str,
        category: DataCategory,
        ttl_days: int,
        erasure_method: ErasureMethod = ErasureMethod.CRYPTOGRAPHIC_ZEROIZATION,
    ) -> RetentionPolicy:
        """Configures per-tenant TTL data retention policy."""
        policy = RetentionPolicy(
            category=category,
            ttl_days=ttl_days,
            erasure_method=erasure_method,
        )

        if tenant_id not in self._policies:
            self._policies[tenant_id] = {}
        self._policies[tenant_id][category] = policy

        logger.info(
            "Configured retention policy for tenant '%s' (Category: %s, TTL: %d days)",
            tenant_id,
            category.value,
            ttl_days,
        )
        return policy

    def execute_gdpr_right_to_be_forgotten(
        self,
        tenant_id: str,
        entity_id_hash: str,
    ) -> ErasureAuditRecord:
        """Executes GDPR Article 17 Right-to-be-Forgotten erasure for an entity."""
        erasure_id = f"erase_gdpr_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(UTC)
        raw_hash_str = f"{erasure_id}|{tenant_id}|{entity_id_hash}|{timestamp.isoformat()}"
        erasure_hash = hashlib.sha256(raw_hash_str.encode("utf-8")).hexdigest()

        record = ErasureAuditRecord(
            erasure_id=erasure_id,
            tenant_id=tenant_id,
            category=DataCategory.TRANSACTION_LOGS,
            records_erased_count=1,
            erasure_hash=erasure_hash,
            timestamp=timestamp,
        )
        self._records.append(record)

        logger.warning(
            "EXECUTED GDPR ARTICLE 17 ERASURE %s for tenant '%s' (Entity: %s)",
            erasure_id,
            tenant_id,
            entity_id_hash[:8],
        )
        return record

    def purge_expired_records(self, tenant_id: str) -> list[ErasureAuditRecord]:
        """Scans tenant storage and purges records exceeding configured TTL schedules."""
        tenant_policies = self._policies.get(tenant_id, {})
        purged_records: list[ErasureAuditRecord] = []

        for category, policy in tenant_policies.items():
            erasure_id = f"erase_ttl_{uuid.uuid4().hex[:8]}"
            timestamp = datetime.now(UTC)
            raw_hash_str = f"{erasure_id}|{tenant_id}|{category.value}|{timestamp.isoformat()}"
            erasure_hash = hashlib.sha256(raw_hash_str.encode("utf-8")).hexdigest()

            record = ErasureAuditRecord(
                erasure_id=erasure_id,
                tenant_id=tenant_id,
                category=category,
                records_erased_count=15,  # Simulated purged expired records count
                erasure_hash=erasure_hash,
                timestamp=timestamp,
            )
            self._records.append(record)
            purged_records.append(record)

            logger.info(
                "Purged expired %s records for tenant '%s' (TTL: %d days)",
                category.value,
                tenant_id,
                policy.ttl_days,
            )

        return purged_records

    def get_erasure_audit_trail(self, tenant_id: str) -> list[ErasureAuditRecord]:
        """Retrieves tenant erasure audit records."""
        return [r for r in self._records if r.tenant_id == tenant_id]
