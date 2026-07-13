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
itself is stateless â€” all state is either passed in or persisted to
the database.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import torch
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
from app.domain.value_objects import ModelWeights

if TYPE_CHECKING:
    from app.application.services.fl_engine import FederatedLearningEngine
    from app.application.services.metrics_service import MetricsService
    from app.application.services.model_service import ModelService
    from app.config import Settings
    from app.domain.value_objects import SimulationConfig

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
        from app.application.services.model_registry import ModelRegistry

        self.model_registry = ModelRegistry()

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
        from app.infrastructure.telemetry import (
            active_simulations,
            simulation_duration_seconds,
            simulation_rounds_total,
        )

        simulation = SimulationRun(config=config, total_rounds=config.num_rounds)
        simulation.started_at = _now()
        rng = np.random.default_rng(42)
        active_simulations.add(1)

        # Initialize MLflow experiment run
        mlflow_run = self._init_mlflow(simulation.id, config)

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

            # Scale down datasets for optimal CPU training on
            # Hugging Face Spaces environment (16 GB RAM, 2 vCPUs).
            # 50,000 â†’ 5,000, 30,000 â†’ 3,000, 20,000 â†’ 2,000 transactions
            datasets = self.data_generator.generate_bank_datasets(
                bank_a_size=max(500, config.bank_a_transactions // 10),
                bank_b_size=max(500, config.bank_b_transactions // 10),
                bank_c_size=max(500, config.bank_c_transactions // 10),
            )
            profiles = self.data_generator.create_bank_profiles(datasets)
            banks = self.data_generator.create_bank_entities(datasets, profiles)
            simulation.banks = banks

            # Notify progress callback of the generated banks early
            self._notify(
                progress_callback,
                simulation.id,
                "banks_generated",
                {
                    "banks": [
                        {
                            "id": b.id,
                            "name": b.name,
                            "tier": b.tier.value,
                            "fraud_ratio": b.fraud_ratio,
                            "num_transactions": b.num_transactions,
                            "status": b.status.value,
                        }
                        for b in banks
                    ]
                },
            )

            # Split into train/test per bank
            bank_data: dict[str, dict[str, np.ndarray]] = {}
            for bank_id, (df, labels) in datasets.items():
                X = DataGenerator.encode_features(df)
                y = labels.values

                # Stratified split preferred, but fall back to random split
                # when a class has < 2 members (tiny datasets).
                try:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X,
                        y,
                        test_size=0.2,
                        random_state=42,
                        stratify=cast("Any", y),
                    )
                except ValueError:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X,
                        y,
                        test_size=0.2,
                        random_state=42,
                    )

                bank_data[bank_id] = {
                    "X_train": X_train,
                    "X_test": X_test,
                    "y_train": y_train,
                    "y_test": y_test,
                }

            # Create a global validation/test set by concatenating all bank test sets
            X_val_global = np.concatenate([data["X_test"] for data in bank_data.values()], axis=0)
            y_val_global = np.concatenate([data["y_test"] for data in bank_data.values()], axis=0)

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
                    "Local model for %s â€” F1: %.4f, AUC: %.4f",
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
            dp_mode = getattr(config, "dp_mode", "post_hoc")
            use_opacus_dp = enable_dp and dp_mode == "opacus"

            global_model = self.model_service.create_model(dp_compatible=use_opacus_dp)
            global_weights = self.model_service.get_parameters(global_model)
            privacy_service = PrivacyService()

            fl_engine_type = getattr(config, "fl_engine_type", "custom")

            rounds: list[TrainingRound] = []
            dropped_banks: set[str] = set()
            client_weights: list[ModelWeights] = []
            client_samples: list[int] = []
            per_bank_loss: dict[str, float] = {}

            if fl_engine_type == "flower":
                # â”€â”€ Flower Framework Branch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                from app.application.services.flower_engine import FlowerFLEngine

                flower_engine = FlowerFLEngine(self.model_service)
                self._notify(
                    progress_callback,
                    simulation.id,
                    "status",
                    {
                        "status": simulation.status,
                        "message": "Running Flower FL simulation",
                    },
                )

                def flower_progress_cb(sim_id: str, event_type: str, data: dict[str, Any]) -> None:
                    self._notify(progress_callback, sim_id, event_type, data)

                flower_result = flower_engine.run_federated_training(
                    config=config,
                    bank_data=bank_data,
                    global_model=global_model,
                    progress_callback=flower_progress_cb if progress_callback else None,
                    simulation_id=simulation.id,
                )

                rounds = [
                    TrainingRound(
                        round_number=r["round_number"],
                        simulation_id=simulation.id,
                        participating_bank_ids=r["participating_bank_ids"],
                        dropped_bank_ids=r["dropped_bank_ids"],
                        global_loss=r["global_loss"],
                        per_bank_loss=r.get("per_bank_loss", {}),
                        per_bank_samples=r.get("per_bank_samples", {}),
                        aggregation_time_ms=r.get("aggregation_time_ms", 0.0),
                        round_duration_ms=r.get("round_duration_ms", 0.0),
                    )
                    for r in flower_result.get("rounds", [])
                ]

            else:
                # â”€â”€ Bank Connector-driven Engine Branch (distributed, event-driven, or custom/in-memory) â”€â”€
                from app.infrastructure.connectors.factory import BankConnectorFactory

                bank_connectors = {}
                for bank in banks:
                    conn_type = getattr(
                        self.settings, f"{bank.id.replace('-', '_')}_connector_type", None
                    )
                    if conn_type == "mock" or not conn_type:
                        if fl_engine_type == "distributed":
                            conn_type = "rest"
                        elif fl_engine_type == "event_driven":
                            conn_type = "redis"
                        else:
                            conn_type = "mock"

                    local_settings = self.settings.model_copy()
                    setattr(
                        local_settings, f"{bank.id.replace('-', '_')}_connector_type", conn_type
                    )

                    connector = BankConnectorFactory.get_connector(
                        bank_id=bank.id,
                        settings=local_settings,
                        model_service=self.model_service,
                        data_generator=self.data_generator,
                    )
                    bank_connectors[bank.id] = connector

                # Trigger dataset initialization on all connectors
                simulation.status = SimulationStatus.INITIALIZING_CLIENTS
                self._notify(
                    progress_callback,
                    simulation.id,
                    "status",
                    {
                        "status": simulation.status,
                        "message": "Initializing bank client datasets via Bank Connectors",
                    },
                )
                for bank in banks:
                    num_txns = max(
                        500,
                        getattr(config, f"{bank.id.replace('-', '_')}_transactions", 1000) // 10,
                    )
                    init_res = bank_connectors[bank.id].initialize(
                        bank.id, num_transactions=num_txns, seed=42
                    )
                    if init_res.get("status") == "failed" or "error" in init_res:
                        logger.error(
                            "Failed to initialize bank %s via connector: %s",
                            bank.id,
                            init_res.get("error"),
                        )

                dropped_banks = set()

                if enable_dp:
                    budget = privacy_service.get_or_create_budget(
                        simulation.id,
                        config.dp_epsilon,
                        config.dp_delta,
                    )

                rounds = []

                for round_num in range(1, config.num_rounds + 1):
                    round_start = time.perf_counter()
                    simulation.current_round = round_num
                    logger.info("Starting Federated Round %d/%d", round_num, config.num_rounds)

                    self._notify(
                        progress_callback,
                        simulation.id,
                        "round_start",
                        {
                            "round": round_num,
                            "total": config.num_rounds,
                        },
                    )

                    # Determine client availability using FL engine
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

                    # Local training at each participating bank client via resolved connectors
                    client_weights = []
                    client_samples = []
                    per_bank_loss = {}
                    per_bank_samples = {}

                    for bank in participating:
                        correlation_id = f"train_{simulation.id}_{round_num}_{bank.id}"
                        logger.info("Triggering training for %s via connector", bank.id)
                        connector = bank_connectors[bank.id]

                        train_res = connector.train(
                            bank_id=bank.id,
                            weights=global_weights,
                            learning_rate=config.learning_rate,
                            batch_size=config.batch_size,
                            epochs=config.local_epochs,
                            enable_dp=enable_dp,
                            dp_epsilon=config.dp_epsilon,
                            dp_delta=config.dp_delta,
                            dp_max_grad_norm=config.dp_max_grad_norm,
                            correlation_id=correlation_id,
                        )

                        if "error" in train_res:
                            logger.error(
                                "Training failed for bank %s: %s", bank.id, train_res["error"]
                            )
                            continue

                        # Extract result weights
                        res_shapes = [
                            tuple(shape) for shape in train_res["weights"]["layer_shapes"]
                        ]
                        res_w = ModelWeights(
                            layer_shapes=res_shapes,
                            flat_weights=train_res["weights"]["flat_weights"],
                        )

                        # Apply model poisoning if this bank is the attacker
                        if (
                            config.enable_poisoning_simulation
                            and bank.id == config.poisoning_bank_id
                        ):
                            res_w = self.fl_engine.apply_model_poisoning(
                                res_w,
                                scale=config.poisoning_scale,
                                rng=rng,
                            )
                            logger.warning(
                                "Round %d: Bank %s weights POISONED in custom connector mode",
                                round_num,
                                bank.name,
                            )

                        # Apply post-hoc DP if enabled and not using Opacus
                        if enable_dp and dp_mode != "opacus":
                            res_w = privacy_service.clip_model_update(
                                global_weights,
                                res_w,
                                config.dp_max_grad_norm,
                            )
                            res_w = privacy_service.add_noise_to_weights(
                                res_w,
                                config.dp_epsilon,
                                config.dp_delta,
                                config.dp_max_grad_norm,
                                rng=rng,
                            )
                            budget.spend(config.dp_epsilon)

                        if train_res.get("actual_epsilon"):
                            privacy_service.record_opacus_epsilon(
                                simulation.id, train_res["actual_epsilon"]
                            )

                        client_weights.append(res_w)
                        client_samples.append(train_res["num_samples"])
                        per_bank_loss[bank.id] = train_res["loss"]
                        per_bank_samples[bank.id] = train_res["num_samples"]

                    # Apply secure aggregation masks
                    if enable_sa and len(client_weights) > 1:
                        client_weights = self.fl_engine.apply_secure_aggregation_masks(
                            client_weights,
                            client_samples=client_samples,
                            rng=rng,
                        )

                    # Check for Byzantine/Malicious clients & defense mechanism
                    if len(client_weights) > 0:
                        is_malicious = [
                            config.enable_poisoning_simulation and b.id == config.poisoning_bank_id
                            for b in participating
                        ]
                        agg_start = time.perf_counter()

                        # If poisoning is detected/defended, filter weights
                        if (
                            config.enable_poisoning_simulation
                            and config.byzantine_defense != "none"
                        ):
                            client_weights = self.fl_engine.apply_byzantine_defense(
                                client_weights,
                                defense_type=config.byzantine_defense,
                            )
                            logger.info(
                                "Round %d: Byzantine defense (%s) applied",
                                round_num,
                                config.byzantine_defense,
                            )

                        # Perform aggregation (FedAvg/Weighted/etc.)
                        agg_method = AggregationMethod(config.aggregation_method)
                        global_weights = self.fl_engine.aggregate_parameters(
                            client_weights,
                            client_samples=client_samples,
                            method=agg_method,
                        )
                        agg_time = (time.perf_counter() - agg_start) * 1000
                    else:
                        agg_time = 0.0

                    # Load aggregated weights into global structure
                    global_model = self.model_service.set_parameters(global_model, global_weights)

                    # Evaluate global model on participating client nodes test partitions
                    eval_losses = []
                    for bank in participating:
                        correlation_id = f"evaluate_{simulation.id}_{round_num}_{bank.id}"
                        connector = bank_connectors[bank.id]
                        try:
                            eval_res = connector.evaluate(
                                bank_id=bank.id,
                                weights=global_weights,
                                correlation_id=correlation_id,
                            )
                            if "error" not in eval_res:
                                eval_losses.append(eval_res["loss"])
                        except Exception as exc:
                            logger.error("Evaluation failed for bank %s: %s", bank.id, exc)

                    round_loss = sum(eval_losses) / len(eval_losses) if eval_losses else 0.0

                    # Simulate differential privacy canary validation checks if enabled
                    canary_info: dict[str, Any] = {}

                    # Calculate feature importance
                    ref_X = bank_data[participating[0].id]["X_train"]
                    round_feature_importance = self.model_service.get_feature_importance(
                        global_model, ref_X
                    )

                    round_duration = (time.perf_counter() - round_start) * 1000

                    training_round = TrainingRound(
                        round_number=round_num,
                        simulation_id=simulation.id,
                        participating_bank_ids=[b.id for b in participating],
                        dropped_bank_ids=dropped_this_round,
                        global_loss=round_loss,
                        per_bank_loss=per_bank_loss,
                        per_bank_samples=per_bank_samples,
                        aggregation_time_ms=agg_time,
                        round_duration_ms=round_duration,
                        canary_info=canary_info,
                    )
                    rounds.append(training_round)
                    simulation.rounds_run = round_num
                    simulation.rounds = rounds

                    logger.info(
                        "[Federated FL] Round %d/%d — loss: %.4f, participants: %d, dropped: %d, duration: %.0fms",
                        round_num,
                        config.num_rounds,
                        round_loss,
                        len(participating),
                        len(dropped_this_round),
                        round_duration,
                    )

                    # Record OTEL metrics for this round
                    simulation_rounds_total.add(1)
                    simulation_duration_seconds.record(round_duration / 1000)

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
                            "feature_importance": round_feature_importance,
                            "canary_info": canary_info,
                        },
                    )

                    # Log metrics for this round to MLflow
                    self._log_mlflow_round(
                        mlflow_run,
                        round_num=round_num,
                        round_loss=round_loss,
                        active_participants=len(participating),
                        privacy_budget=budget.total_epsilon if enable_dp else 0.0,
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
                if fl_engine_type == "flower":
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
                else:
                    correlation_id = f"evaluate_final_{simulation.id}_{bank.id}"
                    try:
                        connector = bank_connectors[bank.id]
                        eval_res = connector.evaluate(
                            bank_id=bank.id,
                            weights=global_weights,
                            correlation_id=correlation_id,
                        )
                        if "error" in eval_res:
                            raise RuntimeError(eval_res["error"])

                        fed_feat_imp = self.model_service.get_feature_importance(
                            global_model, X_val_global
                        )
                        bank.federated_metrics = self.metrics_service.from_eval_dict(
                            eval_res,
                            fed_feat_imp,
                        )
                    except Exception as exc:
                        logger.error(
                            "Connector evaluation fallback locally for bank %s: %s",
                            bank.id,
                            exc,
                        )
                        # Fallback: evaluate locally using the bank's test data
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
            active_simulations.add(-1)
            simulation.status = SimulationStatus.COMPLETED
            simulation.completed_at = _now()

            # Save the final global model for explainability
            try:
                storage_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage"
                )
                os.makedirs(storage_dir, exist_ok=True)
                model_path = os.path.join(storage_dir, "global_model.pt")
                torch.save(global_model.state_dict(), model_path)
                logger.info("Saved global model for explainability to %s", model_path)
            except Exception as e:
                logger.warning("Failed to save global model for explainability: %s", e)

            # Log final parameters/metrics and complete MLflow run
            self._finalize_mlflow(mlflow_run, banks, "completed")

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
            active_simulations.add(-1)
            simulation.status = SimulationStatus.FAILED
            simulation.error_message = str(e)
            simulation.completed_at = _now()
            logger.exception("Simulation %s failed: %s", simulation.id, e)

            # Log final parameters/metrics and mark MLflow run as failed
            self._finalize_mlflow(
                mlflow_run if "mlflow_run" in locals() else None,
                banks if "banks" in locals() else [],
                "failed",
                error_message=str(e),
            )

            self._notify(
                progress_callback,
                simulation.id,
                "error",
                {
                    "error": str(e),
                },
            )

            return simulation

    def _init_mlflow(self, simulation_id: str, config: Any) -> Any:
        """Initialize MLflow run and log parameters."""
        if not self.settings.mlflow_enabled:
            return None

        try:
            # Opt out of MLflow 3.0's filestore deprecation error to allow local tracking
            import os as python_os

            import mlflow

            python_os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

            if self.settings.mlflow_tracking_uri:
                mlflow.set_tracking_uri(self.settings.mlflow_tracking_uri)
            mlflow.set_experiment(self.settings.mlflow_experiment_name)

            run = mlflow.start_run(run_name=f"sim-{simulation_id[:8]}")

            # Log params
            mlflow.log_params(
                {
                    "simulation_id": simulation_id,
                    "num_rounds": config.num_rounds,
                    "local_epochs": config.local_epochs,
                    "learning_rate": config.learning_rate,
                    "batch_size": config.batch_size,
                    "min_clients_per_round": config.min_clients_per_round,
                    "aggregation_method": getattr(config, "aggregation_method", "fed_avg_weighted"),
                    "enable_differential_privacy": getattr(
                        config, "enable_differential_privacy", False
                    ),
                    "dp_epsilon": getattr(config, "dp_epsilon", 0.0),
                    "dp_delta": getattr(config, "dp_delta", 0.0),
                    "enable_secure_aggregation": getattr(
                        config, "enable_secure_aggregation", False
                    ),
                    "enable_poisoning_simulation": getattr(
                        config, "enable_poisoning_simulation", False
                    ),
                }
            )
            return run
        except Exception as e:
            logger.warning("Failed to initialize MLflow tracking: %s", e)
            return None

    def _log_mlflow_round(
        self,
        run: Any,
        round_num: int,
        round_loss: float,
        active_participants: int,
        privacy_budget: float,
    ) -> None:
        """Log round metrics to MLflow."""
        if not run:
            return
        try:
            import mlflow

            mlflow.log_metrics(
                {
                    "round_global_loss": round_loss,
                    "active_participants": active_participants,
                    "privacy_budget_spent": privacy_budget,
                },
                step=round_num,
            )
        except Exception as e:
            logger.warning("Failed to log round metrics to MLflow: %s", e)

    def _finalize_mlflow(
        self, run: Any, banks: list[Any], status: str, error_message: str | None = None
    ) -> None:
        """Log final metrics and close MLflow run."""
        if not run:
            return
        try:
            import mlflow

            # Log final status
            mlflow.set_tag("simulation_status", status)
            if error_message:
                mlflow.set_tag("error", error_message)

            # Log average metrics across all banks
            valid_banks = [b for b in banks if getattr(b, "federated_metrics", None) is not None]
            if valid_banks:
                avg_accuracy = sum(b.federated_metrics.accuracy for b in valid_banks) / len(
                    valid_banks
                )
                avg_precision = sum(b.federated_metrics.precision for b in valid_banks) / len(
                    valid_banks
                )
                avg_recall = sum(b.federated_metrics.recall for b in valid_banks) / len(valid_banks)
                avg_f1_score = sum(b.federated_metrics.f1_score for b in valid_banks) / len(
                    valid_banks
                )
                avg_auc_roc = sum(b.federated_metrics.auc_roc for b in valid_banks) / len(
                    valid_banks
                )

                mlflow.log_metrics(
                    {
                        "final_avg_accuracy": avg_accuracy,
                        "final_avg_precision": avg_precision,
                        "final_avg_recall": avg_recall,
                        "final_avg_f1_score": avg_f1_score,
                        "final_avg_auc_roc": avg_auc_roc,
                    }
                )

                # Log metrics per bank
                for b in valid_banks:
                    mlflow.log_metrics(
                        {
                            f"{b.id}_accuracy": b.federated_metrics.accuracy,
                            f"{b.id}_precision": b.federated_metrics.precision,
                            f"{b.id}_recall": b.federated_metrics.recall,
                            f"{b.id}_f1_score": b.federated_metrics.f1_score,
                            f"{b.id}_auc_roc": b.federated_metrics.auc_roc,
                        }
                    )

            mlflow.end_run()
        except Exception as e:
            logger.warning("Failed to finalize MLflow run: %s", e)

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
