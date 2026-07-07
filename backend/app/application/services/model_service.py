"""PyTorch fraud detection model and training utilities.

Defines a simple MLP binary classifier suitable for tabular fraud data.
The model is intentionally straightforward — the point of this project
is the federated learning architecture, not model complexity.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from app.domain.value_objects import ModelWeights

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

# Number of input features after encoding
NUM_FEATURES = 10


class FraudDetectionModel(nn.Module):
    """3-layer MLP for binary fraud classification.

    Architecture: 10 → 64 → 32 → 1

    Deliberately simple to keep the focus on the FL pipeline.
    A production model would use attention, embeddings for categoricals,
    and possibly temporal features via LSTM.
    """

    def __init__(self, input_dim: int = NUM_FEATURES, dp_compatible: bool = False) -> None:
        super().__init__()
        norm1 = nn.GroupNorm(8, 64) if dp_compatible else nn.BatchNorm1d(64)
        norm2 = nn.GroupNorm(4, 32) if dp_compatible else nn.BatchNorm1d(32)
        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            norm1,
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            norm2,
            nn.Dropout(0.2),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x).squeeze(-1)


class ModelService:
    """Manages model lifecycle: creation, training, evaluation, and parameter exchange.

    This service owns the PyTorch model logic and exposes methods that the
    FL engine and simulation service call.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("ModelService using device: %s", self.device)

    def create_model(self, dp_compatible: bool = False) -> FraudDetectionModel:
        """Create a fresh model instance with random initialization."""
        model = FraudDetectionModel(input_dim=NUM_FEATURES, dp_compatible=dp_compatible)
        return model.to(self.device)

    def train_local(
        self,
        model: FraudDetectionModel,
        X_train: np.ndarray,
        y_train: np.ndarray,
        epochs: int | None = None,
        learning_rate: float | None = None,
        batch_size: int | None = None,
    ) -> tuple[FraudDetectionModel, list[float]]:
        """Train the model on a bank's local data.

        Returns the trained model and per-epoch loss history.
        """
        epochs = epochs or self.settings.fl_default_local_epochs
        learning_rate = learning_rate or self.settings.fl_default_learning_rate
        batch_size = batch_size or self.settings.fl_default_batch_size

        model.train()

        # Use standard BCE since model has sigmoid
        criterion: Any = nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        dataset = TensorDataset(
            torch.FloatTensor(X_train).to(self.device),
            torch.FloatTensor(y_train).to(self.device),
        )
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=False)

        import time

        loss_history: list[float] = []

        for epoch in range(epochs):
            epoch_loss = 0.0
            n_batches = 0

            for X_batch, y_batch in loader:
                optimizer.zero_grad()
                predictions = model(X_batch)
                loss = criterion(predictions, y_batch)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

                # Yield control to event loop/other threads to prevent GIL starvation
                time.sleep(0.005)

            avg_loss = epoch_loss / max(n_batches, 1)
            loss_history.append(avg_loss)
            logger.debug("Epoch %d/%d — loss: %.4f", epoch + 1, epochs, avg_loss)

            # Additional yield between epochs
            time.sleep(0.02)

        import gc

        gc.collect()

        return model, loss_history

    def train_local_with_opacus(
        self,
        model: FraudDetectionModel,
        X_train: np.ndarray,
        y_train: np.ndarray,
        target_epsilon: float,
        target_delta: float,
        max_grad_norm: float = 1.0,
        epochs: int | None = None,
        learning_rate: float | None = None,
        batch_size: int | None = None,
    ) -> tuple[FraudDetectionModel, list[float], float]:
        """Train the model on a bank's local data with Differential Privacy using Opacus.

        Performs per-sample gradient clipping and noise injection during training.
        Returns the trained model, loss history, and actual epsilon spent.
        """
        from opacus import PrivacyEngine

        epochs = epochs or self.settings.fl_default_local_epochs
        learning_rate = learning_rate or self.settings.fl_default_learning_rate
        batch_size = batch_size or self.settings.fl_default_batch_size

        model.train()

        criterion: Any = nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        dataset = TensorDataset(
            torch.FloatTensor(X_train).to(self.device),
            torch.FloatTensor(y_train).to(self.device),
        )
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=False)

        privacy_engine = PrivacyEngine()

        # Cast to Any to prevent IDE type checker errors caused by Opacus overloading definitions
        res: Any = privacy_engine.make_private_with_epsilon(
            module=model,
            optimizer=optimizer,
            data_loader=loader,
            target_epsilon=target_epsilon,
            target_delta=target_delta,
            epochs=epochs,
            max_grad_norm=max_grad_norm,
        )
        model_private: Any = res[0]
        optimizer_private: Any = res[1]
        loader_private: Any = res[2]

        import time

        loss_history: list[float] = []

        for epoch in range(epochs):
            epoch_loss = 0.0
            n_batches = 0

            for X_batch, y_batch in loader_private:
                optimizer_private.zero_grad()
                predictions = model_private(X_batch)
                loss = criterion(predictions, y_batch)
                loss.backward()
                optimizer_private.step()

                epoch_loss += loss.item()
                n_batches += 1

                # Yield control to prevent GIL starvation
                time.sleep(0.005)

            avg_loss = epoch_loss / max(n_batches, 1)
            loss_history.append(avg_loss)
            logger.debug("Opacus Epoch %d/%d — loss: %.4f", epoch + 1, epochs, avg_loss)

            time.sleep(0.02)

        actual_epsilon = privacy_engine.get_epsilon(delta=target_delta)

        # De-wrap the module before returning it
        model_final = cast("FraudDetectionModel", model_private._module)

        import gc

        gc.collect()

        return model_final, loss_history, actual_epsilon

    def evaluate(
        self,
        model: FraudDetectionModel,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> dict[str, float | list]:
        """Evaluate model on test data.

        Returns a dict with accuracy, precision, recall, f1, auc_roc, loss,
        confusion_matrix, roc_fpr, roc_tpr, roc_thresholds.
        """
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
            roc_curve,
        )

        model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_test).to(self.device)
            y_tensor = torch.FloatTensor(y_test).to(self.device)
            probs = model(X_tensor).cpu().numpy()
            loss_tensor = nn.BCELoss()(
                torch.FloatTensor(probs).to(self.device),
                y_tensor,
            )
            loss = loss_tensor.item()
            del X_tensor, y_tensor, loss_tensor
            import gc

            gc.collect()

        preds = (probs >= 0.5).astype(int)

        # Handle edge case where test set has only one class
        try:
            auc = roc_auc_score(y_test, probs)
            fpr, tpr, thresholds = roc_curve(y_test, probs)
        except ValueError:
            auc = 0.0
            fpr = np.array([0.0, 1.0])
            tpr = np.array([0.0, 1.0])
            thresholds = np.array([1.0, 0.0])

        cm = confusion_matrix(y_test, preds, labels=[0, 1])

        return {
            "accuracy": float(accuracy_score(y_test, preds)),
            "precision": float(precision_score(y_test, preds, zero_division=0)),
            "recall": float(recall_score(y_test, preds, zero_division=0)),
            "f1_score": float(f1_score(y_test, preds, zero_division=0)),
            "auc_roc": float(auc),
            "loss": float(loss),
            "confusion_matrix": cm.tolist(),
            "roc_fpr": fpr.tolist(),
            "roc_tpr": tpr.tolist(),
            "roc_thresholds": thresholds.tolist(),
        }

    def get_parameters(self, model: FraudDetectionModel) -> ModelWeights:
        """Extract model parameters as a serializable ModelWeights object."""
        shapes = []
        flat: list[float] = []

        for param in model.parameters():
            shapes.append(tuple(param.shape))
            flat.extend(param.data.cpu().numpy().flatten().tolist())

        return ModelWeights(layer_shapes=shapes, flat_weights=flat)

    def set_parameters(
        self,
        model: FraudDetectionModel,
        weights: ModelWeights,
    ) -> FraudDetectionModel:
        """Load parameters from a ModelWeights object into the model."""
        offset = 0
        for param, shape in zip(model.parameters(), weights.layer_shapes, strict=False):
            numel = 1
            for s in shape:
                numel *= s
            param_data = weights.flat_weights[offset : offset + numel]
            param.data = torch.FloatTensor(param_data).reshape(shape).to(self.device)
            offset += numel

        return model

    def compute_integrated_gradients(
        self,
        model: FraudDetectionModel,
        input_tensor: torch.Tensor,
        baseline_tensor: torch.Tensor | None = None,
        steps: int = 50,
    ) -> np.ndarray:
        """Compute Integrated Gradients attribution for a given input tensor.

        Args:
            model: The trained FraudDetectionModel.
            input_tensor: Shape (N, 10) representing the input features.
            baseline_tensor: Optional shape (10,) or (N, 10) representing the baseline.
                             Defaults to all zeros if None.
            steps: Number of integration steps.

        Returns:
            np.ndarray of shape (N, 10) representing feature attributions.
        """
        model.eval()
        if baseline_tensor is None:
            baseline_tensor = torch.zeros_like(input_tensor)

        # Scale inputs from baseline to input
        scaled_inputs = []
        for i in range(steps + 1):
            alpha = i / steps
            scaled_inputs.append(baseline_tensor + alpha * (input_tensor - baseline_tensor))

        # Stack scaled inputs to process as a single batch
        scaled_inputs_batch = torch.cat(scaled_inputs, dim=0).requires_grad_(True).to(self.device)

        # Forward pass
        predictions = model(scaled_inputs_batch)

        # Backward pass to get gradients
        gradients = torch.autograd.grad(
            outputs=predictions,
            inputs=scaled_inputs_batch,
            grad_outputs=torch.ones_like(predictions),
            create_graph=False,
            retain_graph=False,
        )[0]

        # Average the gradients across steps
        gradients = gradients.reshape(steps + 1, input_tensor.shape[0], input_tensor.shape[1])
        avg_gradients = gradients.mean(dim=0)  # Shape (N, 10)

        # IG = (input - baseline) * avg_gradients
        delta = input_tensor.to(self.device) - baseline_tensor.to(self.device)
        attributions = delta * avg_gradients

        return attributions.detach().cpu().numpy()

    def get_feature_importance(
        self, model: FraudDetectionModel, X_ref: np.ndarray | None = None
    ) -> dict[str, float]:
        """Extract feature importance from the first layer weights.

        Uses absolute weight magnitude as a proxy for importance.
        This is a rough heuristic — not as rigorous as SHAP or permutation
        importance, but sufficient for visualization purposes.
        """
        from app.application.services.data_generator import FEATURE_NAMES

        if X_ref is None or len(X_ref) == 0:
            first_layer = list(model.parameters())[0]  # Shape: [64, 10]
            importance = first_layer.abs().mean(dim=0).detach().cpu().numpy()
        else:
            # Calculate Integrated Gradients on reference data
            ref_size = min(100, len(X_ref))
            input_tensor = torch.FloatTensor(X_ref[:ref_size]).to(self.device)
            attributions = self.compute_integrated_gradients(model, input_tensor)
            importance = np.mean(np.abs(attributions), axis=0)

        # Normalize to [0, 1]
        max_imp = importance.max()
        if max_imp > 0:
            importance = importance / max_imp

        return {name: float(imp) for name, imp in zip(FEATURE_NAMES, importance, strict=False)}
