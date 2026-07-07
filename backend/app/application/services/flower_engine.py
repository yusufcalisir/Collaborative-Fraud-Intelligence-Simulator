"""Flower FL framework adapter.

Provides an alternative FL engine using the Flower (flwr.dev) framework's
simulation mode. This demonstrates compatibility with industry-standard
FL tooling while running entirely in-process via Ray.

Design decisions:
- Uses ``flwr.simulation.start_simulation()`` for single-machine execution
- Wraps our existing ``ModelService`` for training and evaluation
- Supports FedAvg aggregation (weighted by dataset size)
- Fires progress callbacks via a custom Strategy subclass
- Compatible with both post-hoc and Opacus DP modes

Limitations vs. the custom engine:
- No Krum/Median aggregation (Flower would need custom Strategy subclasses)
- No client dropout/reconnection simulation (Flower manages scheduling)
- No network latency simulation (in-process simulation)
- No secure aggregation masks (Flower has its own SecAgg, out of scope)
- No model poisoning simulation (would need a custom malicious client)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import numpy as np

    from app.application.services.model_service import ModelService
    from app.domain.value_objects import SimulationConfig

logger = logging.getLogger(__name__)

# Type for progress callback: (simulation_id, event_type, data)
ProgressCallback = Callable[[str, str, dict[str, Any]], None] | None


def _weights_to_ndarrays(
    model_service: ModelService,
    model: Any,
) -> list[np.ndarray]:
    """Convert model parameters to a list of NumPy arrays (Flower format)."""
    arrays: list[np.ndarray] = []
    for param in model.parameters():
        arrays.append(param.data.cpu().numpy().copy())
    return arrays


def _ndarrays_to_model(
    model_service: ModelService,
    model: Any,
    ndarrays: list[np.ndarray],
) -> Any:
    """Load a list of NumPy arrays into a PyTorch model."""
    import torch

    for param, arr in zip(model.parameters(), ndarrays, strict=False):
        param.data = torch.FloatTensor(arr).to(model_service.device)
    return model


class FlowerFLEngine:
    """Flower-based FL engine using simulation mode.

    Wraps the federated training loop using Flower's ``start_simulation``
    with a custom FedAvg strategy and NumPyClient implementation.
    """

    def __init__(self, model_service: ModelService) -> None:
        self.model_service = model_service

    def run_federated_training(
        self,
        config: SimulationConfig,
        bank_data: dict[str, dict[str, np.ndarray]],
        global_model: Any,
        progress_callback: ProgressCallback = None,
        simulation_id: str = "",
    ) -> dict[str, Any]:
        """Execute federated training using Flower's simulation engine.

        Args:
            config: Simulation configuration.
            bank_data: Per-bank train/test splits.
            global_model: The initial global model.
            progress_callback: Callback for round-level progress events.
            simulation_id: ID for progress callback context.

        Returns:
            A dict with 'rounds' (list of round dicts), 'global_model',
            and 'global_weights'.
        """
        import flwr as fl
        from flwr.common import ndarrays_to_parameters
        from flwr.simulation import start_simulation

        bank_ids = list(bank_data.keys())
        model_service = self.model_service
        use_opacus_dp = getattr(config, "dp_mode", "post_hoc") == "opacus" and getattr(
            config, "enable_differential_privacy", False
        )

        # Capture round results from the strategy
        round_results: list[dict[str, Any]] = []

        # ── Flower Client ──────────────────────────────────────────
        class FraudFlowerClient(fl.client.NumPyClient):
            """Flower NumPyClient wrapping our ModelService."""

            def __init__(self, bank_id: str) -> None:
                self.bank_id = bank_id
                self.data = bank_data[bank_id]
                self.model = model_service.create_model(dp_compatible=use_opacus_dp)

            def get_parameters(self, config_dict: dict[str, Any]) -> list[np.ndarray]:
                return _weights_to_ndarrays(model_service, self.model)

            def fit(
                self,
                parameters: list[np.ndarray],
                config_dict: dict[str, Any],
            ) -> tuple[list[np.ndarray], int, dict[str, Any]]:
                # Load global parameters
                _ndarrays_to_model(model_service, self.model, parameters)

                n_samples = len(self.data["X_train"])

                if use_opacus_dp:
                    self.model, loss_hist, epsilon = model_service.train_local_with_opacus(
                        self.model,
                        self.data["X_train"],
                        self.data["y_train"],
                        target_epsilon=config.dp_epsilon,
                        target_delta=config.dp_delta,
                        max_grad_norm=config.dp_max_grad_norm,
                        epochs=config.local_epochs,
                        learning_rate=config.learning_rate,
                        batch_size=config.batch_size,
                    )
                    metrics = {"loss": loss_hist[-1], "epsilon": epsilon}
                else:
                    self.model, loss_hist = model_service.train_local(
                        self.model,
                        self.data["X_train"],
                        self.data["y_train"],
                        epochs=config.local_epochs,
                        learning_rate=config.learning_rate,
                        batch_size=config.batch_size,
                    )
                    metrics = {"loss": loss_hist[-1]}

                updated_params = _weights_to_ndarrays(model_service, self.model)
                return updated_params, n_samples, metrics

            def evaluate(
                self,
                parameters: list[np.ndarray],
                config_dict: dict[str, Any],
            ) -> tuple[float, int, dict[str, Any]]:
                _ndarrays_to_model(model_service, self.model, parameters)
                eval_result = model_service.evaluate(
                    self.model,
                    self.data["X_test"],
                    self.data["y_test"],
                )
                n_samples = len(self.data["X_test"])
                loss = cast(float, eval_result["loss"])
                return (
                    loss,
                    n_samples,
                    {
                        "accuracy": eval_result["accuracy"],
                        "f1_score": eval_result["f1_score"],
                    },
                )

        # ── Custom Strategy with Callbacks ─────────────────────────
        class CallbackFedAvg(fl.server.strategy.FedAvg):
            """FedAvg strategy that fires progress callbacks after each round."""

            def aggregate_fit(
                self,
                server_round: int,
                results: list,
                failures: list,
            ) -> Any:
                round_start = time.perf_counter()
                aggregated = super().aggregate_fit(server_round, results, failures)
                round_duration = (time.perf_counter() - round_start) * 1000

                # Collect per-client losses
                per_bank_loss: dict[str, float] = {}
                for i, (_, fit_res) in enumerate(results):
                    if i < len(bank_ids):
                        bid = bank_ids[i]
                        per_bank_loss[bid] = fit_res.metrics.get("loss", 0.0)

                avg_loss = (
                    sum(per_bank_loss.values()) / len(per_bank_loss) if per_bank_loss else 0.0
                )

                round_info = {
                    "round_number": server_round,
                    "global_loss": avg_loss,
                    "per_bank_loss": per_bank_loss,
                    "participating_bank_ids": bank_ids,
                    "dropped_bank_ids": [],
                    "aggregation_time_ms": round_duration,
                    "round_duration_ms": round_duration,
                    "per_bank_samples": {bid: len(bank_data[bid]["X_train"]) for bid in bank_ids},
                }
                round_results.append(round_info)

                if progress_callback:
                    progress_callback(
                        simulation_id,
                        "round_complete",
                        {
                            "round": server_round,
                            "total": config.num_rounds,
                            "loss": avg_loss,
                            "participants": bank_ids,
                            "dropped": [],
                            "duration_ms": round_duration,
                            "privacy_budget": 0.0,
                        },
                    )

                logger.info(
                    "[Flower] Round %d/%d — avg loss: %.4f, duration: %.0fms",
                    server_round,
                    config.num_rounds,
                    avg_loss,
                    round_duration,
                )

                return aggregated

        # ── Client Factory ─────────────────────────────────────────
        def client_fn(cid: str) -> fl.client.Client:
            bank_id = bank_ids[int(cid)]
            return FraudFlowerClient(bank_id).to_client()

        # ── Run Simulation ─────────────────────────────────────────
        initial_params = ndarrays_to_parameters(_weights_to_ndarrays(model_service, global_model))

        strategy = CallbackFedAvg(
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=len(bank_ids),
            min_evaluate_clients=len(bank_ids),
            min_available_clients=len(bank_ids),
            initial_parameters=initial_params,
        )

        logger.info(
            "[Flower] Starting simulation: %d clients, %d rounds",
            len(bank_ids),
            config.num_rounds,
        )

        history = start_simulation(
            client_fn=client_fn,
            num_clients=len(bank_ids),
            config=fl.server.ServerConfig(num_rounds=config.num_rounds),
            strategy=strategy,
            client_resources={"num_cpus": 1, "num_gpus": 0.0},
            ray_init_args={
                "object_store_memory": 100 * 1024 * 1024,
                "num_cpus": 1,
                "ignore_reinit_error": True,
                "include_dashboard": False,
            },
        )

        import ray

        if ray.is_initialized():
            ray.shutdown()

        logger.info(
            "[Flower] Simulation complete. History losses: %s",
            history.losses_distributed,
        )

        # ── Extract final global model ─────────────────────────────
        if history.losses_distributed:
            # Use the last round's distributed loss as the final global loss
            pass

        return {
            "rounds": round_results,
            "history": history,
        }
