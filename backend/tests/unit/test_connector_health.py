# ruff: noqa: E402
"""Unit test suite for Bank Connector Health Check Protocol and Reference Connector Script."""

from __future__ import annotations

import os
import sys

# Add sdk/python to path for testing importability
sdk_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "sdk", "python")
)
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from cfi_connector_sdk import ConnectorHealthMonitor, ConnectorHealthStatus


def test_connector_health_monitor_ping_and_report() -> None:
    """Test health monitor broker ping probing and health report generation."""
    # Test unreachable port probe
    monitor = ConnectorHealthMonitor(broker_host="localhost", broker_port=59999)

    report = monitor.get_health_report()

    assert isinstance(report, ConnectorHealthStatus)
    assert report.broker_connected is False
    assert report.status == "UNHEALTHY"
    assert "broker_target" in report.details


def test_connector_cert_validity_check(tmp_path) -> None:
    """Test certificate validity checking with missing vs mock cert."""
    monitor = ConnectorHealthMonitor(cert_path=str(tmp_path / "non_existent.crt"))

    # Missing cert returns fallback days
    days = monitor.check_cert_validity()
    assert days == 30
