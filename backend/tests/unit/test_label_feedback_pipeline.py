# ruff: noqa: E402
"""Automated Unit Test Suite for Local Label Feedback & Privacy-Preserving Gradient Update."""

from __future__ import annotations

import pytest

from app.application.services.label_feedback_pipeline import (
    FeedbackLabel,
    LocalLabelFeedbackPipeline,
)
from app.domain.label_privacy_guard import LabelPrivacyViolationError


def test_local_label_feedback_ingestion_and_buffer_management() -> None:
    """Test analyst determination label ingestion and tenant buffer tracking."""
    pipeline = LocalLabelFeedbackPipeline()

    # 1. Ingest valid hashed transaction feedback
    tx_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4"  # 40-char HMAC hash
    item = pipeline.ingest_analyst_determination(
        tenant_id="bank_alpha",
        transaction_id_hash=tx_hash,
        determination="CONFIRMED_FRAUD",
    )
    assert item.transaction_id_hash == tx_hash
    assert item.label == FeedbackLabel.CONFIRMED_FRAUD
    assert pipeline.get_buffer_size("bank_alpha") == 1


def test_label_privacy_guard_rejects_unmasked_pii() -> None:
    """Test zero-PII enforcement blocking raw IBAN or SSN feedback inputs."""
    pipeline = LocalLabelFeedbackPipeline()

    # 1. Short non-hash transaction ID -> Fails
    with pytest.raises(LabelPrivacyViolationError) as exc_info1:
        pipeline.ingest_analyst_determination(
            tenant_id="bank_beta",
            transaction_id_hash="tx_short",
            determination="FALSE_POSITIVE",
        )
    assert "must be an HMAC-SHA256 hash" in str(exc_info1.value)

    # 2. Raw IBAN (>= 32 chars) -> Fails pattern check
    with pytest.raises(LabelPrivacyViolationError) as exc_info2:
        pipeline.ingest_analyst_determination(
            tenant_id="bank_beta",
            transaction_id_hash="TR12345678901234567890123456789012",
            determination="FALSE_POSITIVE",
        )
    assert "matches raw PII format" in str(exc_info2.value)

    # 3. Raw PII attribute key -> Fails
    with pytest.raises(LabelPrivacyViolationError) as exc_info3:
        pipeline.ingest_analyst_determination(
            tenant_id="bank_beta",
            transaction_id_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4",
            determination="FALSE_POSITIVE",
            raw_attributes={"iban": "TR990001"},
        )
    assert "Forbidden raw PII key" in str(exc_info3.value)


def test_dp_gradient_update_computation_with_noise_injection() -> None:
    """Test Gaussian DP noise injection on local gradient updates."""
    pipeline = LocalLabelFeedbackPipeline()
    tenant = "bank_gamma"

    # Ingest 3 confirmed fraud items
    for i in range(3):
        pipeline.ingest_analyst_determination(
            tenant_id=tenant,
            transaction_id_hash=f"hash_sample_{i:02d}_1234567890abcdef1234567890",
            determination="CONFIRMED_FRAUD",
        )

    # Compute DP gradient update
    res = pipeline.compute_dp_gradient_update(tenant_id=tenant, epsilon=1.0)
    assert res["tenant_id"] == tenant
    assert res["sample_count"] == 3
    assert res["epsilon"] == 1.0
    assert len(res["delta_weights"]) == 4

    # Invalid epsilon > max_epsilon (2.0) -> Fails
    with pytest.raises(LabelPrivacyViolationError):
        pipeline.compute_dp_gradient_update(tenant_id=tenant, epsilon=5.0)
