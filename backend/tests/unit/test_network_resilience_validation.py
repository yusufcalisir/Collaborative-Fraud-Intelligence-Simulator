"""Unit tests for NetworkResilienceEvaluator & Dynamic Quorum Fault Tolerance Validation (Section 9.5)."""

from __future__ import annotations

from app.domain.security_evaluator import NetworkResilienceEvaluator


def test_straggler_latency_triggers_quorum_auto_aggregation() -> None:
    """Verifies that 60% node submissions auto-trigger aggregation in <12.5s without waiting for stragglers."""
    evaluator = NetworkResilienceEvaluator(seed=42)
    res = evaluator.evaluate_network_resilience(total_nodes=5, quorum_threshold_pct=0.60)

    assert res.scenario_a_quorum_reached is True
    assert res.scenario_a_duration_sec < 12.5
    assert res.zero_deadlock_verified is True


def test_abrupt_disconnect_graceful_recovery() -> None:
    """Verifies that abrupt node disconnect (40% dropout) gracefully completes round aggregation."""
    evaluator = NetworkResilienceEvaluator(seed=42)
    res = evaluator.evaluate_network_resilience(total_nodes=5, quorum_threshold_pct=0.60)

    assert res.scenario_b_quorum_reached is True
    assert res.scenario_b_duration_sec < 15.0
    assert res.scenario_c_quorum_reached is True


def test_staleness_attenuation_preserves_model_convergence() -> None:
    """Verifies that FedAsync staleness attenuation downweights delayed updates, preserving F1 > 0.93."""
    evaluator = NetworkResilienceEvaluator(seed=42)
    res = evaluator.evaluate_network_resilience(total_nodes=5, quorum_threshold_pct=0.60)

    assert res.staleness_attenuation_f1 >= 0.93
    assert res.zero_deadlock_verified is True
