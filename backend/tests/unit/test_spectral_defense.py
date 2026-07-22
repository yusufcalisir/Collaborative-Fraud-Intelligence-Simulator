"""Unit tests for Spectral Anomaly Detection & Backdoor Poisoning Defense (Section 6.5)."""

from __future__ import annotations

from app.domain.spectral_defense import (
    SpectralAnomalyDetector,
    SpectralDefenseConfig,
)

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def _make_honest_update(value: float, n_params: int = 10) -> dict[str, float]:
    """Generate a normal-magnitude honest client parameter update."""
    return {f"param_{i}": value + (i * 0.01) for i in range(n_params)}


def _make_poisoned_update(scale: float = 100.0, n_params: int = 10) -> dict[str, float]:
    """Generate a backdoor-poisoned update with anomalously large magnitude in a specific subspace."""
    update: dict[str, float] = {}
    for i in range(n_params):
        # Backdoor attack: inject a dominant low-rank perturbation along param_0 axis
        if i == 0:
            update[f"param_{i}"] = scale
        else:
            update[f"param_{i}"] = 0.01
    return update


# ---------------------------------------------------------------------------
# Test: compute_spectral_scores
# ---------------------------------------------------------------------------


def test_spectral_score_computation() -> None:
    """Verifies SVD projection scores are computed and all non-negative."""
    config = SpectralDefenseConfig(min_clients=2)
    detector = SpectralAnomalyDetector(config=config)

    client_updates = {
        "bank_a": _make_honest_update(0.1),
        "bank_b": _make_honest_update(0.12),
        "bank_c": _make_honest_update(0.09),
    }

    scores = detector.compute_spectral_scores(client_updates)

    assert set(scores.keys()) == {"bank_a", "bank_b", "bank_c"}
    for bank_id, score in scores.items():
        assert score >= 0.0, f"Spectral score must be non-negative for {bank_id}"


# ---------------------------------------------------------------------------
# Test: detect_backdoor_poisoning_attack
# ---------------------------------------------------------------------------


def test_detect_backdoor_poisoning_attack() -> None:
    """Verifies that a stealthy low-rank backdoor injection is detected and quarantined."""
    config = SpectralDefenseConfig(
        spectral_threshold_multiplier=0.5,  # Tighter threshold to ensure detection
        min_clients=3,
    )
    detector = SpectralAnomalyDetector(config=config)

    client_updates = {
        "bank_honest_a": _make_honest_update(0.1),
        "bank_honest_b": _make_honest_update(0.12),
        "bank_honest_c": _make_honest_update(0.09),
        "bank_poisoned": _make_poisoned_update(scale=500.0),  # Extreme backdoor
    }

    reports = detector.detect_backdoor_anomalies(client_updates)

    assert len(reports) == 4

    report_map = {r.node_id: r for r in reports}

    # Poisoned node must be detected
    assert report_map["bank_poisoned"].is_poisoned is True, (
        f"Backdoor node not detected. Score={report_map['bank_poisoned'].spectral_score}"
    )

    # Honest nodes must pass
    for honest_id in ["bank_honest_a", "bank_honest_b", "bank_honest_c"]:
        assert report_map[honest_id].is_poisoned is False, (
            f"Honest node {honest_id} incorrectly quarantined"
        )


# ---------------------------------------------------------------------------
# Test: aggregate_robust_spectral
# ---------------------------------------------------------------------------


def test_robust_spectral_aggregation() -> None:
    """Verifies poisoned updates are excluded from robustly aggregated global weights."""
    config = SpectralDefenseConfig(
        spectral_threshold_multiplier=0.5,
        min_clients=3,
    )
    detector = SpectralAnomalyDetector(config=config)

    poisoned_value = 999.0
    honest_value = 0.1

    client_updates = {
        "bank_a": _make_honest_update(honest_value),
        "bank_b": _make_honest_update(honest_value + 0.01),
        "bank_c": _make_honest_update(honest_value - 0.01),
        "bank_evil": _make_poisoned_update(scale=poisoned_value),
    }

    aggregated = detector.aggregate_robust_spectral(client_updates)

    assert len(aggregated) > 0, "Aggregated result must not be empty"

    # Aggregated param_0 should be close to honest range (~0.1), far from poisoned (999.0)
    param_0 = aggregated.get("param_0", 0.0)
    assert param_0 < 50.0, (
        f"Aggregated param_0={param_0} too large; poisoned update likely leaked into aggregation"
    )


# ---------------------------------------------------------------------------
# Test: insufficient clients fallback
# ---------------------------------------------------------------------------


def test_spectral_defense_insufficient_clients_fallback() -> None:
    """Verifies graceful fallback behavior when fewer than min_clients submit updates."""
    config = SpectralDefenseConfig(min_clients=5)
    detector = SpectralAnomalyDetector(config=config)

    client_updates = {
        "bank_a": _make_honest_update(0.1),
        "bank_b": _make_honest_update(0.12),
    }

    reports = detector.detect_backdoor_anomalies(client_updates)

    assert len(reports) == 2
    for report in reports:
        assert report.is_poisoned is False
        assert report.reason == "insufficient_clients_fallback"
        assert report.spectral_score == 0.0
