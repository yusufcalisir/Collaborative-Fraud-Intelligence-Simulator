"""Simulation orchestrator service.

This is the central service that coordinates the full federated learning
simulation pipeline:

1. Generate Non-IID synthetic data for 3 banks
2. Train local-only models (baseline for comparison)
3. Evaluate local models
4. Run N rounds of federated training (FedAvg)
5. Evaluate the global federated model at each bank
6. Produce side-by-side comparison metrics
7. Persist results
8. Broadcast progress via callback

The simulation runs synchronously within a Celery task. The service
itself is stateless — all state is either passed in or persisted to
the database.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from sklearn.model_selection import train_test_split

from app.application.services.data_generator import DataGenerator
from app.application.services.privacy_service import PrivacyService
from app.domain.entities import SimulationRun, TrainingRound
from app.domain.enums import (
    AggregationMethod,
    ClientStatus,
    PrivacyMechanism,
    SimulationStatus,
)

if TYPE_CHECKING:
    from app.application.services.fl_engine import FederatedLearningEngine
    from app.application.services.metrics_service import MetricsService
    from app.application.services.model_service import ModelService
    from app.config import Settings
    from app.domain.value_objects import (
        ModelWeights,
        SimulationConfig,
    )

logger = logging.getLogger(__name__)

# Type for progress callback: (simulation_id, event_type, data)
ProgressCallback = Callable[[str, str, dict[str, Any]], None] | None


class SimulationService:
    """Orchestrates the complete federated learning simulation."""

    def __init__(
        self,
        settings: Settings,
        simulation_repo: Any,  # SimulationRepository
        bank_repo: Any,  # BankRepository
        metrics_repo: Any,  # MetricsRepository
        data_generator: DataGenerator,
        fl_engine: FederatedLearningEngine,
        metrics_service: MetricsService,
        model_service: ModelService,
    ) -> None:
        self.settings = settings
        self.simulation_repo = simulation_repo
        self.bank_repo = bank_repo
        self.metrics_repo = metrics_repo
        self.data_generator = data_generator
        self.fl_engine = fl_engine
        self.metrics_service = metrics_service
        self.model_service = model_service

    def run_simulation(
        self,
        config: SimulationConfig,
        progress_callback: ProgressCallback = None,
    ) -> SimulationRun:
        """Execute the full simulation pipeline.

        This method is designed to be called from a Celery task.
        It's synchronous and can take several minutes depending on
        data volume and number of rounds.
        """
        simulation = SimulationRun(config=config, total_rounds=config.num_rounds)
        simulation.started_at = _now()
        rng = np.random.default_rng(42)

        try:
            # Phase 1: Generate data
            simulation.status = SimulationStatus.GENERATING_DATA
            self._notify(
                progress_callback,
                simulation.id,
                "status",
                {
                    "status": simulation.status,
                    "message": "Generating synthetic transaction data",
                },
            )

            # Scale down datasets aggressively for fast CPU training on
            # constrained environments (Render free tier: 0.1 CPU, 512 MB RAM).
            # 50,000 → 250, 30,000 → 150, 20,000 → 100 transactions
            datasets = self.data_generator.generate_bank_datasets(
                bank_a_size=max(100, config.bank_a_transactions // 200),
                bank_b_size=max(100, config.bank_b_transactions // 200),
                bank_c_size=max(100, config.bank_c_transactions // 200),
            )
            profiles = self.data_generator.create_bank_profiles(datasets)
            banks = self.data_generator.create_bank_entities(datasets, profiles)
            simulation.banks = banks

            # Split into train/test per bank
            bank_data: dict[str, dict[str, np.ndarray]] = {}
            for bank_id, (df, labels) in datasets.items():
                X = DataGenerator.encode_features(df)
                y = labels.values

                X_train, X_test, y_train, y_test = train_test_split(
                    X,
                    y,
                    test_size=0.2,
                    random_state=42,
                    stratify=cast("Any", y),
                )

                bank_data[bank_id] = {
                    "X_train": X_train,
                    "X_test": X_test,
                    "y_train": y_train,
                    "y_test": y_test,
                }

            # Phase 2: Train local models (baseline)
            simulation.status = SimulationStatus.TRAINING_LOCAL
            self._notify(
                progress_callback,
                simulation.id,
                "status",
                {
                    "status": simulation.status,
                    "message": "Training local baseline models",
                },
            )

            for bank in banks:
                data = bank_data[bank.id]
                model = self.model_service.create_model()
                model, loss_history = self.model_service.train_local(
                    model,
                    data["X_train"],
                    data["y_train"],
                    epochs=1,  # Fixed to 1 for fast completion on constrained hosts
                    learning_rate=config.learning_rate,
                    batch_size=config.batch_size,
                )

                eval_dict = self.model_service.evaluate(model, data["X_test"], data["y_test"])
                feat_imp = self.model_service.get_feature_importance(model)
                bank.local_metrics = self.metrics_service.from_eval_dict(eval_dict, feat_imp)

                logger.info(
                    "Local model for %s — F1: %.4f, AUC: %.4f",
                    bank.name,
                    bank.local_metrics.f1_score,
                    bank.local_metrics.auc_roc,
                )

                self._notify(
                    progress_callback,
                    simulation.id,
                    "local_training",
                    {
                        "bank_id": bank.id,
                        "bank_name": bank.name,
                        "metrics": self.metrics_service.metrics_to_dict(bank.local_metrics),
                    },
                )

                # Free memory immediately
                del model
                import gc

                gc.collect()

            # Phase 3: Federated training
            simulation.status = SimulationStatus.TRAINING_FEDERATED
            global_model = self.model_service.create_model()
            global_weights = self.model_service.get_parameters(global_model)
            dropped_banks: set[str] = set()
            privacy_service = PrivacyService()

            enable_dp = config.enable_differential_privacy or getattr(
                config, "privacy_mechanism", None
            ) in (
                PrivacyMechanism.DIFFERENTIAL_PRIVACY,
                PrivacyMechanism.BOTH,
            )
            enable_sa = config.enable_secure_aggregation or getattr(
                config, "privacy_mechanism", None
            ) in (
                PrivacyMechanism.SECURE_AGGREGATION,
                PrivacyMechanism.BOTH,
            )

            if enable_dp:
                budget = privacy_service.get_or_create_budget(
                    simulation.id,
                    config.dp_epsilon,
                    config.dp_delta,
                )

            rounds: list[TrainingRound] = []

            for round_num in range(1, config.num_rounds + 1):
                round_start = time.perf_counter()
                simulation.current_round = round_num

                self._notify(
                    progress_callback,
                    simulation.id,
                    "round_start",
                    {
                        "round": round_num,
                        "total": config.num_rounds,
                    },
                )

                # Determine client availability
                if config.enable_dropout_simulation:
                    client_statuses = self.fl_engine.simulate_client_availability(
                        bank_ids=[b.id for b in banks],
                        dropout_probability=config.dropout_probability,
                        previously_dropped=dropped_banks,
                        enable_reconnect=config.enable_reconnect_simulation,
                        rng=rng,
                    )
                else:
                    client_statuses = {b.id: ClientStatus.ACTIVE for b in banks}

                # Update bank statuses
                for bank in banks:
                    bank.status = client_statuses.get(bank.id, ClientStatus.ACTIVE)

                participating = [
                    b
                    for b in banks
                    if client_statuses[b.id] in (ClientStatus.ACTIVE, ClientStatus.RECONNECTED)
                ]
                dropped_this_round = [
                    b.id
                    for b in banks
                    if client_statuses[b.id] in (ClientStatus.DROPPED, ClientStatus.OFFLINE)
                ]
                dropped_banks = set(dropped_this_round)

                # Skip round if too few participants
                if len(participating) < config.min_clients_per_round:
                    logger.warning(
                        "Round %d: only %d participants (min: %d), skipping",
                        round_num,
                        len(participating),
                        config.min_clients_per_round,
                    )
                    training_round = TrainingRound(
                        round_number=round_num,
                        simulation_id=simulation.id,
                        participating_bank_ids=[],
                        dropped_bank_ids=dropped_this_round,
                        global_loss=0.0,
                    )
                    rounds.append(training_round)
                    continue

                # Local training at each participating bank
                client_weights: list[ModelWeights] = []
                client_samples: list[int] = []
                per_bank_loss: dict[str, float] = {}

                for bank in participating:
                    data = bank_data[bank.id]

                    # Start from global model
                    local_model = self.model_service.create_model()
                    local_model = self.model_service.set_parameters(local_model, global_weights)

                    # Train locally
                    local_model, loss_hist = self.model_service.train_local(
                        local_model,
                        data["X_train"],
                        data["y_train"],
                        epochs=1,  # Fixed to 1 for fast completion on constrained hosts
                        learning_rate=config.learning_rate,
                        batch_size=config.batch_size,
                    )

                    local_w = self.model_service.get_parameters(local_model)

                    # Apply DP if enabled
                    if enable_dp:
                        local_w = privacy_service.clip_model_update(
                            global_weights,
                            local_w,
                            config.dp_max_grad_norm,
                        )
                        local_w = privacy_service.add_noise_to_weights(
                            local_w,
                            config.dp_epsilon,
                            config.dp_delta,
                            config.dp_max_grad_norm,
                            rng=rng,
                        )
                        budget.spend(config.dp_epsilon)

                    client_weights.append(local_w)
                    client_samples.append(len(data["X_train"]))
                    per_bank_loss[bank.id] = loss_hist[-1] if loss_hist else 0.0

                    # Free memory immediately
                    del local_model
                    import gc

                    gc.collect()

                # Apply secure aggregation masks
                if enable_sa and len(client_weights) > 1:
                    client_weights = self.fl_engine.apply_secure_aggregation_masks(
                        client_weights,
                        rng=rng,
                    )

                # Aggregate
                agg_start = time.perf_counter()
                global_weights = self.fl_engine.aggregate_parameters(
                    client_weights,
                    client_samples,
                    method=AggregationMethod.FED_AVG_WEIGHTED,
                )
                agg_time = (time.perf_counter() - agg_start) * 1000

                # Update global model
                global_model = self.model_service.set_parameters(global_model, global_weights)

                # Evaluate global model for this round's loss
                # Use the first participating bank's test set as a proxy
                first_bank_data = bank_data[participating[0].id]
                round_eval = self.model_service.evaluate(
                    global_model,
                    first_bank_data["X_test"],
                    first_bank_data["y_test"],
                )
                round_loss = round_eval["loss"]

                round_duration = (time.perf_counter() - round_start) * 1000

                training_round = TrainingRound(
                    round_number=round_num,
                    simulation_id=simulation.id,
                    participating_bank_ids=[b.id for b in participating],
                    dropped_bank_ids=dropped_this_round,
                    global_loss=cast("float", round_loss),
                    per_bank_loss=per_bank_loss,
                    per_bank_samples={b.id: len(bank_data[b.id]["X_train"]) for b in participating},
                    aggregation_time_ms=agg_time,
                    round_duration_ms=round_duration,
                )
                rounds.append(training_round)

                logger.info(
                    "Round %d/%d — loss: %.4f, participants: %d, dropped: %d, duration: %.0fms",
                    round_num,
                    config.num_rounds,
                    round_loss,
                    len(participating),
                    len(dropped_this_round),
                    round_duration,
                )

                self._notify(
                    progress_callback,
                    simulation.id,
                    "round_complete",
                    {
                        "round": round_num,
                        "total": config.num_rounds,
                        "loss": round_loss,
                        "participants": [b.id for b in participating],
                        "dropped": dropped_this_round,
                        "duration_ms": round_duration,
                        "privacy_budget": budget.total_epsilon if enable_dp else 0.0,
                    },
                )

            # Phase 4: Evaluate federated model at each bank
            simulation.status = SimulationStatus.EVALUATING
            self._notify(
                progress_callback,
                simulation.id,
                "status",
                {
                    "status": simulation.status,
                    "message": "Evaluating federated model",
                },
            )

            for bank in banks:
                data = bank_data[bank.id]
                fed_eval = self.model_service.evaluate(
                    global_model,
                    data["X_test"],
                    data["y_test"],
                )
                fed_feat_imp = self.model_service.get_feature_importance(global_model)
                bank.federated_metrics = self.metrics_service.from_eval_dict(
                    fed_eval,
                    fed_feat_imp,
                )

                logger.info(
                    "Federated model at %s — F1: %.4f (local: %.4f), AUC: %.4f (local: %.4f)",
                    bank.name,
                    bank.federated_metrics.f1_score,
                    bank.local_metrics.f1_score if bank.local_metrics else 0,
                    bank.federated_metrics.auc_roc,
                    bank.local_metrics.auc_roc if bank.local_metrics else 0,
                )

            # Finalize
            simulation.status = SimulationStatus.COMPLETED
            simulation.completed_at = _now()

            self._notify(
                progress_callback,
                simulation.id,
                "completed",
                {
                    "duration_seconds": simulation.duration_seconds,
                    "banks": [
                        {
                            "id": b.id,
                            "name": b.name,
                            "improvement": b.improvement,
                        }
                        for b in banks
                    ],
                },
            )

            return simulation

        except Exception as e:
            simulation.status = SimulationStatus.FAILED
            simulation.error_message = str(e)
            simulation.completed_at = _now()
            logger.exception("Simulation %s failed: %s", simulation.id, e)

            self._notify(
                progress_callback,
                simulation.id,
                "error",
                {
                    "error": str(e),
                },
            )

            return simulation

    @staticmethod
    def _notify(
        callback: ProgressCallback,
        simulation_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Send progress notification if callback is registered."""
        if callback:
            try:
                callback(simulation_id, event_type, data)
            except Exception:
                logger.warning("Progress callback failed", exc_info=True)


def _now() -> datetime:
    """Get current UTC time."""
    return datetime.now(UTC)
