"""Zero-Downtime Rolling Deployment Manager."""

from __future__ import annotations

import logging
import uuid

from app.domain.deployment_state import (
    DeploymentSession,
    DeploymentStage,
    UpgradeWindow,
)

logger = logging.getLogger(__name__)


class ZeroDowntimeDeploymentManager:
    """Orchestrates zero-downtime rolling upgrades, connection draining, and dual-version windows."""

    def __init__(self, current_version: str = "v2.0.0") -> None:
        self.current_version = current_version
        self._sessions: dict[str, DeploymentSession] = {}
        self._upgrade_window: UpgradeWindow | None = None

    def initiate_upgrade(
        self,
        target_version: str,
        compatibility_window_hours: int = 48,
        initial_connections: int = 100,
    ) -> DeploymentSession:
        """Initiates a zero-downtime rolling upgrade session."""
        session_id = f"deploy_{uuid.uuid4().hex[:8]}"

        session = DeploymentSession(
            session_id=session_id,
            target_version=target_version,
            stage=DeploymentStage.DRAINING_CONNECTIONS,
            active_connections_count=initial_connections,
            drained_connections_count=0,
        )
        self._sessions[session_id] = session

        self._upgrade_window = UpgradeWindow(
            current_version=self.current_version,
            target_version=target_version,
            compatibility_window_hours=compatibility_window_hours,
        )

        logger.info(
            "Initiated zero-downtime upgrade session %s (%s -> %s, Window: %dh)",
            session_id,
            self.current_version,
            target_version,
            compatibility_window_hours,
        )
        return session

    def drain_client_connections(
        self,
        session_id: str,
        batch_size: int = 50,
    ) -> tuple[int, int]:
        """Gracefully drains active client connections without dropping requests."""
        if session_id not in self._sessions:
            raise KeyError(f"Deployment session '{session_id}' does not exist.")

        session = self._sessions[session_id]
        drained_amount = min(batch_size, session.active_connections_count)

        session.active_connections_count -= drained_amount
        session.drained_connections_count += drained_amount

        if session.active_connections_count == 0:
            session.stage = DeploymentStage.ROLLING_UPGRADE

        logger.info(
            "Drained %d connections for session %s (Remaining active: %d, Drained total: %d)",
            drained_amount,
            session_id,
            session.active_connections_count,
            session.drained_connections_count,
        )
        return session.active_connections_count, session.drained_connections_count

    def execute_rolling_instance_update(
        self,
        session_id: str,
        instance_ids: list[str],
    ) -> DeploymentSession:
        """Performs rolling instance updates across the cluster."""
        if session_id not in self._sessions:
            raise KeyError(f"Deployment session '{session_id}' does not exist.")

        session = self._sessions[session_id]
        session.updated_instances.extend(instance_ids)
        session.stage = DeploymentStage.DUAL_VERSION_ACTIVE

        logger.info(
            "Updated %d cluster instances for session %s to %s. Stage: DUAL_VERSION_ACTIVE",
            len(instance_ids),
            session_id,
            session.target_version,
        )
        return session

    def finalize_upgrade(self, session_id: str) -> DeploymentSession:
        """Finalizes upgrade session and sets stage to UPGRADE_COMPLETED."""
        if session_id not in self._sessions:
            raise KeyError(f"Deployment session '{session_id}' does not exist.")

        session = self._sessions[session_id]
        session.stage = DeploymentStage.UPGRADE_COMPLETED
        self.current_version = session.target_version

        logger.info(
            "Finalized deployment session %s. Platform current version updated to %s.",
            session_id,
            self.current_version,
        )
        return session

    def get_session(self, session_id: str) -> DeploymentSession | None:
        """Retrieves deployment session by ID."""
        return self._sessions.get(session_id)
