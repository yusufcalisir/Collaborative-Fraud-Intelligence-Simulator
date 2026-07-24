# ruff: noqa: E402
"""Automated Unit Test Suite for Zero-Downtime Platform Upgrade & Client Compatibility."""

from __future__ import annotations

from app.application.services.zero_downtime_deployer import (
    ZeroDowntimeDeploymentManager,
)
from app.domain.deployment_state import DeploymentStage


def test_zero_downtime_upgrade_initiation_and_connection_draining() -> None:
    """Test initiating an upgrade session and gracefully draining active client connections."""
    manager = ZeroDowntimeDeploymentManager(current_version="v2.0.0")

    session = manager.initiate_upgrade(
        target_version="v2.1.0",
        compatibility_window_hours=48,
        initial_connections=100,
    )
    assert session.target_version == "v2.1.0"
    assert session.stage == DeploymentStage.DRAINING_CONNECTIONS
    assert session.active_connections_count == 100

    # 1. First drain batch (50 connections)
    active1, drained1 = manager.drain_client_connections(session.session_id, batch_size=50)
    assert active1 == 50
    assert drained1 == 50
    assert session.stage == DeploymentStage.DRAINING_CONNECTIONS

    # 2. Second drain batch (remaining 50 connections) -> Stage transitions to ROLLING_UPGRADE
    active2, drained2 = manager.drain_client_connections(session.session_id, batch_size=50)
    assert active2 == 0
    assert drained2 == 100
    assert session.stage == DeploymentStage.ROLLING_UPGRADE


def test_rolling_instance_update_and_finalization() -> None:
    """Test rolling instance updates across cluster and finalization."""
    manager = ZeroDowntimeDeploymentManager(current_version="v2.0.0")
    session = manager.initiate_upgrade(target_version="v2.1.0", initial_connections=0)

    # Execute rolling update
    session = manager.execute_rolling_instance_update(
        session_id=session.session_id,
        instance_ids=["pod_app_1", "pod_app_2"],
    )
    assert session.stage == DeploymentStage.DUAL_VERSION_ACTIVE
    assert len(session.updated_instances) == 2

    # Finalize upgrade
    finalized = manager.finalize_upgrade(session.session_id)
    assert finalized.stage == DeploymentStage.UPGRADE_COMPLETED
    assert manager.current_version == "v2.1.0"
