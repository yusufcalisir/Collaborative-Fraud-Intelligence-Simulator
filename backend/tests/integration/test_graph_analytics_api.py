"""Integration tests for graph analytics and PSI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.application.services.entity_resolution import EntityResolutionService
from app.domain.enums import EntityType, RelationshipType, RiskLevel
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_graph_stores() -> None:
    # Clear out RedisStore / memory caches before test run
    entity_service = EntityResolutionService()
    entity_service._entities.clear()
    entity_service._relationships.clear()
    entity_service._hash_index.clear()


def test_psi_endpoint_returns_matches() -> None:
    entity_service = EntityResolutionService()
    # Create matching entities
    entity_service.create_entity(
        entity_type=EntityType.CUSTOMER,
        raw_identifier="shared_user_123",
        bank_id="bank_a",
    )
    entity_service.create_entity(
        entity_type=EntityType.CUSTOMER,
        raw_identifier="shared_user_123",
        bank_id="bank_b",
    )

    response = client.post(
        "/api/v1/entities/psi",
        json={
            "bank_a_id": "bank_a",
            "bank_b_id": "bank_b",
            "entity_type": "customer",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert "stats" in data
    assert len(data["matches"]) == 1
    assert data["matches"][0]["privacy_hash"] is not None
    assert data["stats"]["num_entities_a"] == 1
    assert data["stats"]["num_entities_b"] == 1


def test_graph_analytics_endpoints() -> None:
    entity_service = EntityResolutionService()

    # Create entities and relationships
    a = entity_service.create_entity(EntityType.CUSTOMER, "alice", "bank_a")
    b = entity_service.create_entity(EntityType.CUSTOMER, "bob", "bank_a")
    c = entity_service.create_entity(EntityType.CUSTOMER, "charlie", "bank_a")

    entity_service.update_risk_level(a.id, RiskLevel.CRITICAL)

    entity_service.add_relationship(a.id, b.id, RelationshipType.OWNS)
    entity_service.add_relationship(b.id, c.id, RelationshipType.OWNS)

    # 1. Test Risk Propagation
    prop_response = client.post(
        "/api/v1/graph/propagate-risk",
        json={"decay_factor": 0.8},
    )
    assert prop_response.status_code == 200
    prop_data = prop_response.json()
    assert "updated_nodes_count" in prop_data
    assert prop_data["updated_nodes_count"] >= 1

    # 2. Test Communities Analytics
    comm_response = client.get("/api/v1/graph/communities/analytics?min_size=2")
    assert comm_response.status_code == 200
    comm_data = comm_response.json()
    assert len(comm_data) >= 1
    assert comm_data[0]["size"] == 3
    assert comm_data[0]["fraud_density"] > 0.0

    # 3. Test Temporal Anomalies
    temp_response = client.get("/api/v1/graph/temporal-anomalies?window_minutes=10&min_edges=2")
    assert temp_response.status_code == 200
    temp_data = temp_response.json()
    assert len(temp_data) >= 1
    assert temp_data[0]["edges_count"] == 2
    assert temp_data[0]["velocity_score"] > 0.0
