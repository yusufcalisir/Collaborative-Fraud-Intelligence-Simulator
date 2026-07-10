import numpy as np
import pytest

from app.presentation.routers.banks import (
    _compute_categorical_js,
    _compute_categorical_psi,
    _compute_js_divergence,
    _compute_psi,
    get_bank_distributions,
)


def test_js_divergence_identical_distributions():
    # Identical distributions should have JS divergence of 0.0
    p = np.array([10, 20, 30, 40], dtype=float)
    q = np.array([10, 20, 30, 40], dtype=float)

    js = _compute_js_divergence(p, q)
    assert pytest.approx(js, abs=1e-5) == 0.0


def test_js_divergence_disjoint_distributions():
    # Orthogonal/completely disjoint distributions should have high JS divergence
    p = np.array([1, 0, 0], dtype=float)
    q = np.array([0, 0, 1], dtype=float)

    js = _compute_js_divergence(p, q)
    # JS divergence using log2 is 1.0 for orthogonal distributions
    assert js > 0.9


def test_psi_identical():
    # Identical distributions should have PSI of 0.0
    expected = np.random.normal(0, 1, 100)
    actual = expected.copy()

    psi = _compute_psi(expected, actual)
    assert pytest.approx(psi, abs=1e-5) == 0.0


def test_psi_shifted():
    # Shifted distributions should have a positive PSI score
    np.random.seed(42)
    expected = np.random.normal(0, 1, 1000)
    actual = np.random.normal(1.5, 1, 1000)  # Significantly shifted

    psi = _compute_psi(expected, actual)
    assert psi > 0.25  # Large shift indicator threshold


def test_categorical_metrics():
    expected = np.array(["apple", "apple", "banana", "orange"])
    actual = np.array(["banana", "orange", "orange", "orange"])

    js = _compute_categorical_js(expected, actual)
    psi = _compute_categorical_psi(expected, actual)

    assert js > 0.0
    assert psi > 0.0


@pytest.mark.asyncio
async def test_api_distributions_endpoint_returns_drift_schema():
    # Call the endpoint handler directly (it is an async function)
    result = await get_bank_distributions()

    # Verify core keys exist
    assert "banks" in result
    assert "divergence_summary" in result

    div_summary = result["divergence_summary"]
    assert "amount_ks_statistic" in div_summary
    assert "overall_non_iid_score" in div_summary
    assert "feature_drift" in div_summary
    assert "concept_drift" in div_summary

    # Check feature drift keys structure
    fd = div_summary["feature_drift"]
    assert "a_vs_b" in fd
    assert "a_vs_c" in fd
    assert "b_vs_c" in fd

    # Check continuous feature drift values
    ab_drift = fd["a_vs_b"]
    assert "overall_psi" in ab_drift
    assert "overall_js" in ab_drift
    assert "features" in ab_drift
    assert "transaction_amount" in ab_drift["features"]
    assert "velocity" in ab_drift["features"]
    assert "device_type" in ab_drift["features"]

    # Check concept drift keys structure
    cd = div_summary["concept_drift"]
    assert "a_vs_b" in cd
    assert "model_prediction_drift" in cd["a_vs_b"]
    assert "conditional_drifts" in cd["a_vs_b"]
    assert "hour_of_day" in cd["a_vs_b"]["conditional_drifts"]
    assert "merchant_category" in cd["a_vs_b"]["conditional_drifts"]
