import os
import sys

# Force CPU execution to prevent PyTorch from hanging during CUDA driver initialization
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import time

import matplotlib.pyplot as plt
import numpy as np

# Add backend root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, "..")))

from app.application.services.data_generator import DataGenerator  # noqa: E402
from app.application.services.fl_engine import FederatedLearningEngine  # noqa: E402
from app.application.services.metrics_service import MetricsService  # noqa: E402
from app.application.services.model_service import ModelService  # noqa: E402
from app.application.services.privacy_service import PrivacyService  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.domain.enums import AggregationMethod  # noqa: E402
from app.domain.value_objects import SimulationConfig  # noqa: E402


def run_simulation_run(
    config, bank_data, fl_engine, model_service, privacy_service, metrics_service
):
    """Run a simulation and return round-by-round evaluation metrics on global test set."""
    num_rounds = config.num_rounds

    # Concatenate global test set
    X_test_global = np.concatenate([data["X_test"] for data in bank_data.values()], axis=0)
    y_test_global = np.concatenate([data["y_test"] for data in bank_data.values()], axis=0)

    # Initialize global model
    global_model = model_service.create_model()
    global_weights = model_service.get_parameters(global_model)

    metrics_history = []
    round_times = []

    rng = np.random.default_rng(42)

    for round_num in range(1, num_rounds + 1):
        round_start_time = time.perf_counter()

        # Local training at each bank
        client_weights = []
        client_samples = []

        for bank_id, data in bank_data.items():
            # Create a fresh local model and load current global parameters
            local_model = model_service.create_model()
            local_model = model_service.set_parameters(local_model, global_weights)

            # Train local model for 1 epoch
            local_model, _ = model_service.train_local(
                local_model,
                data["X_train"],
                data["y_train"],
                epochs=config.local_epochs,
                learning_rate=config.learning_rate,
                batch_size=config.batch_size,
            )
            local_w = model_service.get_parameters(local_model)

            # Apply model poisoning if enabled and this bank is C (the attacker)
            if config.enable_poisoning_simulation and bank_id == "bank_c":
                local_w = fl_engine.apply_model_poisoning(
                    local_w,
                    scale=config.poisoning_scale,
                    rng=rng,
                )

            # Apply post-hoc DP if enabled
            if config.enable_differential_privacy:
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

            client_weights.append(local_w)
            client_samples.append(len(data["X_train"]))

        # Apply Secure Aggregation masking if enabled
        if config.enable_secure_aggregation:
            client_weights = fl_engine.apply_secure_aggregation_masks(
                client_weights,
                client_samples,
                rng=rng,
            )

        # Aggregation
        global_weights = fl_engine.aggregate_parameters(
            client_weights,
            client_samples,
            method=config.aggregation_method,
        )

        # Track round duration
        round_duration_ms = (time.perf_counter() - round_start_time) * 1000
        round_times.append(round_duration_ms)

        # Evaluate global model on global test set
        global_model = model_service.set_parameters(global_model, global_weights)
        eval_dict = model_service.evaluate(global_model, X_test_global, y_test_global)
        metrics = metrics_service.from_eval_dict(eval_dict)
        metrics_history.append(metrics)

    return metrics_history, round_times


