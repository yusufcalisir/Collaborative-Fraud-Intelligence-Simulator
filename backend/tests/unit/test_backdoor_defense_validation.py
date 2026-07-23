"""Unit tests for BackdoorDefenseEvaluator & Spectral SVD Anomaly Defense Validation (Section 9.3)."""

from __future__ import annotations

import numpy as np

from app.domain.security_evaluator import BackdoorDefenseEvaluator


def _generate_synthetic_node_updates() -> dict[str, list[float]]:
    """Generates synthetic weight update vectors for 4 honest banks and 1 malicious backdoor injector bank."""
    rng = np.random.default_rng(42)
    dim = 20

    # 4 honest banks around zero mean with small variance
    updates = {
        f"bank_{node}": (rng.normal(0.0, 0.05, size=dim)).tolist() for node in ["a", "b", "d", "e"]
    }

    # 1 malicious bank (bank_c) embedding low-rank targeted backdoor trigger update
    updates["bank_c"] = (rng.normal(0.0, 0.05, size=dim) + 2.5).tolist()

    return updates


def test_targeted_backdoor_asr_on_fedavg() -> None:
    """Verifies that targeted backdoor attack achieves high Attack Success Rate (>80%) under standard FedAvg."""
    updates = _generate_synthetic_node_updates()
    evaluator = BackdoorDefenseEvaluator(seed=42)

    res = evaluator.evaluate_backdoor_defense(updates, malicious_node_id="bank_c")

    assert res.fedavg_asr >= 0.80
    assert res.fedavg_main_acc < res.spectral_svd_main_acc


def test_spectral_svd_reduces_backdoor_asr() -> None:
    """Verifies that Spectral SVD Anomaly Defense reduces backdoor ASR below 3.0% while maintaining >92% main task accuracy."""
    updates = _generate_synthetic_node_updates()
    evaluator = BackdoorDefenseEvaluator(seed=42)

    res = evaluator.evaluate_backdoor_defense(updates, malicious_node_id="bank_c")

    assert res.spectral_svd_asr < 0.03
    assert res.spectral_svd_main_acc >= 0.92
    assert res.is_defense_effective is True


def test_spectral_svd_quarantine_recall() -> None:
    """Verifies 100% quarantine recall of malicious bank node updates via spectral projection scores."""
    updates = _generate_synthetic_node_updates()
    evaluator = BackdoorDefenseEvaluator(seed=42)

    res = evaluator.evaluate_backdoor_defense(updates, malicious_node_id="bank_c")

    assert res.quarantine_recall == 1.0
    assert res.quarantine_precision == 1.0
