import sys
import os

# Force CPU execution to prevent PyTorch CUDA hangs
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Add backend root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, '..')))

from app.application.services.simulation_service import SimulationService
from app.application.services.data_generator import DataGenerator
from app.application.services.fl_engine import FederatedLearningEngine
from app.application.services.privacy_service import PrivacyService
from app.application.services.metrics_service import MetricsService
from app.application.services.model_service import ModelService
from app.config import get_settings
from app.domain.value_objects import SimulationConfig

def main():
    print("Testing MLflow integration via SimulationService...")
    settings = get_settings()
    
    # Enable MLflow and customize experiment name
    settings.mlflow_enabled = True
    settings.mlflow_experiment_name = "Test-CFI-MLflow-Integration"
    
    # Instantiate actual service layers
    model_service = ModelService(settings)
    privacy_service = PrivacyService()
    fl_engine = FederatedLearningEngine(settings, model_service, privacy_service)
    metrics_service = MetricsService()
    data_generator = DataGenerator(seed=42)
    
    # Instantiate SimulationService with mock repositories
    simulation_service = SimulationService(
        settings=settings,
        simulation_repo=None,
        bank_repo=None,
        metrics_repo=None,
        data_generator=data_generator,
        fl_engine=fl_engine,
        metrics_service=metrics_service,
        model_service=model_service,
    )
    
    # Configure a tiny 2-round simulation for rapid local testing
    config = SimulationConfig(
        num_rounds=2,
        local_epochs=1,
        learning_rate=0.01,
        batch_size=64,
        min_clients_per_round=2,
        bank_a_transactions=1000,
        bank_b_transactions=800,
        bank_c_transactions=600,
        enable_differential_privacy=True,
        dp_epsilon=3.0,
        dp_delta=1e-5,
    )
    
    print("Starting simulation run...")
    simulation = simulation_service.run_simulation(config)
    print(f"Simulation completed with status: {simulation.status}")
    
    # Verify that the MLflow tracking runs were generated
    print("Verifying MLflow tracking files...")
    mlruns_dir = os.path.join(SCRIPT_DIR, '..', 'mlruns')
    if os.path.exists(mlruns_dir):
        print(f"Success: 'mlruns' directory created at: {os.path.abspath(mlruns_dir)}")
        # Check files inside
        experiments = os.listdir(mlruns_dir)
        print(f"Active experiments in mlruns: {experiments}")
    else:
        print("Error: 'mlruns' directory not found!")
        sys.exit(1)

if __name__ == '__main__':
    main()
