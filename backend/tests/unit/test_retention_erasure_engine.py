# ruff: noqa: E402
"""Automated Unit Test Suite for Retention & Erasure Policy Engine."""

from __future__ import annotations

from app.application.services.retention_engine import AutomatedRetentionEngine
from app.domain.retention_policy import DataCategory, ErasureMethod


def test_tenant_retention_policy_configuration() -> None:
    """Test configuring per-tenant retention TTL policies."""
    engine = AutomatedRetentionEngine()

    policy = engine.configure_tenant_policy(
        tenant_id="bank_alpha",
        category=DataCategory.TRANSACTION_LOGS,
        ttl_days=90,
        erasure_method=ErasureMethod.CRYPTOGRAPHIC_ZEROIZATION,
    )
    assert policy.category == DataCategory.TRANSACTION_LOGS
    assert policy.ttl_days == 90
    assert policy.erasure_method == ErasureMethod.CRYPTOGRAPHIC_ZEROIZATION


def test_automated_ttl_purging_execution() -> None:
    """Test executing automated TTL purging for expired tenant records."""
    engine = AutomatedRetentionEngine()
    tenant = "bank_beta"

    engine.configure_tenant_policy(tenant, DataCategory.TRANSACTION_LOGS, ttl_days=30)
    engine.configure_tenant_policy(tenant, DataCategory.GRAPH_EDGES, ttl_days=15)

    purged = engine.purge_expired_records(tenant_id=tenant)
    assert len(purged) == 2
    assert any(p.category == DataCategory.TRANSACTION_LOGS for p in purged)
    assert any(p.category == DataCategory.GRAPH_EDGES for p in purged)
    assert all(p.records_erased_count > 0 for p in purged)
    assert all(len(p.erasure_hash) == 64 for p in purged)  # SHA-256 length check


def test_gdpr_article_17_right_to_be_forgotten_erasure() -> None:
    """Test executing GDPR Article 17 Right-to-be-Forgotten erasure for an entity."""
    engine = AutomatedRetentionEngine()
    tenant = "bank_gamma"
    entity_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    record = engine.execute_gdpr_right_to_be_forgotten(
        tenant_id=tenant,
        entity_id_hash=entity_hash,
    )
    assert record.tenant_id == tenant
    assert record.erasure_id.startswith("erase_gdpr_")
    assert record.records_erased_count == 1
    assert len(record.erasure_hash) == 64

    trail = engine.get_erasure_audit_trail(tenant)
    assert len(trail) == 1
    assert trail[0].erasure_id == record.erasure_id
