# ruff: noqa: E402
"""Automated Unit Test Suite for Per-Tenant KMS Encryption, Quotas & Metering."""

from __future__ import annotations

import pytest
from cryptography.fernet import InvalidToken

from app.application.services.tenant_metering import (
    TenantMeteringService,
    TenantQuotaLimits,
)
from app.infrastructure.security.tenant_kms import TenantKMSManager


def test_tenant_kms_key_isolation_and_encryption() -> None:
    """Test per-tenant envelope encryption and cryptographic key isolation."""
    kms = TenantKMSManager(master_secret="unit_test_master_secret_2026")
    plaintext = "Sensitive Account Data 998822"

    # Encrypt data under bank_a context
    ciphertext_a = kms.encrypt_tenant_data("bank_a", plaintext)
    assert ciphertext_a != plaintext

    # Decrypt under correct bank_a context
    decrypted_a = kms.decrypt_tenant_data("bank_a", ciphertext_a)
    assert decrypted_a == plaintext

    # Verify key isolation: Bank B cannot decrypt Bank A's ciphertext
    with pytest.raises(InvalidToken):
        kms.decrypt_tenant_data("bank_b", ciphertext_a)


def test_tenant_kms_key_rotation() -> None:
    """Test tenant key rotation mechanics."""
    kms = TenantKMSManager()
    rotation_info = kms.rotate_tenant_key("bank_a")

    assert rotation_info["status"] == "ROTATED"
    assert rotation_info["tenant_id"] == "bank_a"
    assert "key_version" in rotation_info


def test_tenant_metering_and_quota_enforcement() -> None:
    """Test usage metering tracking and quota boundary enforcement."""
    metering = TenantMeteringService()

    # Configure custom low quota for bank_c
    limits = TenantQuotaLimits(max_daily_inferences=5, max_monthly_fl_rounds=2, max_storage_mb=10.0)
    metering.set_quota_limits("bank_c", limits)

    # 1. Record inferences within quota
    for _ in range(5):
        allowed, reason = metering.check_quota("bank_c", "INFERENCE")
        assert allowed is True
        assert reason == "OK"
        metering.record_inference("bank_c", 1)

    # 2. Exceed inference quota
    allowed_over, reason_over = metering.check_quota("bank_c", "INFERENCE")
    assert allowed_over is False
    assert "Daily inference quota exceeded" in reason_over

    # 3. Check billing summary calculation
    metering.record_fl_round("bank_c")
    summary = metering.get_billing_summary("bank_c")

    assert summary["tenant_id"] == "bank_c"
    assert summary["daily_inferences"] == 5
    assert summary["monthly_fl_rounds"] == 1
    assert summary["estimated_cost_usd"] > 0
