# ruff: noqa: E402, TC003
"""Automated Unit Test Suite for cfi-cli Utility & Packaging."""

from __future__ import annotations

from pathlib import Path

from app.presentation.cli.cfi_cli import (
    command_deploy,
    command_export_diagnostics,
    command_health,
    command_status,
    main,
)


def test_cli_subcommands_execution(tmp_path: Path) -> None:
    """Test direct execution of cfi-cli subcommands."""
    # 1. status
    status = command_status()
    assert status["status"] == "HEALTHY"
    assert len(status["active_bank_nodes"]) == 3

    # 2. health
    health = command_health()
    assert health["status"] == "UP"
    assert health["components"]["inference_engine"] == "HEALTHY"

    # 3. export-diagnostics
    out_file = tmp_path / "test_diag.json"
    exported = command_export_diagnostics(output_path=str(out_file))
    assert exported.exists()
    assert "cli_version" in exported.read_text(encoding="utf-8")

    # 4. deploy
    deploy = command_deploy(target_version="v2.1.0")
    assert deploy["target_version"] == "v2.1.0"
    assert deploy["stage"] == "DRAINING_CONNECTIONS"


def test_main_cli_entrypoint(tmp_path: Path) -> None:
    """Test main entrypoint argument parsing."""
    out_file = tmp_path / "cli_diag.json"

    ret_status = main(["status"])
    assert ret_status == 0

    ret_health = main(["health"])
    assert ret_health == 0

    ret_export = main(["export-diagnostics", "--output", str(out_file)])
    assert ret_export == 0
    assert out_file.exists()

    ret_deploy = main(["deploy", "--target-version", "v2.2.0"])
    assert ret_deploy == 0
