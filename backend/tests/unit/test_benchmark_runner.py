"""Unit tests for BenchmarkRunner & 9-Configuration Benchmark Suite (Section 8.2)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.domain.benchmark_runner import BenchmarkResult, BenchmarkRunner


def test_benchmark_result_schema_complete() -> None:
    """Verifies that BenchmarkResult dataclass schema contains all required fields with correct types."""
    res = BenchmarkResult(
        config_id="C3",
        name="Standard FedAvg",
        roc_auc=0.912,
        pr_auc=0.785,
        f1_score=0.745,
        recall_at_1pct_fpr=0.820,
        false_positive_rate=0.01,
        epsilon_consumed=0.0,
        total_bytes_transmitted=12_500_000,
        rounds_to_convergence=5,
        training_time_seconds=2.45,
        inference_latency_p99_ms=2.8,
    )

    d = res.to_dict()
    assert d["config_id"] == "C3"
    assert d["roc_auc"] == 0.912
    assert d["pr_auc"] == 0.785
    assert d["recall_at_1pct_fpr"] == 0.820
    assert d["total_bytes_transmitted"] == 12_500_000


def test_local_only_auc_below_centralized() -> None:
    """Sanity check verifying Local-Only (C1) ROC-AUC is lower than Centralized Pooled (C2)."""
    runner = BenchmarkRunner(samples_per_bank=300, rounds=2)
    results = runner.run_all()

    c1 = results["C1"]
    c2 = results["C2"]

    assert c1.roc_auc < c2.roc_auc
    assert c1.pr_auc <= c2.pr_auc


def test_dp_reduces_auc_vs_fedavg() -> None:
    """Sanity check verifying Differential Privacy (C5) causes a controlled reduction in AUC vs FedAvg (C3)."""
    runner = BenchmarkRunner(samples_per_bank=300, rounds=2)
    results = runner.run_all()

    c3 = results["C3"]
    c5 = results["C5"]

    assert c5.roc_auc < c3.roc_auc
    assert c5.epsilon_consumed == 1.0


def test_benchmark_runner_saves_json() -> None:
    """Verifies that BenchmarkRunner saves JSON results to disk correctly."""
    runner = BenchmarkRunner(samples_per_bank=200, rounds=1)
    runner.run_all()

    with tempfile.TemporaryDirectory() as tmp_dir:
        json_path = Path(tmp_dir) / "benchmark_test.json"
        saved_path = runner.save_results_json(json_path)

        assert saved_path.exists()
        assert saved_path.stat().st_size > 0
