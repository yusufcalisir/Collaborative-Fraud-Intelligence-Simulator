# ruff: noqa: E402
"""Unit test suite for Consortium Quorum & Policy Enforcement Engine."""

from __future__ import annotations

import pytest

from app.application.services.consortium_service import ConsortiumGovernanceService
from app.domain.consortium_policy import (
    ConsortiumPolicyConfig,
    ConsortiumPolicyEngine,
    ConsortiumPolicyViolation,
)


def test_consortium_policy_validation_success() -> None:
    """Test policy validation passing for compliant FL round parameters."""
    service = ConsortiumGovernanceService()
    consortium = service.create_consortium(
        consortium_id="eu_aml_policy",
        name="EU Policy Test",
        founder_bank_id="bank_a",
        max_epsilon=4.0,
    )
    # Add bank_b to meet 2-member min active count
    service.propose_membership_change("eu_aml_policy", "bank_a", "bank_b")

    engine = ConsortiumPolicyEngine(config=ConsortiumPolicyConfig(min_active_members=2))

    is_valid, reasons = engine.validate_fl_round_preconditions(
        consortium=consortium,
        participating_banks=["bank_a", "bank_b"],
        round_epsilon=2.0,
        architecture="PyTorch_MLP",
    )

    assert is_valid is True
    assert len(reasons) == 0


def test_consortium_policy_blocks_insufficient_quorum() -> None:
    """Test blocking FL round when participating bank count is below min_active_members."""
    service = ConsortiumGovernanceService()
    consortium = service.create_consortium(
        consortium_id="solo_policy",
        name="Solo Test",
        founder_bank_id="bank_a",
    )

    engine = ConsortiumPolicyEngine(config=ConsortiumPolicyConfig(min_active_members=2))

    with pytest.raises(ConsortiumPolicyViolation) as exc_info:
        engine.enforce_fl_round_preconditions(
            consortium=consortium,
            participating_banks=["bank_a"],  # Only 1 bank
            round_epsilon=1.0,
        )

    assert "Insufficient participating members" in str(exc_info.value)


def test_consortium_policy_blocks_exceeded_epsilon() -> None:
    """Test blocking FL round when proposed DP noise budget exceeds max_epsilon."""
    service = ConsortiumGovernanceService()
    consortium = service.create_consortium(
        consortium_id="dp_cap_test",
        name="DP Cap Test",
        founder_bank_id="bank_a",
        max_epsilon=3.0,
    )
    service.propose_membership_change("dp_cap_test", "bank_a", "bank_b")

    engine = ConsortiumPolicyEngine()

    with pytest.raises(ConsortiumPolicyViolation) as exc_info:
        engine.enforce_fl_round_preconditions(
            consortium=consortium,
            participating_banks=["bank_a", "bank_b"],
            round_epsilon=8.0,  # Exceeds max 3.0
        )

    assert "Proposed DP epsilon (8.00) exceeds max allowed limit" in str(exc_info.value)


def test_consortium_policy_blocks_unapproved_bank() -> None:
    """Test blocking FL round when an unapproved/evicted bank attempts to participate."""
    service = ConsortiumGovernanceService()
    consortium = service.create_consortium(
        consortium_id="auth_test",
        name="Auth Test",
        founder_bank_id="bank_a",
    )
    service.propose_membership_change("auth_test", "bank_a", "bank_b")

    engine = ConsortiumPolicyEngine(config=ConsortiumPolicyConfig(min_active_members=2))

    with pytest.raises(ConsortiumPolicyViolation) as exc_info:
        engine.enforce_fl_round_preconditions(
            consortium=consortium,
            participating_banks=["bank_a", "unauthorized_bank_x"],
            round_epsilon=1.0,
        )

    assert "is not an active member" in str(exc_info.value)
