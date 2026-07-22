"""Unit tests for cfi-cli Bank Onboarding CLI & Self-Service Integration Sandbox (Section 6.3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helper: locate the cfi_cli script
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"
CLI_PATH = SCRIPTS_DIR / "cfi_cli.py"


def _run_cli(*argv: str) -> tuple[int, dict]:
    """Run cfi_cli.main() with the given argv and capture stdout JSON output."""
    # Dynamically import the script as a module
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("cfi_cli", CLI_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None

    captured_output: list[str] = []

    def _capturing_print(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
        captured_output.append(" ".join(str(a) for a in args))

    with (
        patch("builtins.print", side_effect=_capturing_print),
        patch.object(sys, "argv", ["cfi-cli", *argv]),
    ):
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        exit_code = mod.main()

    result: dict = {}
    for line in captured_output:
        try:
            result = json.loads(line)
            break
        except (json.JSONDecodeError, ValueError):
            pass

    return exit_code, result


# ---------------------------------------------------------------------------
# Test: cfi-cli init
# ---------------------------------------------------------------------------


def test_cli_init_creates_directory_structure(tmp_path: Path) -> None:
    """cfi-cli init must create data/vault/, certs/, logs/ and bank_config.yaml."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("cfi_cli", CLI_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    import argparse  # noqa: PLC0415

    args = argparse.Namespace(
        bank_id="test_bank",
        coordinator="coordinator.cfi.internal:50051",
        output_dir=str(tmp_path),
    )

    exit_code = mod.cmd_init(args)

    assert exit_code == 0
    assert (tmp_path / "data" / "vault").is_dir()
    assert (tmp_path / "certs").is_dir()
    assert (tmp_path / "logs").is_dir()

    config_file = tmp_path / "bank_config.yaml"
    assert config_file.is_file()
    config_text = config_file.read_text(encoding="utf-8")
    assert "test_bank" in config_text
    assert "coordinator.cfi.internal" in config_text
    assert "50051" in config_text


# ---------------------------------------------------------------------------
# Test: cfi-cli cert generate-csr
# ---------------------------------------------------------------------------


def test_cli_cert_generate_csr_creates_key_and_csr(tmp_path: Path) -> None:
    """cfi-cli cert generate-csr must write PEM-encoded RSA key and X.509 CSR."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("cfi_cli", CLI_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    import argparse  # noqa: PLC0415

    args = argparse.Namespace(
        bank_id="test_bank",
        output_dir=str(tmp_path),
        country="US",
        org="CFI Consortium",
    )

    with patch("builtins.print"):
        exit_code = mod.cmd_cert_generate_csr(args)

    assert exit_code == 0

    key_path = tmp_path / "bank.key"
    csr_path = tmp_path / "bank.csr"

    assert key_path.is_file(), "bank.key must be created"
    assert csr_path.is_file(), "bank.csr must be created"

    key_pem = key_path.read_bytes()
    csr_pem = csr_path.read_bytes()

    assert (
        b"-----BEGIN RSA PRIVATE KEY-----" in key_pem or b"-----BEGIN PRIVATE KEY-----" in key_pem
    )
    assert b"-----BEGIN CERTIFICATE REQUEST-----" in csr_pem

    # Verify CSR contains correct CN using cryptography library
    from cryptography import x509  # noqa: PLC0415

    csr = x509.load_pem_x509_csr(csr_pem)
    cn_values = [
        attr.value
        for attr in csr.subject
        if attr.oid.dotted_string == "2.5.4.3"  # OID for CN
    ]
    assert "test_bank" in cn_values


# ---------------------------------------------------------------------------
# Test: cfi-cli test-connection (failure path)
# ---------------------------------------------------------------------------


def test_cli_test_connection_reports_failure_gracefully() -> None:
    """cfi-cli test-connection must return exit code 1 and JSON error on unreachable host."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("cfi_cli", CLI_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    import argparse  # noqa: PLC0415

    # Use a port that should never be open in test environment
    args = argparse.Namespace(
        host="127.0.0.1",
        port=19999,
        timeout=0.1,
    )

    captured: list[str] = []
    with patch("builtins.print", side_effect=lambda *a, **k: captured.append(str(a[0]))):
        exit_code = mod.cmd_test_connection(args)

    assert exit_code == 1

    result = json.loads(captured[0])
    assert result["status"] == "error"
    assert result["tcp_reachable"] is False
    assert "latency_ms" in result
    assert result["latency_sla"] == "N/A"


# ---------------------------------------------------------------------------
# Test: cfi-cli sandbox run
# ---------------------------------------------------------------------------


def test_cli_sandbox_run_produces_throughput_report() -> None:
    """cfi-cli sandbox run must generate transactions and report throughput >= 1 TPS."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("cfi_cli", CLI_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    import argparse  # noqa: PLC0415

    args = argparse.Namespace(transactions=500)

    captured: list[str] = []
    with patch("builtins.print", side_effect=lambda *a, **k: captured.append(str(a[0]))):
        exit_code = mod.cmd_sandbox_run(args)

    assert exit_code == 0

    result = json.loads(captured[0])
    assert result["status"] == "ok"
    assert result["transactions_generated"] == 500
    assert result["throughput_tps"] >= 1.0, "Throughput must be at least 1 TPS"
    assert "hardware" in result
    assert "pytorch_available" in result["hardware"]
    assert "fraud_rate_pct" in result
    assert 0.0 <= result["fraud_rate_pct"] <= 100.0
