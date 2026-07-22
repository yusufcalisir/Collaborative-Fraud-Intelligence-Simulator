"""Unit tests for Regional Governance Rings & EU AI Act Compliance Engine (Section 6.1)."""

from __future__ import annotations

import os

import numpy as np
import pytest

from app.domain.regional_governance import (
    CrossBorderSovereigntyFilter,
    CrossBorderSovereigntyViolationError,
    Region,
    RegionalGovernanceRingManager,
)
from app.infrastructure.security.ai_act_compliance import EUAIActComplianceEngine


def test_regional_ring_node_registration_and_intra_aggregation() -> None:
    """Verifies bank node registration and intra-region FedAvg weight aggregation."""
    manager = RegionalGovernanceRingManager()

    manager.register_node("bank_a", "Bank A (EU)", Region.EU_CENTRAL)
    manager.register_node("bank_b", "Bank B (EU)", Region.EU_CENTRAL)
    manager.register_node("bank_c", "Bank C (US)", Region.US_EAST)

    # Weights for EU nodes
    weights_a = {"layer1": np.array([1.0, 2.0, 3.0])}
    weights_b = {"layer1": np.array([3.0, 4.0, 5.0])}
    client_weights = {"bank_a": weights_a, "bank_b": weights_b}
    sample_counts = {"bank_a": 100, "bank_b": 100}

    eu_aggregated = manager.aggregate_intra_region(Region.EU_CENTRAL, client_weights, sample_counts)

    assert "layer1" in eu_aggregated
    # Average of [1,2,3] and [3,4,5] is [2,3,4]
    np.testing.assert_array_almost_equal(eu_aggregated["layer1"], np.array([2.0, 3.0, 4.0]))


def test_inter_region_dp_meta_aggregation() -> None:
    """Verifies inter-region DP-scrubbed meta-aggregation across regional rings."""
    manager = RegionalGovernanceRingManager()

    manager.register_node("bank_eu", "Bank EU", Region.EU_CENTRAL)
    manager.register_node("bank_us", "Bank US", Region.US_EAST)

    manager.regional_weights[Region.EU_CENTRAL] = {"fc": np.array([10.0, 20.0])}
    manager.regional_weights[Region.US_EAST] = {"fc": np.array([30.0, 40.0])}

    meta_weights = manager.aggregate_inter_region_meta(inter_region_dp_epsilon=1.0)

    assert "fc" in meta_weights
    assert meta_weights["fc"].shape == (2,)


def test_cross_border_sovereignty_filter_blocks_raw_transfer() -> None:
    """Verifies CrossBorderSovereigntyFilter blocks raw parameter transfer across regional boundaries."""
    # Transfer within same region is allowed
    assert CrossBorderSovereigntyFilter.validate_transfer(
        Region.EU_CENTRAL, Region.EU_CENTRAL, is_dp_scrubbed=False, is_raw_parameter=True
    )

    # Cross-border transfer of raw parameters without DP scrubbing is strictly blocked
    with pytest.raises(CrossBorderSovereigntyViolationError):
        CrossBorderSovereigntyFilter.validate_transfer(
            Region.EU_CENTRAL, Region.US_EAST, is_dp_scrubbed=False, is_raw_parameter=True
        )


def test_eu_ai_act_compliance_certificate_generation(tmp_path: pytest.TempPathFactory) -> None:
    """Verifies automated EU AI Act High-Risk AI System compliance certificate generation."""
    output_dir = str(tmp_path)
    engine = EUAIActComplianceEngine(output_dir=output_dir)

    human_signoffs = [
        {"role": "ml_engineer", "user_id": "eng_lead_01", "status": "APPROVED"},
        {"role": "compliance_officer", "user_id": "comp_off_02", "status": "APPROVED"},
    ]
    explainability = {"top_feature": "merchant_velocity_1h", "shap_auc": 0.94}
    robustness = {"clean_accuracy": 0.98, "pgd_evasion_rejection": 0.94}

    cert = engine.generate_certificate(
        model_version="v2.5.0",
        git_commit_sha="2d1733f",
        training_dataset_hash="sha256_dataset_mock",
        human_oversight_signoffs=human_signoffs,
        explainability_metrics=explainability,
        robustness_scores=robustness,
        dp_epsilon=2.5,
    )

    assert cert.model_version == "v2.5.0"
    assert cert.data_governance_art10["status"] == "COMPLIANT"
    assert cert.human_oversight_art14["four_eyes_principle_enforced"] is True
    assert len(cert.cryptographic_digest_sha256) == 64

    # Verify file saved
    expected_path = os.path.join(output_dir, f"{cert.certificate_id}.json")
    assert os.path.exists(expected_path)
