"""Unit tests for ModelRegistryVault, ModelCheckpoint, and promotion gating (Section 13.2).

Covers:
- Checkpoint registration and SHA-256 digest computation
- HSM digital signature envelope generation and verification
- Promotion gating (Dual Sign-Off + HSM Signature verification)
- Automated archiving of previous production models
- Zero-downtime production rollback to archived models
- JSON serialization of ModelCheckpoint manifests
"""

from __future__ import annotations

import pytest

from app.domain.model_governance import (
    InvalidSignatureError,
    ModelCheckpoint,
    ModelGovernanceError,
    ModelRegistryVault,
    ModelStatus,
)

SIGNING_KEY = b"hsm-production-vault-signing-key-secret"
WRONG_KEY = b"wrong-unauthorized-key-secret"

VALID_SIGNOFFS = [
    {
        "role": "ml_engineer",
        "user": "dr.smith@bank.com",
        "signature": "rsa4096_sig_engineer_hash123",
    },
    {
        "role": "compliance_officer",
        "user": "auditor.jones@bank.com",
        "signature": "rsa4096_sig_compliance_hash456",
    },
]

INCOMPLETE_SIGNOFFS = [
    {
        "role": "ml_engineer",
        "user": "dr.smith@bank.com",
        "signature": "rsa4096_sig_engineer_hash123",
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def vault() -> ModelRegistryVault:
    return ModelRegistryVault()


@pytest.fixture()
def registered_checkpoint(vault: ModelRegistryVault) -> ModelCheckpoint:
    return vault.register_checkpoint(
        version_str="v1.0.0",
        weights_bytes=b"dummy_fl_model_weights_tensor_v1",
        hyperparameters={"learning_rate": 0.01, "batch_size": 64},
        dataset_hash="a" * 64,
        dp_epsilon=1.5,
        dp_delta=1e-5,
    )


# ---------------------------------------------------------------------------
# 1. TestModelRegistryRegistration
# ---------------------------------------------------------------------------

class TestModelRegistryRegistration:
    def test_register_checkpoint_creates_candidate_checkpoint(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Newly registered checkpoint must default to CANDIDATE status."""
        assert registered_checkpoint.status == ModelStatus.CANDIDATE
        assert registered_checkpoint.version.to_tag() == "v1.0.0"
        assert registered_checkpoint.model_id in [c.model_id for c in vault.list_checkpoints()]

    def test_register_checkpoint_computes_sha256_digests(
        self, registered_checkpoint: ModelCheckpoint
    ):
        """Weights SHA-256 and hyperparameters SHA-256 digests must be computed correctly."""
        assert len(registered_checkpoint.weights_sha256) == 64
        assert len(registered_checkpoint.hyperparams_sha256) == 64
        assert int(registered_checkpoint.weights_sha256, 16) > 0
        assert int(registered_checkpoint.hyperparams_sha256, 16) > 0

    def test_list_checkpoints_filters_by_status(self, vault: ModelRegistryVault):
        """list_checkpoints must filter results when status parameter is supplied."""
        cp1 = vault.register_checkpoint(
            "v1.0.0", b"w1", {"lr": 0.01}, "hash1", 1.0, initial_status=ModelStatus.CANDIDATE
        )
        cp2 = vault.register_checkpoint(
            "v1.1.0", b"w2", {"lr": 0.02}, "hash2", 1.0, initial_status=ModelStatus.DRAFT
        )

        candidates = vault.list_checkpoints(ModelStatus.CANDIDATE)
        drafts = vault.list_checkpoints(ModelStatus.DRAFT)

        assert cp1 in candidates
        assert cp2 not in candidates
        assert cp2 in drafts
        assert cp1 not in drafts


# ---------------------------------------------------------------------------
# 2. TestModelRegistrySigning
# ---------------------------------------------------------------------------

class TestModelRegistrySigning:
    def test_sign_checkpoint_attaches_signature(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """sign_checkpoint must generate and attach a non-empty HMAC signature envelope."""
        sig = vault.sign_checkpoint(registered_checkpoint.model_id, SIGNING_KEY)
        assert sig != ""
        assert len(sig) == 64
        assert registered_checkpoint.hsm_signature == sig

    def test_verify_signature_passes_with_correct_key(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Signature verification must return True for correct key."""
        vault.sign_checkpoint(registered_checkpoint.model_id, SIGNING_KEY)
        assert vault.verify_checkpoint_signature(registered_checkpoint.model_id, SIGNING_KEY) is True

    def test_verify_signature_fails_with_wrong_key(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Signature verification must return False for an unauthorized key."""
        vault.sign_checkpoint(registered_checkpoint.model_id, SIGNING_KEY)
        assert vault.verify_checkpoint_signature(registered_checkpoint.model_id, WRONG_KEY) is False

    def test_verify_signature_fails_if_unsigned(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Signature verification must return False if checkpoint has not been signed."""
        assert vault.verify_checkpoint_signature(registered_checkpoint.model_id, SIGNING_KEY) is False


# ---------------------------------------------------------------------------
# 3. TestModelRegistryPromotion
# ---------------------------------------------------------------------------

class TestModelRegistryPromotion:
    def test_promote_to_production_succeeds_with_valid_signoff_and_signature(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Promotion succeeds when dual sign-off AND valid HSM signature are present."""
        vault.sign_checkpoint(registered_checkpoint.model_id, SIGNING_KEY)

        promoted = vault.promote_to_production(
            registered_checkpoint.model_id,
            sign_offs=VALID_SIGNOFFS,
            signing_key=SIGNING_KEY,
        )

        assert promoted.status == ModelStatus.PRODUCTION
        assert promoted.promoted_at is not None
        assert vault.get_production_model() == promoted

    def test_promote_fails_without_signoffs(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Promotion fails with ModelGovernanceError if no sign-offs are provided."""
        vault.sign_checkpoint(registered_checkpoint.model_id, SIGNING_KEY)

        with pytest.raises(ModelGovernanceError, match="Promotion Gate Failed"):
            vault.promote_to_production(
                registered_checkpoint.model_id,
                sign_offs=[],
                signing_key=SIGNING_KEY,
            )

    def test_promote_fails_with_incomplete_signoffs(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Promotion fails if missing compliance_officer sign-off."""
        vault.sign_checkpoint(registered_checkpoint.model_id, SIGNING_KEY)

        with pytest.raises(ModelGovernanceError, match="Missing required sign-off roles"):
            vault.promote_to_production(
                registered_checkpoint.model_id,
                sign_offs=INCOMPLETE_SIGNOFFS,
                signing_key=SIGNING_KEY,
            )

    def test_promote_fails_without_valid_hsm_signature(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Promotion fails with InvalidSignatureError if checkpoint signature is invalid/missing."""
        # Checkpoint is NOT signed
        with pytest.raises(InvalidSignatureError, match="Invalid Signature Gate Failed"):
            vault.promote_to_production(
                registered_checkpoint.model_id,
                sign_offs=VALID_SIGNOFFS,
                signing_key=SIGNING_KEY,
            )

    def test_promote_archives_previous_production_model(self, vault: ModelRegistryVault):
        """Promoting a new model must demote the existing PRODUCTION model to ARCHIVED."""
        # 1. Register and promote v1.0.0
        cp1 = vault.register_checkpoint("v1.0.0", b"w1", {"lr": 0.01}, "hash1", 1.0)
        vault.sign_checkpoint(cp1.model_id, SIGNING_KEY)
        vault.promote_to_production(cp1.model_id, VALID_SIGNOFFS, SIGNING_KEY)
        assert cp1.status == ModelStatus.PRODUCTION

        # 2. Register and promote v2.0.0
        cp2 = vault.register_checkpoint("v2.0.0", b"w2", {"lr": 0.01}, "hash2", 1.0)
        vault.sign_checkpoint(cp2.model_id, SIGNING_KEY)
        vault.promote_to_production(cp2.model_id, VALID_SIGNOFFS, SIGNING_KEY)

        # Assert cp1 is now ARCHIVED and cp2 is PRODUCTION
        assert cp1.status == ModelStatus.ARCHIVED
        assert cp2.status == ModelStatus.PRODUCTION
        assert vault.get_production_model() == cp2


# ---------------------------------------------------------------------------
# 4. TestModelRegistryRollback
# ---------------------------------------------------------------------------

class TestModelRegistryRollback:
    def test_rollback_production_demotes_active_and_restores_archived(
        self, vault: ModelRegistryVault
    ):
        """Rollback demotes active model to ROLLED_BACK and restores most recent ARCHIVED model to PRODUCTION."""
        # Setup: promote v1.0.0 then v2.0.0 (v1.0.0 becomes ARCHIVED, v2.0.0 becomes PRODUCTION)
        cp1 = vault.register_checkpoint("v1.0.0", b"w1", {"lr": 0.01}, "hash1", 1.0)
        vault.sign_checkpoint(cp1.model_id, SIGNING_KEY)
        vault.promote_to_production(cp1.model_id, VALID_SIGNOFFS, SIGNING_KEY)

        cp2 = vault.register_checkpoint("v2.0.0", b"w2", {"lr": 0.01}, "hash2", 1.0)
        vault.sign_checkpoint(cp2.model_id, SIGNING_KEY)
        vault.promote_to_production(cp2.model_id, VALID_SIGNOFFS, SIGNING_KEY)

        assert vault.get_production_model() == cp2

        # Execute rollback
        rolled_back, restored = vault.rollback_production(reason="AUC dropped below 0.65 in production telemetry")

        assert rolled_back == cp2
        assert cp2.status == ModelStatus.ROLLED_BACK
        assert restored == cp1
        assert cp1.status == ModelStatus.PRODUCTION
        assert vault.get_production_model() == cp1

    def test_rollback_fails_if_no_active_production_model(self, vault: ModelRegistryVault):
        """Rollback fails with ModelGovernanceError if no model is currently PRODUCTION."""
        with pytest.raises(ModelGovernanceError, match="No active PRODUCTION model found"):
            vault.rollback_production(reason="Test failure")

    def test_rollback_fails_if_no_archived_model_available(
        self, vault: ModelRegistryVault, registered_checkpoint: ModelCheckpoint
    ):
        """Rollback fails if there is a PRODUCTION model but no previous ARCHIVED model to restore."""
        vault.sign_checkpoint(registered_checkpoint.model_id, SIGNING_KEY)
        vault.promote_to_production(registered_checkpoint.model_id, VALID_SIGNOFFS, SIGNING_KEY)

        with pytest.raises(ModelGovernanceError, match="No ARCHIVED checkpoint available"):
            vault.rollback_production(reason="No fallback model exists")


# ---------------------------------------------------------------------------
# 5. TestModelCheckpointSerialization
# ---------------------------------------------------------------------------

class TestModelCheckpointSerialization:
    def test_model_checkpoint_to_dict_contains_all_manifest_keys(
        self, registered_checkpoint: ModelCheckpoint
    ):
        """to_dict() must return a JSON-serializable map with all manifest fields."""
        data = registered_checkpoint.to_dict()

        assert data["model_id"] == registered_checkpoint.model_id
        assert data["version"] == "v1.0.0"
        assert data["status"] == "CANDIDATE"
        assert "weights_sha256" in data
        assert "hyperparams_sha256" in data
        assert "dataset_hash" in data
        assert "dp_epsilon" in data
        assert "lineage" in data
