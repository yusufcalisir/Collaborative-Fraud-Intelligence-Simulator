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

from app.domain.entities_phase2 import Entity, Relationship
from app.domain.enums import EntityType, RelationshipType, RiskLevel
from app.domain.value_objects_phase2 import GraphSubgraph

logger = logging.getLogger(__name__)

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
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        # Adjacency list: entity_id → set of (neighbor_id, relationship_id)
        self._adjacency: dict[str, set[tuple[str, str]]] = defaultdict(set)

    def register_entity(self, entity: Entity) -> None:
        """Register an entity in the graph."""
        self._entities[entity.id] = entity

    def register_entities(self, entities: list[Entity]) -> None:
        for entity in entities:
            self.register_entity(entity)

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship (edge) to the graph."""
        self._relationships[relationship.id] = relationship
        self._adjacency[relationship.source_entity_id].add(
            (relationship.target_entity_id, relationship.id)
        )
        self._adjacency[relationship.target_entity_id].add(
            (relationship.source_entity_id, relationship.id)
        )

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
                    rel = self._relationships.get(rel_id)
                    if rel and rel.relationship_type not in relationship_types:
                        continue

                visited.add(neighbor_id)
                entity = self._entities.get(neighbor_id)
                if entity:
                    neighbors.append(entity)
                    queue.append((neighbor_id, current_depth + 1))

        return neighbors

    def detect_clusters(self, min_size: int = 3) -> list[list[str]]:
        """Find connected components (clusters) of at least min_size.

        Clusters of connected entities often indicate fraud rings
        or organized criminal activity.
        """
        visited: set[str] = set()
        clusters: list[list[str]] = []

        for entity_id in self._entities:
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
        if center_entity_id not in self._entities:
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
            entity = self._entities.get(nid)
            if not entity:
                continue

            # Radial layout
            import math
            if nid == center_entity_id:
                x, y = 400, 300
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

            nodes.append({
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
            })

        # Build React Flow edges
        edges = []
        node_id_set = set(node_ids)
        for rel in self._relationships.values():
            if rel.source_entity_id in node_id_set and rel.target_entity_id in node_id_set:
                style = _EDGE_STYLES.get(rel.relationship_type, {})
                edges.append({
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
                })

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
        for entity in self._entities.values():
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
        return len(self._entities)

    @property
    def edge_count(self) -> int:
        return len(self._relationships)

    def get_stats(self) -> dict:
        """Graph statistics for the dashboard."""
        type_counts: dict[str, int] = defaultdict(int)
        risk_counts: dict[str, int] = defaultdict(int)
        for entity in self._entities.values():
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
