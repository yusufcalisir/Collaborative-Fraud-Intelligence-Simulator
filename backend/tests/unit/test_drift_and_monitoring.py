"""Unit tests for Enterprise Observability, Model Drift Engine & Calibration Monitoring."""

from __future__ import annotations

import numpy as np

from app.application.services.drift_service import ModelDriftService


class TestModelDriftService:
    """Test suite for statistical feature drift, concept drift (PSI), and model calibration."""

    def test_feature_drift_ks_test_and_psi(self):
        svc = ModelDriftService()
        np.random.seed(42)

        ref_data = {"amount": np.random.normal(100.0, 20.0, 100).tolist()}
        curr_data = {"amount": np.random.normal(250.0, 50.0, 100).tolist()}  # Severe drift

        drifts = svc.analyze_feature_drift(curr_data, ref_data)
        assert len(drifts) == 1
        d = drifts[0]

        assert d.feature_name == "amount"
        assert d.ks_statistic > 0.5
        assert d.ks_p_value < 0.05
        assert d.psi > 0.10
        assert d.status in ("MODERATE_DRIFT", "SEVERE_DRIFT")

    def test_identical_distributions_show_stable_status(self):
        svc = ModelDriftService()
        np.random.seed(123)
        sample = np.random.normal(100.0, 15.0, 150).tolist()

        ref_data = {"amount": sample}
        curr_data = {"amount": sample}

        drifts = svc.analyze_feature_drift(curr_data, ref_data)
        assert len(drifts) == 1
        d = drifts[0]

        assert d.ks_statistic == 0.0
        assert d.ks_p_value == 1.0
        assert d.psi == 0.0
        assert d.status == "STABLE"

    def test_model_calibration_brier_score_and_ece(self):
        svc = ModelDriftService()

        # Perfect calibration (prob matches label)
        y_true = [0, 0, 0, 0, 1, 1, 1, 1]
        y_prob = [0.01, 0.02, 0.01, 0.02, 0.98, 0.99, 0.98, 0.99]

        cal = svc.compute_calibration(y_true, y_prob)
        assert cal.brier_score < 0.05
        assert cal.expected_calibration_error < 0.05
        assert cal.is_well_calibrated is True
        assert len(cal.bins) == 10

    def test_full_drift_analysis_system_status_and_trigger(self):
        svc = ModelDriftService()
        np.random.seed(42)

        ref_data = {"f1": np.random.normal(10.0, 2.0, 100).tolist()}
        curr_data = {"f1": np.random.normal(50.0, 10.0, 100).tolist()}

        ref_scores = np.random.beta(1.0, 5.0, 100).tolist()
        curr_scores = np.random.beta(5.0, 1.0, 100).tolist()

        rpt = svc.run_full_drift_analysis(
            current_data=curr_data,
            reference_data=ref_data,
            current_scores=curr_scores,
            reference_scores=ref_scores,
            y_true=[0, 1] * 50,
            y_prob=curr_scores,
        )

        assert rpt.overall_status in ("WARNING", "CRITICAL")
        assert rpt.concept_drift_psi > 0.10
        assert rpt.calibration is not None
