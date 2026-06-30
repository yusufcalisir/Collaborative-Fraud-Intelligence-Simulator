from fastapi.testclient import TestClient

from app.domain.enums import SimulationStatus
from app.main import app

client = TestClient(app)


def test_create_and_get_simulation():
    # 1. Create a simulation
    response = client.post(
        "/api/v1/simulations",
        json={
            "num_rounds": 2,
            "local_epochs": 1,
            "learning_rate": 0.001,
            "batch_size": 32,
            "min_clients_per_round": 2,
            "enable_latency_simulation": False,
            "enable_dropout_simulation": False,
            "enable_reconnect_simulation": True,
            "privacy_mechanism": "none",
            "dp_epsilon": 1.0,
            "dp_delta": 1e-5,
            "dp_max_grad_norm": 1.0,
            "bank_a_transactions": 1000,
            "bank_b_transactions": 1000,
            "bank_c_transactions": 1000,
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    simulation_id = data["id"]

    # 2. Immediately get the simulation (while it's running / pending)
    get_response = client.get(f"/api/v1/simulations/{simulation_id}")
    assert get_response.status_code == 200, f"Failed with {get_response.text}"
    get_data = get_response.json()
    assert get_data["id"] == simulation_id
    assert get_data["status"] in (
        SimulationStatus.PENDING.value,
        SimulationStatus.GENERATING_DATA.value,
    )
