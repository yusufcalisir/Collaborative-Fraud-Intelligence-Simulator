# ruff: noqa: E402
"""Automated Unit Test Suite for Active-Passive Multi-Region Coordinator Failover."""

from __future__ import annotations

import datetime

from app.domain.dr_coordinator import CoordinatorRegionRole
from app.infrastructure.disaster_recovery.region_failover import (
    MultiRegionFailoverManager,
)


def test_multi_region_failover_registration_and_heartbeat() -> None:
    """Test regional coordinator node registration and heartbeat tracking."""
    manager = MultiRegionFailoverManager()

    node_primary = manager.register_node(
        node_id="coord_eu_west_1",
        region="eu-west-1",
        role=CoordinatorRegionRole.PRIMARY_ACTIVE,
    )
    node_standby = manager.register_node(
        node_id="coord_eu_central_1",
        region="eu-central-1",
        role=CoordinatorRegionRole.PASSIVE_STANDBY,
    )

    assert node_primary.role == CoordinatorRegionRole.PRIMARY_ACTIVE
    assert node_standby.role == CoordinatorRegionRole.PASSIVE_STANDBY

    # Healthy primary heartbeat -> No failover
    manager.record_heartbeat("coord_eu_west_1")
    event = manager.evaluate_health_and_failover(timeout_seconds=15.0)
    assert event is None


def test_automatic_primary_failure_detection_and_standby_promotion() -> None:
    """Test automatic primary region failure detection and passive standby promotion (RTO < 30s, RPO = 0)."""
    manager = MultiRegionFailoverManager()

    node_primary = manager.register_node(
        node_id="coord_eu_west_1",
        region="eu-west-1",
        role=CoordinatorRegionRole.PRIMARY_ACTIVE,
    )
    node_standby = manager.register_node(
        node_id="coord_eu_central_1",
        region="eu-central-1",
        role=CoordinatorRegionRole.PASSIVE_STANDBY,
    )

    # Simulate primary failure by aging last heartbeat past 15 seconds
    stale_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=20)
    node_primary.last_heartbeat = stale_time

    # Evaluate health -> Triggers failover
    event = manager.evaluate_health_and_failover(timeout_seconds=15.0)
    assert event is not None
    assert event.failed_primary_region == "eu-west-1"
    assert event.promoted_standby_region == "eu-central-1"
    assert event.rto_seconds >= 15.0
    assert event.rto_seconds < 30.0  # RTO < 30s check
    assert event.rpo_loss_records == 0  # RPO = 0 check

    assert node_primary.role == CoordinatorRegionRole.PASSIVE_STANDBY
    assert node_primary.is_healthy is False
    assert node_standby.role == CoordinatorRegionRole.FAILOVER_PROMOTED

    trail = manager.get_audit_trail()
    assert len(trail) == 1
    assert trail[0].event_id == event.event_id
