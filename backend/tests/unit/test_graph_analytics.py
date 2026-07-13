"""Unit tests for Graph Analytics service."""

from __future__ import annotations

import pytest

from app.application.services.entity_resolution import EntityResolutionService
from app.application.services.graph_analytics_service import GraphAnalyticsService
from app.application.services.graph_engine import GraphEngine
from app.domain.enums import EntityType, RelationshipType, RiskLevel


@pytest.fixture
def entity_service() -> EntityResolutionService:
    return EntityResolutionService()


@pytest.fixture
def graph_engine() -> GraphEngine:
    return GraphEngine()


@pytest.fixture
def analytics_service(
    graph_engine: GraphEngine, entity_service: EntityResolutionService
) -> GraphAnalyticsService:
    return GraphAnalyticsService(graph_engine, entity_service)


class TestGraphAnalytics:
    def test_propagate_risk_decays_scores(
        self,
        entity_service: EntityResolutionService,
        analytics_service: GraphAnalyticsService,
    ) -> None:
        # Create a chain of entities: A (Critical) - B (Minimal) - C (Minimal)
        a = entity_service.create_entity(EntityType.CUSTOMER, "user_a", "bank_a")
        b = entity_service.create_entity(EntityType.CUSTOMER, "user_b", "bank_a")
        c = entity_service.create_entity(EntityType.CUSTOMER, "user_c", "bank_a")

        entity_service.update_risk_level(a.id, RiskLevel.CRITICAL)

        # Connect A - B (OWNS) and B - C (OWNS)
        entity_service.add_relationship(a.id, b.id, RelationshipType.OWNS, confidence=1.0)
        entity_service.add_relationship(b.id, c.id, RelationshipType.OWNS, confidence=1.0)

        # Propagate risk
        res = analytics_service.propagate_risk(decay_factor=0.85)

        # Retrieve updated entities
        a_updated = entity_service.get_entity(a.id)
        b_updated = entity_service.get_entity(b.id)
        c_updated = entity_service.get_entity(c.id)

        assert a_updated.risk_level == RiskLevel.CRITICAL
        # Propagated score to B: 1000 * 0.85 * 1.0 * 1.0 = 850 (CRITICAL)
        assert b_updated.risk_level == RiskLevel.CRITICAL
        # Propagated score to C from B (850): 850 * 0.85 * 1.0 * 1.0 = 722.5 (HIGH)
        assert c_updated.risk_level == RiskLevel.HIGH

        assert res["updated_nodes_count"] == 2
        assert res["max_score"] == 1000.0

    def test_community_analytics(
        self,
        entity_service: EntityResolutionService,
        analytics_service: GraphAnalyticsService,
    ) -> None:
        # Create simple cluster of size 3
        a = entity_service.create_entity(EntityType.CUSTOMER, "c_a", "bank_a")
        b = entity_service.create_entity(EntityType.CUSTOMER, "c_b", "bank_a")
        c = entity_service.create_entity(EntityType.CUSTOMER, "c_c", "bank_a")

        entity_service.update_risk_level(a.id, RiskLevel.HIGH)

        entity_service.add_relationship(a.id, b.id, RelationshipType.SHARES_DEVICE)
        entity_service.add_relationship(b.id, c.id, RelationshipType.SHARES_DEVICE)

        communities = analytics_service.get_community_analytics(min_size=2)
        assert len(communities) >= 1

        comm = communities[0]
        assert comm["size"] == 3
        # 1 out of 3 is High risk
        assert comm["fraud_density"] == round(1 / 3, 4)
        assert comm["average_risk"] > 50.0  # (800 + 50 + 50) / 3 = 300

    def test_temporal_anomalies(
        self,
        entity_service: EntityResolutionService,
        analytics_service: GraphAnalyticsService,
    ) -> None:
        # Create nodes and relationships created at same time
        a = entity_service.create_entity(EntityType.CUSTOMER, "t_a", "bank_a")
        b = entity_service.create_entity(EntityType.CUSTOMER, "t_b", "bank_a")
        c = entity_service.create_entity(EntityType.CUSTOMER, "t_c", "bank_a")

        entity_service.add_relationship(a.id, b.id, RelationshipType.TRANSACTS_WITH)
        entity_service.add_relationship(b.id, c.id, RelationshipType.TRANSACTS_WITH)
        entity_service.add_relationship(c.id, a.id, RelationshipType.TRANSACTS_WITH)

        anomalies = analytics_service.get_temporal_anomalies(window_minutes=5, min_edges=3)
        assert len(anomalies) >= 1
        assert anomalies[0]["edges_count"] == 3
        assert anomalies[0]["velocity_score"] > 0.0
