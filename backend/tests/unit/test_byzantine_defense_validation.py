"""Unit tests for ByzantineDefenseEvaluator & 6-Aggregator Fault Tolerance Validation (Section 9.4)."""

from __future__ import annotations

from app.domain.security_evaluator import ByzantineDefenseEvaluator


def test_byzantine_attack_collapses_fedavg() -> None:
    """Verifies that standard FedAvg F1 score collapses below 0.20 under a single Sign-Flip Byzantine attack node."""
    evaluator = ByzantineDefenseEvaluator(seed=42)
    res = evaluator.evaluate_byzantine_resilience(attack_type="sign_flip", f_byzantine=1)

    assert res.fedavg_f1 < 0.20
    assert res.fedprox_f1 < 0.20
    assert res.clean_f1 == 0.945


def test_trimmed_mean_resists_byzantine_attack() -> None:
    """Verifies that Trimmed Mean maintains F1 > 0.90 under a single Byzantine attack node."""
    evaluator = ByzantineDefenseEvaluator(seed=42)
    res = evaluator.evaluate_byzantine_resilience(attack_type="sign_flip", f_byzantine=1)

    assert res.trimmed_mean_f1 >= 0.90
    assert res.median_f1 >= 0.90
    assert res.krum_f1 >= 0.90
    assert res.is_robust_aggregation_verified is True


def test_bulyan_resists_colluding_byzantine_nodes() -> None:
    """Verifies that Bulyan maintains F1 > 0.90 even under f=2 colluding Byzantine attack nodes."""
    evaluator = ByzantineDefenseEvaluator(seed=42)
    res = evaluator.evaluate_byzantine_resilience(attack_type="sign_flip", f_byzantine=2)

    assert res.bulyan_f1 >= 0.90
    assert res.trimmed_mean_f1 >= 0.90
    assert res.bulyan_f1 > res.fedavg_f1
