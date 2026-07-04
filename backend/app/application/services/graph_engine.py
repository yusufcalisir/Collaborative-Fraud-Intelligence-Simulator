"""Graph engine.

Builds and queries the entity relationship graph. The graph represents
connections between entities (customers, merchants, devices, etc.)
across institutions. Graph operations include neighbor expansion,
connected component detection, and serialization to React Flow format
for interactive visualization.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from app.domain.entities_phase2 import Entity, Relationship
from app.domain.enums import EntityType, RelationshipType, RiskLevel
from app.domain.value_objects_phase2 import GraphSubgraph
from app.infrastructure.redis_store import RedisStore

logger = logging.getLogger(__name__)


def _entity_to_dict(e: Entity) -> dict[str, Any]:
    return {
        "id": e.id,
        "entity_type": e.entity_type.value,
        "privacy_id": e.privacy_id,
        "bank_id": e.bank_id,
        "display_label": e.display_label,
        "attributes": e.attributes,
        "risk_level": e.risk_level.value,
        "alert_count": e.alert_count,
        "first_seen": e.first_seen.isoformat(),
        "last_seen": e.last_seen.isoformat(),
    }


def _dict_to_entity(d: dict[str, Any]) -> Entity:
    from datetime import datetime

    d_copy = d.copy()
    d_copy["entity_type"] = EntityType(d_copy["entity_type"])
    d_copy["risk_level"] = RiskLevel(d_copy["risk_level"])
    d_copy["first_seen"] = datetime.fromisoformat(d_copy["first_seen"])
    d_copy["last_seen"] = datetime.fromisoformat(d_copy["last_seen"])
    return Entity(**d_copy)


def _relationship_to_dict(r: Relationship) -> dict[str, Any]:
    return {
        "id": r.id,
        "source_entity_id": r.source_entity_id,
        "target_entity_id": r.target_entity_id,
        "relationship_type": r.relationship_type.value,
        "confidence": r.confidence,
        "evidence": r.evidence,
        "created_at": r.created_at.isoformat(),
    }


def _dict_to_relationship(d: dict[str, Any]) -> Relationship:
    from datetime import datetime

    d_copy = d.copy()
    d_copy["relationship_type"] = RelationshipType(d_copy["relationship_type"])
    d_copy["created_at"] = datetime.fromisoformat(d_copy["created_at"])
    return Relationship(**d_copy)


# Color mapping for React Flow node types
_NODE_COLORS: dict[str, str] = {
    EntityType.CUSTOMER: "#6366f1",
    EntityType.MERCHANT: "#f59e0b",
    EntityType.DEVICE: "#14b8a6",
    EntityType.CARD: "#ec4899",
    EntityType.EMAIL: "#8b5cf6",
    EntityType.PHONE: "#06b6d4",
    EntityType.IP_ADDRESS: "#f43f5e",
}

_EDGE_STYLES: dict[str, dict] = {
    RelationshipType.OWNS: {"stroke": "#6366f1", "strokeWidth": 2},
    RelationshipType.USES: {"stroke": "#14b8a6", "strokeWidth": 1.5},
    RelationshipType.TRANSACTS_WITH: {"stroke": "#f59e0b", "strokeWidth": 2},
    RelationshipType.SHARES_DEVICE: {"stroke": "#ec4899", "strokeDasharray": "5,5"},
    RelationshipType.SHARES_IP: {"stroke": "#f43f5e", "strokeDasharray": "5,5"},
    RelationshipType.LINKED_ALERT: {"stroke": "#ef4444", "strokeWidth": 2.5},
    RelationshipType.SAME_ENTITY: {"stroke": "#a855f7", "strokeWidth": 3},
}


class GraphEngine:
    """Builds and queries the entity relationship graph.

    The graph is an in-memory adjacency structure. In production,
    this would be backed by a graph database (Neo4j, Neptune, etc.).
    For the simulator, in-memory is sufficient and keeps dependencies
    minimal.
    """

    def __init__(self) -> None:
        self._entities = RedisStore("entity")
        self._relationships = RedisStore("relationship")
        self._adjacency: defaultdict[str, set[tuple[str, str]]] = defaultdict(set)

    def _build_adjacency_list(self) -> None:
        self._adjacency = defaultdict(set)
        raw_relationships = self._relationships.list_values()
        for r_dict in raw_relationships:
            r = _dict_to_relationship(r_dict)
            self._adjacency[r.source_entity_id].add((r.target_entity_id, r.id))
            self._adjacency[r.target_entity_id].add((r.source_entity_id, r.id))

    def register_entity(self, entity: Entity) -> None:
        """Register an entity in the graph."""
        self._entities.set(entity.id, _entity_to_dict(entity))

    def register_entities(self, entities: list[Entity]) -> None:
        for entity in entities:
            self.register_entity(entity)

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship (edge) to the graph."""
        self._relationships.set(relationship.id, _relationship_to_dict(relationship))

    def find_neighbors(
        self,
        entity_id: str,
        depth: int = 1,
        relationship_types: set[RelationshipType] | None = None,
    ) -> list[Entity]:
        """BFS traversal to find neighbors up to a given depth.

        Args:
            entity_id: Starting node.
            depth: Maximum traversal depth (1 = direct neighbors).
            relationship_types: Optional filter on edge types.

        Returns:
            List of neighboring entities (excluding the start node).
        """
        self._build_adjacency_list()
        visited: set[str] = {entity_id}
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])
        neighbors: list[Entity] = []

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            for neighbor_id, rel_id in self._adjacency.get(current_id, set()):
                if neighbor_id in visited:
                    continue

                # Filter by relationship type if specified
                if relationship_types:
                    rel_val = self._relationships.get(rel_id)
                    rel = _dict_to_relationship(rel_val) if rel_val else None
                    if rel and rel.relationship_type not in relationship_types:
                        continue

                visited.add(neighbor_id)
                entity_val = self._entities.get(neighbor_id)
                if entity_val:
                    entity = _dict_to_entity(entity_val)
                    neighbors.append(entity)
                    queue.append((neighbor_id, current_depth + 1))

        return neighbors

    def detect_clusters(self, min_size: int = 3) -> list[list[str]]:
        """Find connected components (clusters) of at least min_size.

        Clusters of connected entities often indicate fraud rings
        or organized criminal activity.
        """
        self._build_adjacency_list()
        visited: set[str] = set()
        clusters: list[list[str]] = []

        raw_entities = [_dict_to_entity(v) for v in self._entities.list_values()]
        for entity in raw_entities:
            entity_id = entity.id
            if entity_id in visited:
                continue

            # BFS to find the connected component
            component: list[str] = []
            queue: deque[str] = deque([entity_id])

            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)

                for neighbor_id, _ in self._adjacency.get(current, set()):
                    if neighbor_id not in visited:
                        queue.append(neighbor_id)

            if len(component) >= min_size:
                clusters.append(component)

        # Sort clusters by size, largest first
        clusters.sort(key=len, reverse=True)
        logger.info("Found %d clusters (min_size=%d)", len(clusters), min_size)
        return clusters

    def get_subgraph(
        self,
        center_entity_id: str,
        radius: int = 2,
    ) -> GraphSubgraph:
        """Extract a subgraph centered on an entity.

        Returns the subgraph in React Flow format for visualization.
        """
        self._build_adjacency_list()
        center_entity_val = self._entities.get(center_entity_id)
        if not center_entity_val:
            return GraphSubgraph(center_entity_id=center_entity_id, depth=radius)

        # Collect nodes via BFS
        visited: set[str] = {center_entity_id}
        queue: deque[tuple[str, int]] = deque([(center_entity_id, 0)])
        node_ids: list[str] = [center_entity_id]

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= radius:
                continue
            for neighbor_id, _ in self._adjacency.get(current_id, set()):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    node_ids.append(neighbor_id)
                    queue.append((neighbor_id, current_depth + 1))

        # Build React Flow nodes
        nodes = []
        for i, nid in enumerate(node_ids):
            entity_val = self._entities.get(nid)
            if not entity_val:
                continue
            entity = _dict_to_entity(entity_val)

            # Radial layout
            import math

            if nid == center_entity_id:
                x: float = 400.0
                y: float = 300.0
            else:
                angle = 2 * math.pi * (i - 1) / max(1, len(node_ids) - 1)
                layer = 1
                for depth_check in range(radius):
                    # Rough depth estimation
                    if i > len(node_ids) * (depth_check + 1) / (radius + 1):
                        layer = depth_check + 2
                r = 150 * layer
                x = 400 + r * math.cos(angle)
                y = 300 + r * math.sin(angle)

            color = _NODE_COLORS.get(entity.entity_type, "#6366f1")
            is_high_risk = entity.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

            nodes.append(
                {
                    "id": nid,
                    "type": "default",
                    "position": {"x": round(x), "y": round(y)},
                    "data": {
                        "label": entity.display_label,
                        "entityType": entity.entity_type.value,
                        "bankId": entity.bank_id,
                        "riskLevel": entity.risk_level.value,
                        "alertCount": entity.alert_count,
                        "isCenter": nid == center_entity_id,
                    },
                    "style": {
                        "background": color if not is_high_risk else "#ef4444",
                        "color": "#ffffff",
                        "border": f"2px solid {'#ef4444' if is_high_risk else color}",
                        "borderRadius": "8px",
                        "padding": "8px 12px",
                        "fontSize": "11px",
                        "fontWeight": "600",
                    },
                }
            )

        # Build React Flow edges
        edges = []
        node_id_set = set(node_ids)
        raw_relationships = [_dict_to_relationship(v) for v in self._relationships.list_values()]
        for rel in raw_relationships:
            if rel.source_entity_id in node_id_set and rel.target_entity_id in node_id_set:
                style = _EDGE_STYLES.get(rel.relationship_type, {})
                edges.append(
                    {
                        "id": rel.id,
                        "source": rel.source_entity_id,
                        "target": rel.target_entity_id,
                        "label": rel.relationship_type.value.replace("_", " "),
                        "type": "smoothstep",
                        "animated": rel.relationship_type == RelationshipType.LINKED_ALERT,
                        "style": style,
                        "data": {
                            "confidence": rel.confidence,
                            "relationshipType": rel.relationship_type.value,
                        },
                    }
                )

        # Detect clusters within subgraph
        clusters = self._detect_subgraph_clusters(node_id_set)

        return GraphSubgraph(
            nodes=nodes,
            edges=edges,
            clusters=clusters,
            center_entity_id=center_entity_id,
            depth=radius,
        )

    def search_nodes(
        self,
        query: str,
        entity_type: EntityType | None = None,
        limit: int = 20,
    ) -> list[Entity]:
        """Search entities by display label or privacy ID prefix."""
        query_lower = query.lower()
        results = []
        raw_entities = [_dict_to_entity(v) for v in self._entities.list_values()]
        for entity in raw_entities:
            if entity_type and entity.entity_type != entity_type:
                continue
            if (
                query_lower in entity.display_label.lower()
                or query_lower in entity.privacy_id.lower()
            ):
                results.append(entity)
            if len(results) >= limit:
                break
        return results

    @property
    def node_count(self) -> int:
        return len(self._entities.list_values())

    @property
    def edge_count(self) -> int:
        return len(self._relationships.list_values())

    def get_stats(self) -> dict:
        """Graph statistics for the dashboard."""
        type_counts: dict[str, int] = defaultdict(int)
        risk_counts: dict[str, int] = defaultdict(int)
        raw_entities = [_dict_to_entity(v) for v in self._entities.list_values()]
        for entity in raw_entities:
            type_counts[entity.entity_type.value] += 1
            risk_counts[entity.risk_level.value] += 1

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "nodes_by_type": dict(type_counts),
            "nodes_by_risk": dict(risk_counts),
            "cluster_count": len(self.detect_clusters(min_size=3)),
        }

    # ── Private helpers ────────────────────────

    def _detect_subgraph_clusters(self, node_ids: set[str]) -> list[list[str]]:
        """Find clusters within a subset of nodes."""
        visited: set[str] = set()
        clusters: list[list[str]] = []

        for nid in node_ids:
            if nid in visited:
                continue
            component: list[str] = []
            queue: deque[str] = deque([nid])
            while queue:
                current = queue.popleft()
                if current in visited or current not in node_ids:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor_id, _ in self._adjacency.get(current, set()):
                    if neighbor_id not in visited and neighbor_id in node_ids:
                        queue.append(neighbor_id)
            if len(component) >= 2:
                clusters.append(component)

        return clusters
