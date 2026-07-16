"""Unit tests for GNN Privacy Audit Service (LRA and MIA attacks)."""

from __future__ import annotations

import numpy as np
import pytest

from app.application.services.privacy_audit_service import PrivacyAuditService


@pytest.fixture
def audit_service() -> PrivacyAuditService:
    return PrivacyAuditService()


class TestPrivacyAuditService:
    def test_audit_link_reconstruction_empty(self, audit_service: PrivacyAuditService) -> None:
        result = audit_service.audit_link_reconstruction(
            embeddings={},
            adjacency_lists=[],
            node_id_to_index={},
        )
        assert result["link_leakage_auc"] == 0.5
        assert result["risk_tier"] == "safe"

    def test_audit_link_reconstruction_leakage_measurement(
        self, audit_service: PrivacyAuditService
    ) -> None:
        # 3 nodes: index 0, 1, 2
        # Embs: node_0 and node_1 have identical embeddings (perfect cosine similarity 1.0)
        # and they are linked. Node_2 has an orthogonal embedding.
        embeddings = {
            "node_0": np.array([1.0, 0.0]),
            "node_1": np.array([1.0, 0.0]),
            "node_2": np.array([0.0, 1.0]),
        }
        node_id_to_index = {"node_0": 0, "node_1": 1, "node_2": 2}

        # Positive link between 0 and 1
        adjacency_lists = [[1], [0], []]

        result = audit_service.audit_link_reconstruction(
            embeddings=embeddings,
            adjacency_lists=adjacency_lists,
            node_id_to_index=node_id_to_index,
        )

        assert "link_leakage_auc" in result
        # AUC should be computed and be >= 0.5
        assert result["link_leakage_auc"] >= 0.5
        assert result["risk_tier"] in ("low_risk", "moderate_risk", "high_risk")

    def test_audit_membership_inference_empty(self, audit_service: PrivacyAuditService) -> None:
        result = audit_service.audit_membership_inference(
            train_losses=[],
            test_losses=[],
        )
        assert result["membership_leakage_asr"] == 0.5
        assert result["risk_tier"] == "safe"

    def test_audit_membership_inference_leakage_measurement(
        self, audit_service: PrivacyAuditService
    ) -> None:
        # Member losses are significantly lower than non-member losses (perfect leakage signal)
        train_losses = [0.01, 0.02, 0.03, 0.015, 0.025]
        test_losses = [0.5, 0.6, 0.45, 0.55, 0.7]

        result = audit_service.audit_membership_inference(
            train_losses=train_losses,
            test_losses=test_losses,
        )

        assert "membership_leakage_asr" in result
        # The threshold classifier should correctly separate them with high accuracy (ASR near 1.0)
        assert result["membership_leakage_asr"] >= 0.8
        assert result["risk_tier"] == "high_risk"

    def test_audit_membership_inference_random_chance(
        self, audit_service: PrivacyAuditService
    ) -> None:
        # Train and test losses are identical (random distribution, zero leakage signal)
        train_losses = [0.1, 0.2, 0.3, 0.4, 0.5]
        test_losses = [0.1, 0.2, 0.3, 0.4, 0.5]

        result = audit_service.audit_membership_inference(
            train_losses=train_losses,
            test_losses=test_losses,
        )

        assert (
            result["membership_leakage_asr"] == 0.5
        )  # Median threshold splits them: TP=3, TN=2 -> ASR = 5/10 = 0.5
        assert result["risk_tier"] == "low_risk"
