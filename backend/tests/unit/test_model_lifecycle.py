# ruff: noqa: E402
"""Automated Unit Test Suite for Multi-Stage Production Model State Machine."""

from __future__ import annotations

import pytest

from app.domain.model_lifecycle import (
    InvalidStateTransitionError,
    ModelLifecycleManager,
    ModelState,
)


def test_model_lifecycle_registration_and_progressive_transitions() -> None:
    """Test valid progressive model state transitions STAGING -> SHADOW -> CANARY -> PRODUCTION -> ARCHIVED."""
    manager = ModelLifecycleManager()
    record = manager.register_model("model_v1.0.0")

    assert record.current_state == ModelState.STAGING
    assert not record.compliance_signoff
    assert len(record.state_history) == 1

    # 1. STAGING -> SHADOW
    manager.transition_state("model_v1.0.0", ModelState.SHADOW, actor_role="ML_ENGINEER")
    assert record.current_state == ModelState.SHADOW

    # 2. SHADOW -> CANARY (with sign-off approval)
    manager.transition_state(
        "model_v1.0.0",
        ModelState.CANARY,
        actor_role="COMPLIANCE_OFFICER",
        signoff_approved=True,
    )
    assert record.current_state == ModelState.CANARY
    assert record.compliance_signoff

    # 3. CANARY -> PRODUCTION
    manager.transition_state("model_v1.0.0", ModelState.PRODUCTION, actor_role="SYSTEM")
    assert record.current_state == ModelState.PRODUCTION

    # 4. PRODUCTION -> ARCHIVED
    manager.transition_state("model_v1.0.0", ModelState.ARCHIVED, actor_role="ADMIN")
    assert record.current_state == ModelState.ARCHIVED


def test_model_lifecycle_blocks_illegal_stage_jumps() -> None:
    """Test blocking illegal direct stage transitions (e.g. STAGING directly to PRODUCTION)."""
    manager = ModelLifecycleManager()
    manager.register_model("model_v2.0.0")

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        manager.transition_state("model_v2.0.0", ModelState.PRODUCTION)

    assert "Illegal state transition" in str(exc_info.value)


def test_model_lifecycle_requires_compliance_signoff() -> None:
    """Test blocking promotion to CANARY or PRODUCTION without compliance sign-off."""
    manager = ModelLifecycleManager()
    manager.register_model("model_v3.0.0")
    manager.transition_state("model_v3.0.0", ModelState.SHADOW)

    # Attempting promotion to CANARY without signoff_approved=True
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        manager.transition_state("model_v3.0.0", ModelState.CANARY, signoff_approved=False)

    assert "Compliance sign-off is required" in str(exc_info.value)
