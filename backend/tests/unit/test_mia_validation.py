"""Unit tests for MIAEvaluator & Empirical Membership Inference Attack Validation (Section 9.1)."""

from __future__ import annotations

import numpy as np

from app.domain.security_evaluator import MIAEvaluator


def test_mia_attack_accuracy_on_unprotected_model() -> None:
    """Verifies that shadow model MIA attack achieves non-trivial accuracy (>60%) on unprotected outputs."""
    rng = np.random.default_rng(42)
    n_samples = 500

    y_true = rng.integers(0, 2, size=n_samples)
    member_mask = np.array([1] * (n_samples // 2) + [0] * (n_samples // 2), dtype=bool)

    # Synthetic prediction probabilities where member samples have lower loss (overfitting simulation)
    y_pred_prob = np.zeros(n_samples)
    for i in range(n_samples):
        if member_mask[i]:
            # Member: high confidence prediction (low loss)
            y_pred_prob[i] = 0.95 if y_true[i] == 1 else 0.05
        else:
            # Non-member: lower confidence prediction (higher loss)
            y_pred_prob[i] = 0.60 if y_true[i] == 1 else 0.40

    evaluator = MIAEvaluator(seed=42)
    res = evaluator.evaluate_membership_inference(y_true, y_pred_prob, member_mask, epsilon=1.0)

    assert res.unprotected_attack_acc >= 0.60
    assert res.unprotected_advantage >= 0.20
    assert res.sample_count == n_samples


def test_dp_protection_reduces_mia_accuracy() -> None:
    """Verifies that Differential Privacy (eps=1.0) reduces MIA attack accuracy near 50% random guessing."""
    rng = np.random.default_rng(42)
    n_samples = 500

    y_true = rng.integers(0, 2, size=n_samples)
    member_mask = np.array([1] * (n_samples // 2) + [0] * (n_samples // 2), dtype=bool)
    y_pred_prob = rng.uniform(0.1, 0.9, size=n_samples)

    evaluator = MIAEvaluator(seed=42)
    res = evaluator.evaluate_membership_inference(y_true, y_pred_prob, member_mask, epsilon=1.0)

    assert 0.50 <= res.dp_protected_attack_acc <= 0.53
    assert res.dp_protected_attack_acc < res.unprotected_attack_acc


def test_mia_advantage_bound() -> None:
    """Verifies empirical MIA Advantage < 0.05 under DP epsilon=1.0 protection."""
    rng = np.random.default_rng(42)
    n_samples = 400

    y_true = rng.integers(0, 2, size=n_samples)
    member_mask = rng.choice([True, False], size=n_samples)
    y_pred_prob = rng.uniform(0.1, 0.9, size=n_samples)

    evaluator = MIAEvaluator(seed=42)
    res = evaluator.evaluate_membership_inference(y_true, y_pred_prob, member_mask, epsilon=1.0)

    assert res.dp_protected_advantage < 0.05
    assert res.is_statistically_private is True
