"""Graph Analytics Service.

Provides advanced graph algorithms: PageRank-like risk propagation,
community risk density clustering, and temporal edge velocity anomaly detection.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any

from app.application.services.entity_resolution import EntityResolutionService
from app.application.services.graph_engine import GraphEngine
from app.domain.enums import RelationshipType, RiskLevel

logger = logging.getLogger(__name__)

# Map risk level to base numeric scores (0 to 1000)
RISK_LEVEL_TO_SCORE = {
    RiskLevel.CRITICAL: 1000.0,
    RiskLevel.HIGH: 800.0,
    RiskLevel.MEDIUM: 500.0,
    RiskLevel.LOW: 200.0,
    RiskLevel.MINIMAL: 50.0,
}

# Edge relationship multipliers for risk propagation
RELATIONSHIP_MULTIPLIERS = {
    RelationshipType.OWNS: 1.0,
    RelationshipType.USES: 0.9,
    RelationshipType.TRANSACTS_WITH: 0.8,
    RelationshipType.SHARES_DEVICE: 0.9,
    RelationshipType.SHARES_IP: 0.5,
    RelationshipType.LINKED_ALERT: 1.0,
    RelationshipType.SAME_ENTITY: 1.0,
}


def score_to_risk_level(score: float) -> RiskLevel:
    if score >= 800.0:
        return RiskLevel.CRITICAL
    if score >= 600.0:
        return RiskLevel.HIGH
    if score >= 400.0:
        return RiskLevel.MEDIUM
    if score >= 200.0:
        return RiskLevel.LOW
    return RiskLevel.MINIMAL


class GraphAnalyticsService:
    """Implements graph-based fraud detection algorithms."""

    def __init__(
        self,
        graph_engine: GraphEngine | None = None,
        entity_service: EntityResolutionService | None = None,
    ) -> None:
        self.graph_engine = graph_engine or GraphEngine()
        self.entity_service = entity_service or EntityResolutionService()

    def propagate_risk(self, decay_factor: float = 0.85) -> dict[str, Any]:
        """Propagate risk scores from flagged entities through the graph.

        Uses an iterative propagation similar to PageRank with decay.
        Saves updated risk levels back to entity storage.
        """
        # Load all entities and relationships
        entities = {e.id: e for e in self.entity_service.get_entities(limit=1000)}
        relationships = self.entity_service.get_relationships()

        if not entities:
            return {"updated_nodes_count": 0, "max_score": 0.0, "avg_score_change": 0.0}

        # Initialize base and current scores
        base_scores = {
            eid: RISK_LEVEL_TO_SCORE.get(e.risk_level, 50.0) for eid, e in entities.items()
        }
        current_scores = base_scores.copy()

        # Build adjacency list representation: source_id -> list of (target_id, relationship_type, confidence)
        adjacency = defaultdict(list)
        for r in relationships:
            if r.source_entity_id in entities and r.target_entity_id in entities:
                adjacency[r.source_entity_id].append(
                    (r.target_entity_id, r.relationship_type, r.confidence)
                )
                adjacency[r.target_entity_id].append(
                    (r.source_entity_id, r.relationship_type, r.confidence)
                )

        # Run 3 iterations of Jacobi-style propagation
        iterations = 3
        updated_count = 0
        total_change = 0.0
        max_score = 0.0

        for _ in range(iterations):
            next_scores = current_scores.copy()
            for u in entities:
                # Max propagated score from all neighbors
                propagated_scores = []
                for v, rel_type, confidence in adjacency[u]:
                    mult = RELATIONSHIP_MULTIPLIERS.get(rel_type, 0.5)
                    score_from_neighbor = current_scores[v] * decay_factor * mult * confidence
                    propagated_scores.append(score_from_neighbor)

                if propagated_scores:
                    next_scores[u] = max(base_scores[u], max(propagated_scores))

            current_scores = next_scores

        # Save changes if risk level changed
        for eid, new_score in current_scores.items():
            old_level = entities[eid].risk_level
            new_level = score_to_risk_level(new_score)
            max_score = max(max_score, new_score)

            if old_level != new_level:
                self.entity_service.update_risk_level(eid, new_level)
                # Also synchronize the graph engine's cache if needed
                updated_count += 1
                diff = abs(new_score - RISK_LEVEL_TO_SCORE.get(old_level, 50.0))
                total_change += diff

        avg_change = total_change / len(entities) if entities else 0.0
        logger.info(
            "Risk propagation completed. Updated %d nodes. Max score: %.2f. Avg change: %.2f",
            updated_count,
            max_score,
            avg_change,
        )

        return {
            "updated_nodes_count": updated_count,
            "max_score": round(max_score, 2),
            "avg_score_change": round(avg_change, 2),
        }

    def get_community_analytics(self, min_size: int = 3) -> list[dict[str, Any]]:
        """Identify communities and calculate fraud/risk densities.

        Returns list of community stats sorted by fraud density and size.
        """
        clusters = self.graph_engine.detect_clusters(min_size=min_size)
        communities = []

        for i, cluster in enumerate(clusters):
            # Load entities in this community
            entities = []
            for eid in cluster:
                e = self.entity_service.get_entity(eid)
                if e:
                    entities.append(e)

            if not entities:
                continue

            # Calculate metrics
            total_nodes = len(entities)
            fraud_nodes = sum(
                1 for e in entities if e.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            )
            fraud_density = fraud_nodes / total_nodes if total_nodes > 0 else 0.0

            total_score = sum(RISK_LEVEL_TO_SCORE.get(e.risk_level, 50.0) for e in entities)
            avg_risk = total_score / total_nodes if total_nodes > 0 else 0.0

            communities.append(
                {
                    "community_id": i,
                    "node_ids": cluster,
                    "size": total_nodes,
                    "fraud_density": round(fraud_density, 4),
                    "average_risk": round(avg_risk, 2),
                }
            )

        # Sort: Fraud density descending, then size descending
        communities.sort(key=lambda c: (c["fraud_density"], c["size"]), reverse=True)
        return communities

    def get_temporal_anomalies(
        self, window_minutes: int = 5, min_edges: int = 3
    ) -> list[dict[str, Any]]:
        """Detect edge creation velocity spikes indicating coordinated fraud.

        Groups relations by window_minutes intervals, identifies spikes,
        and constructs anomaly subgraphs.
        """
        relationships = self.entity_service.get_relationships()
        if not relationships:
            return []

        # Sort relationships by timestamp
        sorted_rels = sorted(relationships, key=lambda r: r.created_at)

        # We construct sliding windows over relationships
        windows = []
        n_rels = len(sorted_rels)

        for i in range(n_rels):
            start_time = sorted_rels[i].created_at
            end_time = start_time + timedelta(minutes=window_minutes)

            # Gather all edges in this window
            window_edges = []
            for j in range(i, n_rels):
                if sorted_rels[j].created_at <= end_time:
                    window_edges.append(sorted_rels[j])
                else:
                    break

            if len(window_edges) >= min_edges:
                windows.append((start_time, end_time, window_edges))

        if not windows:
            return []

        # Sort windows by edge count descending to get the largest spikes
        windows.sort(key=lambda w: len(w[2]), reverse=True)

        anomalies = []
        seen_edges_sets: list[set[str]] = []

        for idx, (start, end, edges) in enumerate(windows):
            edge_ids = {r.id for r in edges}

            # Avoid duplicates / highly overlapping windows
            is_redundant = False
            for s in seen_edges_sets:
                # If 80%+ overlap, skip
                if len(edge_ids & s) / len(edge_ids) > 0.8:
                    is_redundant = True
                    break

            if is_redundant:
                continue

            seen_edges_sets.append(edge_ids)

            # Collect unique nodes involved
            node_ids = set()
            for r in edges:
                node_ids.add(r.source_entity_id)
                node_ids.add(r.target_entity_id)

            # Score anomaly velocity
            # Velocity score is edges/minute scaled
            duration_minutes = (end - start).total_seconds() / 60.0
            if duration_minutes <= 0:
                duration_minutes = 0.1
            velocity = len(edges) / duration_minutes

            anomalies.append(
                {
                    "subgraph_id": idx,
                    "node_ids": list(node_ids),
                    "edges_count": len(edges),
                    "velocity_score": round(velocity, 2),
                    "time_window_start": start.isoformat(),
                    "time_window_end": end.isoformat(),
                }
            )

            # Limit to top 10 anomalies
            if len(anomalies) >= 10:
                break

        return anomalies
