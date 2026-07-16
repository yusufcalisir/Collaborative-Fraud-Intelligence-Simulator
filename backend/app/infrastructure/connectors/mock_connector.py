"""In-memory Mock Bank Connector implementing the connector port."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sklearn.model_selection import train_test_split

from app.application.interfaces.bank_connector import BankConnectorInterface
from app.application.services.data_generator import DataGenerator

if TYPE_CHECKING:
    from app.domain.value_objects import ModelWeights

logger = logging.getLogger(__name__)


class MockBankConnector(BankConnectorInterface):
    """Simulates a bank client in-process using local service layers."""

    def __init__(self, model_service: Any, data_generator: DataGenerator) -> None:
        self.model_service = model_service
        self.data_generator = data_generator
        self.X_train: Any = None
        self.y_train: Any = None
        self.X_test: Any = None
        self.y_test: Any = None

    def initialize(
        self,
        bank_id: str,
        num_transactions: int,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Generate local mock data partition and save in-memory."""
        try:
            sizes = {"bank_a": 5000, "bank_b": 3000, "bank_c": 2000}
            sizes[bank_id] = num_transactions

            datasets = self.data_generator.generate_bank_datasets(
                bank_a_size=sizes["bank_a"],
                bank_b_size=sizes["bank_b"],
                bank_c_size=sizes["bank_c"],
            )
            df, labels = datasets[bank_id]
            X = DataGenerator.encode_features(df)
            y = labels.values

            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X,
                    y,
                    test_size=0.2,
                    random_state=42,
                    stratify=y,
                )
            except Exception:
                X_train, X_test, y_train, y_test = train_test_split(
                    X,
                    y,
                    test_size=0.2,
                    random_state=42,
                )

            self.X_train = X_train
            self.y_train = y_train
            self.X_test = X_test
            self.y_test = y_test

            return {
                "status": "initialized",
                "bank_id": bank_id,
                "train_samples": len(X_train),
                "test_samples": len(X_test),
            }
        except Exception as exc:
            logger.error("Mock initialization failed for %s: %s", bank_id, exc)
            return {"status": "failed", "error": str(exc)}

    def train(
        self,
        bank_id: str,
        weights: ModelWeights,
        learning_rate: float,
        batch_size: int,
        epochs: int,
        enable_dp: bool,
        dp_epsilon: float,
        dp_delta: float,
        dp_max_grad_norm: float,
        correlation_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Perform in-memory training of model."""
        try:
            if self.X_train is None or self.y_train is None:
                raise ValueError("Dataset not initialized. Call initialize first.")

            model = self.model_service.create_model(dp_compatible=enable_dp)
            model = self.model_service.set_parameters(model, weights)

            fedprox_mu = kwargs.get("fedprox_mu", 0.0)
            moon_mu = kwargs.get("moon_mu", 0.0)
            moon_temperature = kwargs.get("moon_temperature", 0.5)
            prev_local_weights = kwargs.get("prev_local_weights")

            actual_eps = None
            if enable_dp:
                trained_model, loss_hist, actual_eps = self.model_service.train_local_with_opacus(
                    model,
                    self.X_train,
                    self.y_train,
                    target_epsilon=dp_epsilon,
                    target_delta=dp_delta,
                    max_grad_norm=dp_max_grad_norm,
                    epochs=epochs,
                    learning_rate=learning_rate,
                    batch_size=batch_size,
                    fedprox_mu=fedprox_mu,
                    moon_mu=moon_mu,
                    moon_temperature=moon_temperature,
                    global_weights=weights,
                    prev_local_weights=prev_local_weights,
                )
            else:
                trained_model, loss_hist = self.model_service.train_local(
                    model,
                    self.X_train,
                    self.y_train,
                    epochs=epochs,
                    learning_rate=learning_rate,
                    batch_size=batch_size,
                    fedprox_mu=fedprox_mu,
                    moon_mu=moon_mu,
                    moon_temperature=moon_temperature,
                    global_weights=weights,
                    prev_local_weights=prev_local_weights,
                )

            output_weights = self.model_service.get_parameters(trained_model)
            final_loss = loss_hist[-1] if loss_hist else 0.0

            return {
                "weights": {
                    "layer_shapes": [list(shape) for shape in output_weights.layer_shapes],
                    "flat_weights": output_weights.flat_weights,
                },
                "num_samples": len(self.X_train),
                "loss": float(final_loss),
                "actual_epsilon": float(actual_eps) if actual_eps is not None else None,
                "correlation_id": correlation_id,
            }
        except Exception as exc:
            logger.error("Mock training failed for %s: %s", bank_id, exc)
            return {"error": str(exc), "correlation_id": correlation_id}

    def evaluate(
        self,
        bank_id: str,
        weights: ModelWeights,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Perform in-memory model evaluation."""
        try:
            if self.X_test is None or self.y_test is None:
                raise ValueError("Dataset not initialized. Call initialize first.")

            model = self.model_service.create_model(dp_compatible=False)
            model = self.model_service.set_parameters(model, weights)

            eval_res = self.model_service.evaluate(
                model,
                self.X_test,
                self.y_test,
            )

            return {
                "loss": eval_res["loss"],
                "num_samples": len(self.X_test),
                "accuracy": eval_res["accuracy"],
                "precision": eval_res["precision"],
                "recall": eval_res["recall"],
                "f1_score": eval_res["f1_score"],
                "auc_roc": eval_res["auc_roc"],
                "confusion_matrix": eval_res["confusion_matrix"],
                "roc_fpr": eval_res["roc_fpr"],
                "roc_tpr": eval_res["roc_tpr"],
                "roc_thresholds": eval_res["roc_thresholds"],
                "correlation_id": correlation_id,
            }
        except Exception as exc:
            logger.error("Mock evaluation failed for %s: %s", bank_id, exc)
            return {"error": str(exc), "correlation_id": correlation_id}
