import logging

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812

logger = logging.getLogger(__name__)


class GATAttentionLayer(nn.Module):
    """Custom Graph Attention Network (GAT) layer with multi-head attention.

    Computes:
        alpha_ij = softmax_j(LeakyReLU(a^T [W h_i || W h_j]))
    """

    def __init__(self, in_dim: int, out_dim: int, num_heads: int = 2, dropout: float = 0.2) -> None:
        super().__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.num_heads = num_heads
        self.dropout = dropout

        # Weight projection parameters per head
        self.W = nn.Parameter(torch.empty(num_heads, in_dim, out_dim))
        # Attention weight parameters per head
        self.a = nn.Parameter(torch.empty(num_heads, 2 * out_dim, 1))

        # Initialize parameters
        nn.init.xavier_uniform_(self.W.data)
        nn.init.xavier_uniform_(self.a.data)

        self.leaky_relu = nn.LeakyReLU(0.2)
        self.dropout_layer = nn.Dropout(dropout)

    def forward(
        self, h: torch.Tensor, edge_index: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Forward pass of GAT Layer.

        Args:
            h: Node feature tensor [N, in_dim]
            edge_index: Adjacency list tensor [2, E]

        Returns:
            Tuple: (Output embeddings [N, num_heads * out_dim], Attention coefficients [E, num_heads])
        """
        N = h.size(0)
        E = edge_index.size(1)

        if N == 0 or E == 0:
            # Handle empty graph case gracefully
            out = torch.zeros((N, self.num_heads * self.out_dim), device=h.device)
            att = torch.zeros((E, self.num_heads), device=h.device)
            return out, att

        # h_head shape: [num_heads, N, out_dim]
        # Project node features into attention subspaces
        h_projected = torch.matmul(h.unsqueeze(0), self.W)  # [num_heads, N, out_dim]

        # Extract source and target node representations for each edge
        src_nodes = edge_index[0]
        tgt_nodes = edge_index[1]

        # Get projected features for connected nodes: shape [num_heads, E, out_dim]
        h_src = h_projected[:, src_nodes, :]
        h_tgt = h_projected[:, tgt_nodes, :]

        # Concatenate source and target representations: shape [num_heads, E, 2 * out_dim]
        h_concat = torch.cat([h_src, h_tgt], dim=-1)

        # Compute attention coefficients pre-softmax: shape [num_heads, E, 1]
        e = self.leaky_relu(torch.matmul(h_concat, self.a))

        # Softmax over neighbors (for each head)
        # We need to perform softmax grouping by target node ID (src_nodes)
        # To simulate this correctly and fast in PyTorch without pyg dependency:
        alpha = torch.zeros_like(e)
        for i in range(N):
            # Mask representing incoming edges to node i
            mask = tgt_nodes == i
            if mask.any():
                alpha[:, mask, :] = F.softmax(e[:, mask, :], dim=1)

        alpha = self.dropout_layer(alpha).squeeze(-1)  # [num_heads, E]

        # Aggregate neighbor representations weighted by attention coefficients
        h_out = torch.zeros((N, self.num_heads, self.out_dim), device=h.device)
        for head in range(self.num_heads):
            # Sum_{j in N(i)} alpha_ij * W h_j
            # Weighted message passing
            weighted_messages = h_src[head] * alpha[head].unsqueeze(-1)
            # Scatter sum messages to target nodes
            h_out[tgt_nodes, head, :] += weighted_messages

        # Concatenate multi-head outputs: [N, num_heads * out_dim]
        h_out_concat = h_out.view(N, -1)

        return h_out_concat, alpha.t()  # [E, num_heads]


class StreamingGATModel(nn.Module):
    """Streaming Graph Attention Network (GAT) classifier for real-time fraud detection.

    Consists of an attention layer followed by a binary classification layer.
    """

    def __init__(self, in_dim: int, hidden_dim: int = 16, num_heads: int = 2) -> None:
        super().__init__()
        self.gat = GATAttentionLayer(in_dim, hidden_dim, num_heads=num_heads)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * num_heads, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )
        self.optimizer = torch.optim.Adam(self.parameters(), lr=0.01)
        self.loss_fn = nn.BCELoss()

    def forward(
        self, h: torch.Tensor, edge_index: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Compute predictions and return attention weights."""
        embeddings, attention_weights = self.gat(h, edge_index)
        predictions = self.classifier(embeddings).squeeze(-1)
        return predictions, attention_weights

    def online_train_step(
        self, h: torch.Tensor, edge_index: torch.Tensor, labels: torch.Tensor
    ) -> float:
        """Perform one step of backpropagation on the active streaming graph."""
        if h.size(0) == 0 or edge_index.size(1) == 0:
            return 0.0

        self.train()
        self.optimizer.zero_grad()

        preds, _ = self(h, edge_index)
        loss = self.loss_fn(preds, labels)

        loss.backward()
        self.optimizer.step()

        return float(loss.item())
