import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import torch

from app.application.services.graph_embedding_model import NODE_FEATURE_DIM, extract_node_features

logger = logging.getLogger(__name__)


class StreamingGraphService:
    """Manages the real-time sliding-window transaction graph stream for GNNs."""

    def __init__(self, max_window_minutes: int = 60) -> None:
        self.max_window_minutes = max_window_minutes

        # In-memory graph representation for the sliding window
        self.nodes: dict[str, dict[str, Any]] = {}  # node_id -> node_attributes
        self.edges: list[
            dict[str, Any]
        ] = []  # list of {from_id, to_id, amount, timestamp, bank_id}

        # Node degree tracking for feature normalization
        self.node_degrees: dict[str, int] = defaultdict(int)

        # Fast lookup mapping for node IDs to tensor indices
        self.node_to_index: dict[str, int] = {}
        self.index_to_node: dict[int, str] = {}

    def add_transaction(self, tx: dict[str, Any]) -> None:
        """Ingest a new transaction into the streaming graph buffer."""
        from_id = tx.get("sender_id") or tx.get("source_owner")
        to_id = tx.get("receiver_id") or tx.get("destination_owner")
        amount = float(tx.get("amount") or 0.0)
        timestamp_str = tx.get("timestamp")
        bank_id = tx.get("bank_id")

        if not from_id or not to_id:
            return

        # Parse timestamp
        try:
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now(UTC)
        except Exception:
            timestamp = datetime.now(UTC)

        # Add or update nodes in the current window
        if from_id not in self.nodes:
            self.nodes[from_id] = {
                "entity_type": "customer",
                "risk_level": "high" if tx.get("is_fraud") else "minimal",
                "alert_count": 1 if tx.get("is_fraud") else 0,
                "first_seen": timestamp_str or timestamp.isoformat(),
                "last_seen": timestamp_str or timestamp.isoformat(),
            }
        else:
            self.nodes[from_id]["last_seen"] = timestamp_str or timestamp.isoformat()
            if tx.get("is_fraud"):
                self.nodes[from_id]["alert_count"] += 1
                self.nodes[from_id]["risk_level"] = "high"

        if to_id not in self.nodes:
            self.nodes[to_id] = {
                "entity_type": "customer",
                "risk_level": "high" if tx.get("is_fraud") else "minimal",
                "alert_count": 1 if tx.get("is_fraud") else 0,
                "first_seen": timestamp_str or timestamp.isoformat(),
                "last_seen": timestamp_str or timestamp.isoformat(),
            }
        else:
            self.nodes[to_id]["last_seen"] = timestamp_str or timestamp.isoformat()
            if tx.get("is_fraud"):
                self.nodes[to_id]["alert_count"] += 1
                self.nodes[to_id]["risk_level"] = "high"

        # Record edge
        self.edges.append(
            {
                "from_id": from_id,
                "to_id": to_id,
                "amount": amount,
                "timestamp": timestamp,
                "bank_id": bank_id,
            }
        )

        # Update degrees
        self.node_degrees[from_id] += 1
        self.node_degrees[to_id] += 1

        # Re-index node mapping if there are new nodes
        self._rebuild_indices()

        # Prune expired edges to keep sliding window size bound
        self.prune_expired_edges(self.max_window_minutes)

    def _rebuild_indices(self) -> None:
        """Rebuild mapping between node string IDs and tensor indices."""
        self.node_to_index = {}
        self.index_to_node = {}
        for idx, node_id in enumerate(self.nodes.keys()):
            self.node_to_index[node_id] = idx
            self.index_to_node[idx] = node_id

    def prune_expired_edges(self, max_age_minutes: int) -> None:
        """Prune edges outside of the sliding window and remove orphan nodes."""
        now = datetime.now(UTC)
        cutoff_time = now - timedelta(minutes=max_age_minutes)

        # Filter active edges
        active_edges = []
        active_nodes_set = set()

        # Reset degrees for recounting
        self.node_degrees.clear()

        for edge in self.edges:
            # Handle timezone-naive vs naive comparisons
            edge_time = edge["timestamp"]
            if edge_time.tzinfo is None:
                edge_time = edge_time.replace(tzinfo=UTC)

            if edge_time >= cutoff_time:
                active_edges.append(edge)
                active_nodes_set.add(edge["from_id"])
                active_nodes_set.add(edge["to_id"])
                self.node_degrees[edge["from_id"]] += 1
                self.node_degrees[edge["to_id"]] += 1

        self.edges = active_edges

        # Remove nodes no longer connected in the sliding window
        pruned_nodes = {}
        for node_id in active_nodes_set:
            if node_id in self.nodes:
                pruned_nodes[node_id] = self.nodes[node_id]

        self.nodes = pruned_nodes
        self._rebuild_indices()

    def get_active_subgraph_tensors(self) -> tuple[torch.Tensor, torch.Tensor, list[float]]:
        """Construct PyTorch-compatible GNN tensors from the active sliding window.

        Returns:
            Tuple containing:
            - features (Tensor of shape [N, NODE_FEATURE_DIM])
            - edge_index (Tensor of shape [2, E])
            - labels (list of float binary targets, length N)
        """
        n_nodes = len(self.nodes)
        if n_nodes == 0:
            return (
                torch.empty((0, NODE_FEATURE_DIM), dtype=torch.float32),
                torch.empty((2, 0), dtype=torch.long),
                [],
            )

        # Build feature matrix
        feature_list = []
        labels = []
        for node_id in self.nodes:
            attrs = self.nodes[node_id]
            degree = self.node_degrees[node_id]
            feat = extract_node_features(attrs, degree=degree)
            feature_list.append(feat)

            # Labeled as fraud if risk is high/critical
            risk = attrs.get("risk_level", "minimal")
            is_fraud = 1.0 if risk in ("high", "critical") else 0.0
            labels.append(is_fraud)

        features = torch.tensor(np.array(feature_list), dtype=torch.float32)

        # Build edge index tensor
        edge_indices = []
        for edge in self.edges:
            f_idx = self.node_to_index.get(edge["from_id"])
            t_idx = self.node_to_index.get(edge["to_id"])
            if f_idx is not None and t_idx is not None:
                edge_indices.append([f_idx, t_idx])
                edge_indices.append([t_idx, f_idx])  # Treat as undirected for message-passing

        if len(edge_indices) > 0:
            edge_index = torch.tensor(edge_indices, dtype=torch.long).t().contiguous()
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)

        return features, edge_index, labels

    def get_status_summary(self) -> dict[str, Any]:
        """Return status telemetry info of the streaming graph."""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "window_size_minutes": self.max_window_minutes,
        }
