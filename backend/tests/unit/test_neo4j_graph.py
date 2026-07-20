"""Unit tests for GraphEngine Neo4j integration.

Verifies that when graph_db_type is set to "neo4j", the GraphEngine routes
all calls through the mocked neo4j driver using Cypher statements.
Fallback to Redis/in-memory is also tested when the driver fails.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.application.services.graph_engine import GraphEngine
from app.domain.enums import EntityType, RelationshipType


class TestGraphEngineNeo4jConfig:
    """Verify that GraphEngine correctly reads graph_db_type from settings."""

    def test_default_is_redis(self):
        """Without env vars, graph_db_type should be 'redis' and no neo4j driver created."""
        engine = GraphEngine()
        assert engine.db_type == "redis"
        assert engine.driver is None

    @patch("app.application.services.graph_engine.get_settings")
    def test_neo4j_type_triggers_driver_creation(self, mock_get_settings):
        """When graph_db_type='neo4j', __init__ should attempt to create a driver."""
        settings = MagicMock()
        settings.graph_db_type = "neo4j"
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.neo4j_user = "neo4j"
        settings.neo4j_password = "secret"
        mock_get_settings.return_value = settings

        mock_neo4j = MagicMock()
        with patch.dict("sys.modules", {"neo4j": mock_neo4j}):
            engine = GraphEngine()

        assert engine.db_type == "neo4j"
        mock_neo4j.GraphDatabase.driver.assert_called_once_with(
            "bolt://localhost:7687", auth=("neo4j", "secret")
        )

    @patch("app.application.services.graph_engine.get_settings")
    def test_fallback_to_redis_on_connection_failure(self, mock_get_settings):
        """If driver creation raises, db_type should fall back to 'redis'."""
        settings = MagicMock()
        settings.graph_db_type = "neo4j"
        settings.neo4j_uri = "bolt://unreachable:7687"
        settings.neo4j_user = "neo4j"
        settings.neo4j_password = "bad"
        mock_get_settings.return_value = settings

        mock_neo4j = MagicMock()
        mock_neo4j.GraphDatabase.driver.side_effect = Exception("connection refused")
        with patch.dict("sys.modules", {"neo4j": mock_neo4j}):
            engine = GraphEngine()

        assert engine.db_type == "redis"
        assert engine.driver is None


class TestGraphEngineNeo4jWrites:
    """Verify that register_entity and add_relationship call Cypher when neo4j is active."""

    def _neo4j_engine(self):
        engine = GraphEngine()
        engine.db_type = "neo4j"
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        engine.driver = mock_driver
        return engine, mock_session

    def test_register_entity_runs_cypher_merge(self):
        """register_entity should run a MERGE Cypher query when Neo4j is active."""
        from app.application.services.entity_resolution import EntityResolutionService

        svc = EntityResolutionService()
        entity = svc.create_entity(EntityType.CUSTOMER, "alice", "bank_a")

        engine, mock_session = self._neo4j_engine()
        engine.register_entity(entity)

        assert mock_session.run.called
        call_args = mock_session.run.call_args
        assert "MERGE (e:Entity" in call_args[0][0]
        assert "e.entity_type" in call_args[0][0]

    def test_add_relationship_runs_cypher_merge(self):
        """add_relationship should run a MERGE Cypher query when Neo4j is active."""
        from app.application.services.entity_resolution import EntityResolutionService

        svc = EntityResolutionService()
        ea = svc.create_entity(EntityType.CUSTOMER, "alice_neo", "bank_a")
        eb = svc.create_entity(EntityType.CUSTOMER, "bob_neo", "bank_b")
        rel = svc.add_relationship(ea.id, eb.id, RelationshipType.SHARES_DEVICE)

        engine, mock_session = self._neo4j_engine()
        engine.add_relationship(rel)

        assert mock_session.run.called
        call_args = mock_session.run.call_args
        assert "MERGE" in call_args[0][0]
        assert "shares_device" in call_args[0][0]


class TestGraphEngineNeo4jStats:
    """Verify get_stats returns database_backend correctly."""

    def test_redis_backend_label(self):
        engine = GraphEngine()
        stats = engine.get_stats()
        assert stats["database_backend"] == "Redis (in-memory)"

    def test_neo4j_backend_label(self):
        engine = GraphEngine()
        engine.db_type = "neo4j"

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        engine.driver = mock_driver

        empty_result = MagicMock()
        empty_result.__iter__ = MagicMock(return_value=iter([]))

        count_rec_mock = MagicMock()
        count_rec_mock.__getitem__ = MagicMock(return_value=0)
        count_res = MagicMock()
        count_res.single = MagicMock(return_value=count_rec_mock)

        def _run(query, **kwargs):
            if "count" in query:
                return count_res
            return empty_result

        mock_session.run = MagicMock(side_effect=_run)

        stats = engine.get_stats()
        assert stats["database_backend"] == "Neo4j"


class TestGraphEngineFindNeighborsNeo4j:
    """Verify find_neighbors routes to Cypher when neo4j is active."""

    def test_find_neighbors_calls_cypher(self):
        engine = GraphEngine()
        engine.db_type = "neo4j"

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        engine.driver = mock_driver

        empty_result = MagicMock()
        empty_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.run = MagicMock(return_value=empty_result)

        neighbors = engine.find_neighbors("entity-123", depth=2)

        assert isinstance(neighbors, list)
        assert mock_session.run.called
        call_args = mock_session.run.call_args
        assert "MATCH" in call_args[0][0]
        assert "entity_id" in call_args[1]
