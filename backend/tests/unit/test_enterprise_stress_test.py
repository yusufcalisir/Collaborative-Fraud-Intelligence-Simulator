"""Unit tests for EnterpriseStressTestRunner and PaymentTransactionGenerator (Section 14.1).

Covers:
- ISO 20022 pacs.008 payload schema validation
- Transaction amount and cross-border field correctness
- StressTestRunner prepare() validation
- Benchmark run() completion with non-zero throughput
- StressTestResult JSON serialization
- Markdown report generation
"""

from __future__ import annotations

import os
import sys

import pytest

# Add scripts directory to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))

from run_enterprise_stress_test import (  # type: ignore[import]
    EnterpriseStressTestRunner,
    PaymentTransactionGenerator,
    StressTestConfig,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def generator() -> PaymentTransactionGenerator:
    return PaymentTransactionGenerator(num_banks=3)


@pytest.fixture()
def quick_config() -> StressTestConfig:
    return StressTestConfig(
        num_banks=3,
        transactions_per_second_target=500,
        duration_seconds=2,
        batch_size=20,
        output_dir="reports/test",
    )


@pytest.fixture()
def runner(quick_config: StressTestConfig) -> EnterpriseStressTestRunner:
    return EnterpriseStressTestRunner(quick_config)


# ---------------------------------------------------------------------------
# 1. TestPaymentTransactionGenerator
# ---------------------------------------------------------------------------

class TestPaymentTransactionGenerator:
    def test_transaction_has_required_iso20022_keys(self, generator: PaymentTransactionGenerator):
        """Generated payload contains required ISO 20022 pacs.008 top-level keys."""
        tx = generator.generate_transaction()
        assert "GrpHdr" in tx
        assert "CdtTrfTxInf" in tx
        assert "_cfi_meta" in tx

    def test_grphdr_has_required_fields(self, generator: PaymentTransactionGenerator):
        """GrpHdr section contains MsgId, CreDtTm, NbOfTxs, SttlmInf."""
        grp_hdr = generator.generate_transaction()["GrpHdr"]
        assert "MsgId" in grp_hdr
        assert "CreDtTm" in grp_hdr
        assert "NbOfTxs" in grp_hdr
        assert "SttlmInf" in grp_hdr

    def test_transaction_amount_within_valid_range(self, generator: PaymentTransactionGenerator):
        """Generated transaction amount is within $10.00–$2,000,000.00 range."""
        for _ in range(20):
            tx = generator.generate_transaction()
            amount = tx["_cfi_meta"]["amount"]
            assert 10.0 <= amount <= 2_000_000.0, f"Amount out of range: {amount}"

    def test_cfi_meta_contains_tx_id_and_risk_score(self, generator: PaymentTransactionGenerator):
        """_cfi_meta contains tx_id (UUID) and risk_score in [0, 1]."""
        meta = generator.generate_transaction()["_cfi_meta"]
        assert "tx_id" in meta
        assert "risk_score" in meta
        assert 0.0 <= meta["risk_score"] <= 1.0

    def test_unique_tx_ids_across_transactions(self, generator: PaymentTransactionGenerator):
        """Each generated transaction has a unique tx_id."""
        tx_ids = {generator.generate_transaction()["_cfi_meta"]["tx_id"] for _ in range(50)}
        assert len(tx_ids) == 50

    def test_generate_batch_returns_correct_size(self, generator: PaymentTransactionGenerator):
        """generate_batch returns exactly batch_size transactions."""
        batch = generator.generate_batch(batch_size=25)
        assert len(batch) == 25

    def test_source_bank_is_respected_as_sender(self, generator: PaymentTransactionGenerator):
        """generate_transaction sets source_bank_id in _cfi_meta when specified."""
        for _ in range(10):
            tx = generator.generate_transaction(source_bank="bank_a")
            assert tx["_cfi_meta"]["source_bank_id"] == "bank_a"


# ---------------------------------------------------------------------------
# 2. TestStressTestRunner
# ---------------------------------------------------------------------------

class TestStressTestRunner:
    def test_prepare_does_not_raise(self, runner: EnterpriseStressTestRunner):
        """prepare() validates generator and succeeds without exceptions."""
        runner.prepare()  # Should not raise

    def test_run_completes_within_time_tolerance(self, runner: EnterpriseStressTestRunner):
        """run() completes within duration_seconds + 5s tolerance."""
        import time
        start = time.monotonic()
        _ = runner.run()
        elapsed = time.monotonic() - start
        assert elapsed <= runner.config.duration_seconds + 5.0, (
            f"Test took {elapsed:.1f}s which exceeds {runner.config.duration_seconds + 5}s tolerance"
        )

    def test_run_processes_nonzero_transactions(self, runner: EnterpriseStressTestRunner):
        """run() processes at least 1 transaction per bank node."""
        result = runner.run()
        assert result.total_transactions > 0
        assert result.total_transactions >= runner.config.num_banks

    def test_run_result_has_all_required_fields(self, runner: EnterpriseStressTestRunner):
        """StressTestResult has all mandatory measurement fields set."""
        result = runner.run()
        assert result.peak_tps >= 0.0
        assert result.p50_latency_ms >= 0.0
        assert result.p99_latency_ms >= 0.0
        assert result.mean_latency_ms >= 0.0
        assert result.error_rate_pct >= 0.0
        assert result.duration_actual_seconds > 0.0

    def test_run_result_per_bank_throughput_has_all_banks(
        self, runner: EnterpriseStressTestRunner
    ):
        """per_bank_throughput contains an entry for each bank node."""
        result = runner.run()
        for bank_id in runner._bank_ids:
            assert bank_id in result.per_bank_throughput, f"Missing bank: {bank_id}"


# ---------------------------------------------------------------------------
# 3. TestStressTestResultSerialization
# ---------------------------------------------------------------------------

class TestStressTestResultSerialization:
    def test_to_dict_contains_required_keys(self, runner: EnterpriseStressTestRunner):
        """to_dict() returns JSON-serializable dict with all expected keys."""
        result = runner.run()
        data = result.to_dict()

        assert "total_transactions" in data
        assert "peak_tps" in data
        assert "p50_latency_ms" in data
        assert "p99_latency_ms" in data
        assert "error_rate_pct" in data
        assert "duration_actual_seconds" in data
        assert "per_bank_throughput" in data
        assert "config" in data

    def test_markdown_report_contains_key_sections(self, runner: EnterpriseStressTestRunner):
        """report() generates Markdown containing all required section headers."""
        result = runner.run()
        md = runner.report(result)

        assert "# Enterprise Payment Stream Benchmark Report" in md
        assert "## Test Configuration" in md
        assert "## Throughput Results" in md
        assert "## Latency Distribution" in md
        assert "## Per-Bank Throughput" in md
        assert "## Conformance Verdict" in md
