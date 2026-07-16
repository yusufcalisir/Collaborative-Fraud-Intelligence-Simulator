"""Privacy Leakage Audit Service for Federated Learning.

Performs active audits against Link Reconstruction Attacks (LRA) and
Membership Inference Attacks (MIA) to quantify the privacy boundaries of shared parameters.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class PrivacyAuditService:
    """Audits federated updates and representation embeddings for data leakage."""

    def audit_link_reconstruction(
        self,
        embeddings: dict[str, np.ndarray],
        adjacency_lists: list[list[int]],
        node_id_to_index: dict[str, int],
    ) -> dict[str, Any]:
        """Perform a Link Reconstruction Attack (LRA) audit on node embeddings.

        Evaluates how easily an adversary can reconstruct transaction links
        based on the similarity of shared entity embeddings.

        Returns:
            Dict containing the leakage AUC score and classification risk tier.
        """
        if not embeddings or not adjacency_lists or not node_id_to_index:
            return {
                "link_leakage_auc": 0.5,
                "risk_tier": "safe",
                "message": "Insufficient graph structure to perform LRA audit.",
            }

        # Convert embeddings to matrix aligned with indices
        n_nodes = len(node_id_to_index)
        emb_dim = next(iter(embeddings.values())).shape[0]
        emb_matrix = np.zeros((n_nodes, emb_dim))
        for node_id, idx in node_id_to_index.items():
            if node_id in embeddings:
                emb_matrix[idx] = embeddings[node_id]

        # Normalize embeddings to unit sphere for cosine similarity
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        norm_emb = emb_matrix / norms

        # Gather positive edges (actual links)
        pos_scores: list[float] = []
        for u in range(min(n_nodes, len(adjacency_lists))):
            for v in adjacency_lists[u]:
                if v < n_nodes:
                    sim = float(np.dot(norm_emb[u], norm_emb[v]))
                    pos_scores.append(sim)

        # Gather negative edges (random non-links)
        neg_scores: list[float] = []
        rng = np.random.default_rng(42)
        n_pos = len(pos_scores)
        if n_pos == 0:
            return {
                "link_leakage_auc": 0.5,
                "risk_tier": "safe",
                "message": "No transaction links found in the subgraph.",
            }

        # Sample negative pairs
        attempts = 0
        while len(neg_scores) < n_pos and attempts < n_pos * 10:
            u = int(rng.integers(0, n_nodes))
            v = int(rng.integers(0, n_nodes))
            if u != v and (u >= len(adjacency_lists) or v not in adjacency_lists[u]):
                sim = float(np.dot(norm_emb[u], norm_emb[v]))
                neg_scores.append(sim)
            attempts += 1

        if not neg_scores:
            neg_scores = [0.0] * n_pos

        # Calculate ROC AUC of classification (LRA attack success rate)
        # Sort score thresholds and compute True Positive vs. False Positive Rates
        all_scores = np.concatenate([pos_scores, neg_scores])
        all_labels = np.concatenate([np.ones(len(pos_scores)), np.zeros(len(neg_scores))])

        sort_indices = np.argsort(all_scores)[::-1]
        sorted_labels = all_labels[sort_indices]

        tps = np.cumsum(sorted_labels)
        fps = np.cumsum(1 - sorted_labels)

        tpr = tps / len(pos_scores)
        fpr = fps / len(neg_scores)

        # Integrate using trapezoidal rule to find AUC
        auc = 0.0
        prev_fpr = 0.0
        prev_tpr = 0.0
        for idx in range(len(tpr)):
            curr_fpr = float(fpr[idx])
            curr_tpr = float(tpr[idx])
            auc += (curr_tpr + prev_tpr) * (curr_fpr - prev_fpr) / 2.0
            prev_fpr = curr_fpr
            prev_tpr = curr_tpr
        auc = max(0.5, min(1.0, auc))  # Clip between baseline random guess and complete leakage

        if auc < 0.65:
            risk_tier = "low_risk"
        elif auc < 0.85:
            risk_tier = "moderate_risk"
        else:
            risk_tier = "high_risk"

        return {
            "link_leakage_auc": round(auc, 4),
            "risk_tier": risk_tier,
            "num_positive_edges_audited": len(pos_scores),
            "num_negative_edges_audited": len(neg_scores),
        }

    def audit_membership_inference(
        self,
        train_losses: list[float],
        test_losses: list[float],
    ) -> dict[str, Any]:
        """Perform a Membership Inference Attack (MIA) audit using model loss checks.

        Evaluates if an attacker can infer whether specific transaction samples
        were used in local model training by checking gradient updates/losses.

        Returns:
            Dict containing the attack success rate (ASR) and risk classification.
        """
        if not train_losses or not test_losses:
            return {
                "membership_leakage_asr": 0.5,
                "risk_tier": "safe",
                "message": "Insufficient loss history to perform MIA audit.",
            }

        # Membership Inference: Members typically have smaller loss than non-members.
        # Find optimal threshold to separate train and test losses.
        all_losses = train_losses + test_losses
        threshold = float(np.median(all_losses))

        # Attacker classifier: if loss < threshold, predict MEMBER (1), else NON-MEMBER (0)
        correct_predictions = 0
        for loss in train_losses:
            if loss <= threshold:
                correct_predictions += 1  # True Positive (Member correctly inferred)
        for loss in test_losses:
            if loss > threshold:
                correct_predictions += 1  # True Negative (Non-member correctly inferred)

        asr = float(correct_predictions / (len(train_losses) + len(test_losses)))
        asr = max(0.5, min(1.0, asr))  # Limit between 0.5 (random guess) and 1.0 (perfect MIA)

        if asr < 0.60:
            risk_tier = "low_risk"
        elif asr < 0.75:
            risk_tier = "moderate_risk"
        else:
            risk_tier = "high_risk"

        return {
            "membership_leakage_asr": round(asr, 4),
            "risk_tier": risk_tier,
            "num_train_samples_audited": len(train_losses),
            "num_test_samples_audited": len(test_losses),
        }
