"""Unit tests for Asynchronous FL Engine & Dynamic Quorum Timeout Manager (Section 6.2)."""

from __future__ import annotations

import datetime

import numpy as np

from app.domain.async_fl_engine import AsyncFLEngine, staleness_attenuation
from app.domain.quorum_manager import DynamicQuorumManager, QuorumState


def test_staleness_attenuation_calculation() -> None:
    """Verifies staleness attenuation factor S(tau) = (1 + tau)^(-alpha)."""
    assert staleness_attenuation(tau=0, alpha=0.5) == 1.0
    assert round(staleness_attenuation(tau=1, alpha=0.5), 4) == 0.7071
    assert round(staleness_attenuation(tau=3, alpha=0.5), 4) == 0.5000


def test_async_fl_engine_parameter_update() -> None:
    """Verifies AsyncFLEngine accumulates asynchronous updates with staleness weighting."""
    engine = AsyncFLEngine(current_round=5, alpha_staleness=0.5, learning_rate=1.0)

    global_w = {"fc": np.array([10.0, 20.0])}
    engine.set_global_weights(global_w)

    client_w = {"fc": np.array([20.0, 40.0])}
    # Update from round 1 -> tau = 4 -> s(tau) = (1+4)^(-0.5) = 1 / sqrt(5) ~= 0.4472
    new_w = engine.apply_async_update(
        node_id="bank_slow",
        submitted_round=1,
        client_weights=client_w,
        sample_count=100,
    )

    assert "fc" in new_w
    # Verify global weights moved toward client weights proportionally to attenuated alpha
    assert new_w["fc"][0] > 10.0
    assert new_w["fc"][0] < 20.0


def test_dynamic_quorum_manager_threshold_triggering() -> None:
    """Verifies DynamicQuorumManager triggers QUORUM_REACHED state when >= 60% nodes submit."""
    manager = DynamicQuorumManager(quorum_threshold_pct=0.60, target_window_seconds=300)

    nodes = ["bank_a", "bank_b", "bank_c", "bank_d", "bank_e"]  # 5 nodes
    manager.register_nodes(nodes)

    # 1 node = 20% -> WAITING
    state1 = manager.record_node_submission("bank_a")
    assert state1 == QuorumState.WAITING

    # 2 nodes = 40% -> WAITING
    state2 = manager.record_node_submission("bank_b")
    assert state2 == QuorumState.WAITING

    # 3 nodes = 60% -> QUORUM_REACHED
    state3 = manager.record_node_submission("bank_c")
    assert state3 == QuorumState.QUORUM_REACHED


def test_dynamic_quorum_manager_timeout_expiration() -> None:
    """Verifies DynamicQuorumManager transitions to TIMEOUT_EXPIRED when target window elapses."""
    manager = DynamicQuorumManager(quorum_threshold_pct=0.60, target_window_seconds=10)

    nodes = ["bank_a", "bank_b", "bank_c", "bank_d", "bank_e"]
    manager.register_nodes(nodes)

    # Force start time to 20 seconds in the past to simulate timeout
    manager.round_start_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=20)

    status = manager.evaluate_quorum_status()
    assert status.state == QuorumState.TIMEOUT_EXPIRED
    assert status.time_remaining_seconds == 0.0