def main():
    print("Initializing services...")
    settings = get_settings()
    model_service = ModelService(settings)
    privacy_service = PrivacyService()
    fl_engine = FederatedLearningEngine(settings, model_service, privacy_service)
    metrics_service = MetricsService()

    # Generate datasets (scaled down for speed, but large enough to train reliably)
    print("Generating data...")
    generator = DataGenerator(seed=42)
    datasets = generator.generate_bank_datasets(
        bank_a_size=2000, bank_b_size=1500, bank_c_size=1000
    )

    # Preprocess (encode & split)
    bank_data = {}
    for bank_id, (df, labels) in datasets.items():
        X = DataGenerator.encode_features(df)
        y = labels.values

        # Train / Test split
        from typing import Any, cast

        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=cast("Any", y)
        )
        bank_data[bank_id] = {
            "X_train": X_train,
            "X_test": X_test,
            "y_train": y_train,
            "y_test": y_test,
        }

    IMAGES_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "docs", "images"))
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # Define Configurations
    num_rounds = 5

    # ── Comparison 1: FedAvg vs Krum under Poisoning ──
    print("\n--- Running FedAvg (No Attack) ---")
    cfg_fed_avg_clean = SimulationConfig(
        num_rounds=num_rounds,
        local_epochs=1,
        aggregation_method=AggregationMethod.FED_AVG_WEIGHTED,
        enable_poisoning_simulation=False,
    )
    metrics_fed_avg_clean, times_fed_avg_clean = run_simulation_run(
        cfg_fed_avg_clean, bank_data, fl_engine, model_service, privacy_service, metrics_service
    )

    print("\n--- Running FedAvg (Poisoned) ---")
    cfg_fed_avg_poisoned = SimulationConfig(
        num_rounds=num_rounds,
        local_epochs=1,
        aggregation_method=AggregationMethod.FED_AVG_WEIGHTED,
        enable_poisoning_simulation=True,
        poisoning_bank_id="bank_c",
        poisoning_scale=10.0,
    )
    metrics_fed_avg_poisoned, _ = run_simulation_run(
        cfg_fed_avg_poisoned, bank_data, fl_engine, model_service, privacy_service, metrics_service
    )

    print("\n--- Running Krum (Poisoned) ---")
    cfg_krum_poisoned = SimulationConfig(
        num_rounds=num_rounds,
        local_epochs=1,
        aggregation_method=AggregationMethod.KRUM,
        enable_poisoning_simulation=True,
        poisoning_bank_id="bank_c",
        poisoning_scale=10.0,
    )
    metrics_krum_poisoned, _ = run_simulation_run(
        cfg_krum_poisoned, bank_data, fl_engine, model_service, privacy_service, metrics_service
    )

    # ── Comparison 2: Differential Privacy ON vs OFF ──
    print("\n--- Running FedAvg with DP (Epsilon=2.0) ---")
    cfg_fed_avg_dp = SimulationConfig(
        num_rounds=num_rounds,
        local_epochs=1,
        aggregation_method=AggregationMethod.FED_AVG_WEIGHTED,
        enable_differential_privacy=True,
        dp_epsilon=2.0,
        dp_delta=1e-5,
        dp_max_grad_norm=1.0,
    )
    metrics_fed_avg_dp, _ = run_simulation_run(
        cfg_fed_avg_dp, bank_data, fl_engine, model_service, privacy_service, metrics_service
    )

    # ── Comparison 3: Secure Aggregation ON vs OFF ──
    print("\n--- Running FedAvg with SecAgg ---")
    cfg_fed_avg_secagg = SimulationConfig(
        num_rounds=num_rounds,
        local_epochs=1,
        aggregation_method=AggregationMethod.FED_AVG_WEIGHTED,
        enable_secure_aggregation=True,
    )
    metrics_fed_avg_secagg, times_fed_avg_secagg = run_simulation_run(
        cfg_fed_avg_secagg, bank_data, fl_engine, model_service, privacy_service, metrics_service
    )

    # Plotting styles
    plt.style.use(
        "seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default"
    )

    # ── Plot 1: Byzantine Robustness (FedAvg vs Krum) ──
    print("\nPlotting Byzantine Robustness comparison...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    rounds_range = range(1, num_rounds + 1)

    # Accuracy Plot
    axes[0].plot(
        rounds_range,
        [m.accuracy for m in metrics_fed_avg_clean],
        "g-o",
        label="FedAvg (Clean)",
        linewidth=2,
    )
    axes[0].plot(
        rounds_range,
        [m.accuracy for m in metrics_fed_avg_poisoned],
        "r-x",
        label="FedAvg (Poisoned by Bank C)",
        linewidth=2,
    )
    axes[0].plot(
        rounds_range,
        [m.accuracy for m in metrics_krum_poisoned],
        "b-^",
        label="Krum (Poisoned by Bank C)",
        linewidth=2,
    )
    axes[0].set_title("Global Model Accuracy under Poisoning Attack")
    axes[0].set_xlabel("Round")
    axes[0].set_ylabel("Accuracy")
    axes[0].legend()
    axes[0].set_xticks(rounds_range)

    # F1-Score Plot
    axes[1].plot(
        rounds_range,
        [m.f1_score for m in metrics_fed_avg_clean],
        "g-o",
        label="FedAvg (Clean)",
        linewidth=2,
    )
    axes[1].plot(
        rounds_range,
        [m.f1_score for m in metrics_fed_avg_poisoned],
        "r-x",
        label="FedAvg (Poisoned by Bank C)",
        linewidth=2,
    )
    axes[1].plot(
        rounds_range,
        [m.f1_score for m in metrics_krum_poisoned],
        "b-^",
        label="Krum (Poisoned by Bank C)",
        linewidth=2,
    )
    axes[1].set_title("Global Model F1-Score under Poisoning Attack")
    axes[1].set_xlabel("Round")
    axes[1].set_ylabel("F1-Score")
    axes[1].legend()
    axes[1].set_xticks(rounds_range)

    plt.tight_layout()
    plt.savefig(os.path.join(IMAGES_DIR, "byzantine_robustness.png"), dpi=300)
    plt.close()

    # ── Plot 2: Differential Privacy (DP ON vs OFF) ──
    print("Plotting Differential Privacy utility trade-off...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # F1-Score
    axes[0].plot(
        rounds_range,
        [m.f1_score for m in metrics_fed_avg_clean],
        "g-o",
        label="FedAvg (DP OFF)",
        linewidth=2,
    )
    axes[0].plot(
        rounds_range,
        [m.f1_score for m in metrics_fed_avg_dp],
        "m-s",
        label="FedAvg (DP ON, ε=2.0)",
        linewidth=2,
    )
    axes[0].set_title("F1-Score: Privacy-Utility Trade-off")
    axes[0].set_xlabel("Round")
    axes[0].set_ylabel("F1-Score")
    axes[0].legend()
    axes[0].set_xticks(rounds_range)

    # AUC-ROC
    axes[1].plot(
        rounds_range,
        [m.auc_roc for m in metrics_fed_avg_clean],
        "g-o",
        label="FedAvg (DP OFF)",
        linewidth=2,
    )
    axes[1].plot(
        rounds_range,
        [m.auc_roc for m in metrics_fed_avg_dp],
        "m-s",
        label="FedAvg (DP ON, ε=2.0)",
        linewidth=2,
    )
    axes[1].set_title("AUC-ROC: Privacy-Utility Trade-off")
    axes[1].set_xlabel("Round")
    axes[1].set_ylabel("AUC-ROC")
    axes[1].legend()
    axes[1].set_xticks(rounds_range)

    plt.tight_layout()
    plt.savefig(os.path.join(IMAGES_DIR, "differential_privacy.png"), dpi=300)
    plt.close()

    # ── Plot 3: Secure Aggregation Overhead (SecAgg ON vs OFF) ──
    print("Plotting Secure Aggregation computational overhead...")
    avg_time_off = np.mean(times_fed_avg_clean)
    avg_time_on = np.mean(times_fed_avg_secagg)

    fig, ax = plt.subplots(figsize=(7, 5))
    categories = ["SecAgg OFF", "SecAgg ON"]
    times = [avg_time_off, avg_time_on]

    bars = ax.bar(categories, times, color=["#3b82f6", "#10b981"], width=0.5)
    ax.set_ylabel("Average Round Duration (ms)")
    ax.set_title("Secure Aggregation Computational Overhead")

    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.1f} ms",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),  # 3 points vertical offset
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(os.path.join(IMAGES_DIR, "secure_aggregation_overhead.png"), dpi=300)
    plt.close()

    print("\nAll charts generated successfully in docs/images/!")
    print(f"Directory: {IMAGES_DIR}")


if __name__ == "__main__":
    main()
