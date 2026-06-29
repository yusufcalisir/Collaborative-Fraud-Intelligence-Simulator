# Collaborative Fraud Intelligence Simulator

A production-grade simulation framework for privacy-preserving, cross-institution financial fraud detection and Collaborative Anti-Money Laundering (AML) intelligence. This platform showcases how financial institutions can collaboratively train machine learning models and share risk intelligence without exposing sensitive customer Personally Identifiable Information (PII) or violating global privacy regulations like GDPR, CCPA, and banking secrecy laws.

[![CI](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

***

## The Core Challenge: Siloed Fraud Detection

Financial institutions currently detect fraud and money laundering in absolute isolation. Each bank trains machine learning models solely on its own internal transaction datasets. This isolation creates significant vulnerabilities:

*   **Velocity Fraud:** Fraudsters exploit the blind spot between institutions, transferring funds rapidly across multiple banks before any single bank detects the pattern.
*   **Syndicate Rings:** Large-scale mule networks distribute accounts and transactions across several institutions to fly under detection thresholds.
*   **Emerging Typologies:** New fraud techniques are often only visible when observing aggregate transaction behavior across the entire financial ecosystem.

Directly sharing transaction logs or database records between banks is strictly prohibited by privacy regulations and banking secrecy laws. This platform bridges that gap by demonstrating how banks can collaborate securely.

## The Technical Solution

The Collaborative Fraud Intelligence Simulator demonstrates two parallel tracks of secure, multi-bank collaboration:

### Track 1: Privacy-Preserving Federated Learning (Phase 1)
Instead of centralizing raw customer transactions, the framework uses a distributed machine learning paradigm:
1.  **Local Training:** Each bank trains a local PyTorch Multi-Layer Perceptron (MLP) on its own transaction data.
2.  **Gradient Exchange:** Banks export only their local model weights (gradients), keeping all raw transactions strictly on-premise.
3.  **Secure Aggregation:** An Aggregation Server averages the weights using the Federated Averaging (FedAvg) algorithm to create an improved global model.
4.  **Differential Privacy (DP):** Calibrated Gaussian noise is injected into weight updates, backed by mathematical privacy budget tracking (epsilon, delta), preventing reconstruction of training inputs.

### Track 2: Collaborative AML Intelligence & 9-Signal Risk Engine (Phase 2)
To provide real-time transaction screening and investigation capabilities:
1.  **Deterministic Entity Resolution:** Cross-bank customer and device matching is achieved via one-way HMAC-SHA256 hashes, allowing linkage of malicious actors without revealing identity.
2.  **9-Signal Risk Engine:** Combines machine learning inference with heuristic indicators (e.g., velocity anomalies, device mismatches, high-risk merchant categories, baseline deviations).
3.  **Interactive Relationship Graphs:** A full visual graph of entities, devices, cards, and accounts built using React Flow, mapping suspicious clusters in real time.
4.  **Scenario Replay Engine:** Scripted simulation flows representing typologies like Account Takeover (ATO), Card Testing, and Layering networks.

***

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Dashboard (Vite)                   │
│  Simulation Controls │ Training Timeline │ Metrics Charts   │
└──────────────┬───────────────────┬──────────────────────────┘
               │ REST API          │ WebSocket
┌──────────────▼───────────────────▼──────────────────────────┐
│                    FastAPI Application                      │
│  Routers -> Services -> Domain Entities                     │
│            │                                                │
│            ├─ SimulationService (Orchestrator)              │
│            ├─ FederatedLearningEngine (FedAvg + dropouts)   │
│            ├─ ModelService (PyTorch MLP)                    │
│            ├─ PrivacyService (DP + Secure Aggregation)      │
│            ├─ RiskEngine (9-Signal composite scoring)       │
│            └─ DataGenerator (Non-IID synthetic profiles)    │
└──────────────┬───────────────────┬──────────────────────────┘
               │                   │
    ┌──────────▼───────┐  ┌───────▼────────┐
    │    PostgreSQL    │  │     Redis      │
    │  (Persistence)   │  │ (Cache, PubSub │
    └──────────────────┘  │  + Event Bus)  │
                          └────────────────┘
```

The system is designed around Clean Architecture (Ports and Adapters) principles:
*   **Domain Layer (`backend/app/domain`):** Pure business logic, value objects, and entities. Zero external framework dependencies.
*   **Application Layer (`backend/app/application`):** Orchestrates use cases. Services implement business logic; schemas handle data validation.
*   **Infrastructure Layer (`backend/app/infrastructure`):** Implements data persistence, external caching, event dispatching, and background workers.
*   **Presentation Layer (`backend/app/presentation`):** Exposes async REST endpoints and WebSockets for live UI telemetry.

Detailed technical breakdowns can be found in the [`docs/`](docs/) folder.

***

## Quick Start

### Prerequisites
*   Docker and Docker Compose
*   Make (optional, for utility commands)

### Running with Docker Compose
To boot up the entire stack (FastAPI backend, React frontend, PostgreSQL database, Redis event bus) in development mode:

```bash
# Clone the repository
git clone https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator.git
cd Collaborative-Fraud-Intelligence-Simulator

# Copy environment variables template
cp .env.example .env

# Start all services
make dev
# Alternative: docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Access urls once the containers are running:
*   **Web Dashboard:** `http://localhost:3000`
*   **Interactive Swagger API Docs:** `http://localhost:8000/docs`
*   **ReDoc API Documentation:** `http://localhost:8000/redoc`

### Local Development (Without Docker)
Ensure you have local instances of PostgreSQL and Redis running, then execute:

```bash
# 1. Setup and start Backend
cd backend
python -m venv .venv
# On macOS/Linux: source .venv/bin/activate
# On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Setup and start Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

***

## Detailed Feature Log

| Feature | Technical Implementation | Purpose |
| :--- | :--- | :--- |
| **Non-IID Synthetic Data** | `DataGenerator` generates skewed distributions per bank (skewed fraud rates, different feature means). | Simulates real-world heterogeneity where banks have distinct customer bases. |
| **FedAvg Aggregation** | Weighted averaging of local weights based on relative client sample counts. | Central algorithm for model parameter synchronization in Federated Learning. |
| **Differential Privacy** | Gaussian noise addition to gradients combined with L2 norm clipping. | Mathematically guarantees that individual transaction signatures cannot be leaked. |
| **Client Failures** | Dynamic simulation of network latency, dropouts, and reconnection cycles. | Tests the resilience of the aggregation server against real-world connection drops. |
| **Deterministic Linkage** | Linkage of cross-bank entities using salted HMAC-SHA256 identifiers. | Matches entities (e.g., suspicious cards/devices) without sharing raw names or emails. |
| **9-Signal Risk Engine** | Custom pipeline weighting ML scores, device status, IP velocity, and behavioral shifts. | Builds a comprehensive risk profile for automated alert generation. |
| **Real-time Replay** | Replays historical fraud scenarios event-by-event via WebSockets. | Provides a high-fidelity demonstration of how cross-bank intelligence is shared. |

***

## Configuration Options

When running a simulation from the dashboard, the following parameters are configurable:

*   **Communication Rounds:** The number of aggregation cycles between banks and the central server.
*   **Local Epochs:** How many training epochs each bank performs locally per round before uploading updates.
*   **Learning Rate:** Step size optimization value for gradient descent.
*   **Batch Size:** Size of training data subsets passed through the PyTorch MLP.
*   **Privacy Mechanism:** Choose between *None*, *Differential Privacy*, *Secure Aggregation*, or *Both*.
*   **DP Epsilon ($\epsilon$):** Privacy loss parameter. Lower values mean stronger privacy (more noise) but lower accuracy.
*   **DP Delta ($\delta$):** Probability of accidental information leakage. Typically set to less than the inverse of the dataset size.
*   **Client Dropout Probability:** Probability of a bank client dropping offline during a round.

***

## Testing and Verification

The repository contains a robust integration and unit test suite verifying the FL engine, risk engine, and API layers.

```bash
# Execute full test suite
make test

# Execute backend integration tests only
cd backend
.venv/Scripts/pytest tests/integration/ -v

# Run format and lint checks
cd backend
.venv/Scripts/ruff check app/ tests/
.venv/Scripts/ruff format --check app/ tests/
```

***

## Production Roadmap and Hardening Gaps

To transition this proof-of-concept into a production deployment, the following changes are required:

1.  **Production Orchestration:** Replace the custom threaded aggregation runner with a framework like Flower (`flwr`) or PySyft, communicating over secure gRPC.
2.  **Cryptographic Secure Aggregation:** Upgrade simulated pairwise masking to a Multi-Party Computation (MPC) library (such as SPDZ) running in trusted execution environments.
3.  **Strict DP Accounting:** Replace basic sequential epsilon composition with Rényi Differential Privacy (RDP) using Opacus for optimal utility-privacy trade-offs.
4.  **Transport & Auth:** Enforce mutual TLS (mTLS) for bank-to-server weight transfers and establish HSM-backed key management.
5.  **Byzantine Robustness:** Implement aggregation defenses (e.g., Krum, Trimmed Mean, coordinate-wise median) to detect and reject poisoned model updates.

***

## License

MIT - see [LICENSE](LICENSE) for details.
