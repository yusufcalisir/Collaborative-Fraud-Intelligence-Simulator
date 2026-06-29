"""Test configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_config() -> dict:
    """Default simulation config for tests."""
    return {
        "num_rounds": 3,
        "local_epochs": 2,
        "learning_rate": 0.001,
        "batch_size": 32,
        "min_clients_per_round": 2,
        "enable_latency_simulation": False,
        "latency_range_ms": (50, 500),
        "enable_dropout_simulation": False,
        "dropout_probability": 0.2,
        "enable_reconnect_simulation": True,
        "enable_differential_privacy": False,
        "dp_epsilon": 1.0,
        "dp_delta": 1e-5,
        "dp_max_grad_norm": 1.0,
        "enable_secure_aggregation": False,
        "bank_a_transactions": 1000,
        "bank_b_transactions": 800,
        "bank_c_transactions": 600,
    }
