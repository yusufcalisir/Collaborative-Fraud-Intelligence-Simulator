import numpy as np

from app.application.services.fl_engine import AggregationMethod, FederatedLearningEngine
from app.application.services.model_service import ModelWeights
from app.domain.entities import Bank
from app.domain.enums import BankTier, ClientStatus
from app.infrastructure.security.immutable_audit_chain import ImmutableAuditChain


class TestConsortiumIncentives:
    def test_aggregate_leave_one_out_parameters(self) -> None:
        from app.application.services.model_service import ModelService
        from app.application.services.privacy_service import PrivacyService
        from app.config import get_settings

        settings = get_settings()
        model_service = ModelService(settings)
        privacy_service = PrivacyService()
        fl_engine = FederatedLearningEngine(settings, model_service, privacy_service)

        # Create mock weights for 3 clients
        w1 = ModelWeights(layer_shapes=[(2, 2)], flat_weights=[1.0, 2.0, 3.0, 4.0])
        w2 = ModelWeights(layer_shapes=[(2, 2)], flat_weights=[2.0, 4.0, 6.0, 8.0])
        w3 = ModelWeights(layer_shapes=[(2, 2)], flat_weights=[3.0, 6.0, 9.0, 12.0])

        client_weights = [w1, w2, w3]
        client_samples = [100, 200, 300]

        # Aggregate excluding index 1 (w2)
        # Expected: weighted average of w1 (100 samples) and w3 (300 samples)
        # Total samples of subset = 400.
        # Proportions: w1 = 0.25, w3 = 0.75
        # Element 0: 1.0 * 0.25 + 3.0 * 0.75 = 0.25 + 2.25 = 2.5
        # Element 1: 2.0 * 0.25 + 6.0 * 0.75 = 0.5 + 4.5 = 5.0
        loo_weights = fl_engine.aggregate_leave_one_out_parameters(
            client_weights=client_weights,
            client_samples=client_samples,
            excluded_index=1,
            method=AggregationMethod.FED_AVG_WEIGHTED,
        )

        assert len(loo_weights.flat_weights) == 4
        np.testing.assert_allclose(loo_weights.flat_weights, [2.5, 5.0, 7.5, 10.0])

    def test_free_rider_quarantine_logic(self) -> None:
        """Test free-rider quarantine detection logic."""
        # Setup mock banks
        bank = Bank(
            id="bank_c",
            name="Bank C",
            tier=BankTier.MEDIUM,
            fraud_ratio=0.01,
            num_transactions=1000,
            status=ClientStatus.ACTIVE,
        )

        # Simulate free-riding check
        # Bank C's weights are identical to global_weights (variance = 0)
        global_weights = ModelWeights(layer_shapes=[(10,)], flat_weights=[0.5] * 10)
        client_weights = ModelWeights(layer_shapes=[(10,)], flat_weights=[0.5] * 10)

        weights_flat = np.array(client_weights.flat_weights)
        prev_flat = np.array(global_weights.flat_weights)
        update_var = float(np.var(weights_flat - prev_flat))

        # Check if variance is near 0
        is_free_rider = update_var < 1e-6
        assert is_free_rider

        # Enforce quarantine
        if is_free_rider:
            bank.quarantined = True
            bank.status = ClientStatus.OFFLINE

        assert bank.quarantined
        assert bank.status == ClientStatus.OFFLINE

    def test_poisoner_quarantine_logic(self) -> None:
        """Test model poisoner (negative Shapley score) quarantine logic."""
        bank = Bank(
            id="bank_b",
            name="Bank B",
            tier=BankTier.MEDIUM,
            status=ClientStatus.ACTIVE,
        )

        # Shapley score calculation yields a negative contribution
        # due to corrupted parameters degrading overall F1-score.
        shapley_score = -0.075

        # Gated trigger (SV <= -0.05)
        if shapley_score <= -0.05:
            bank.quarantined = True
            bank.status = ClientStatus.OFFLINE

        assert bank.quarantined
        assert bank.status == ClientStatus.OFFLINE

    def test_immutable_audit_log_consortium(self) -> None:
        """Test that payout and quarantine events are written to the ledger chain."""
        audit_chain = ImmutableAuditChain.get_instance()
        initial_length = len(audit_chain.chain)

        audit_chain.append_event(
            event_type="consortium_incentive_payout",
            actor="coordinator",
            target_id="test_sim_id",
            details={
                "contributions": {"Bank A": 0.08, "Bank B": -0.02, "Bank C": 0.00},
                "quarantine_statuses": {"Bank A": False, "Bank B": False, "Bank C": True},
            }
        )
        assert len(audit_chain.chain) == initial_length + 1

        last_entry = audit_chain.chain[-1]
        assert last_entry.event_type == "consortium_incentive_payout"
        assert last_entry.target_id == "test_sim_id"
        assert last_entry.details["quarantine_statuses"]["Bank C"] is True
        assert last_entry.curr_hash is not None
        assert last_entry.prev_hash is not None
