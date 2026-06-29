# Collaborative Fraud Intelligence Simulator

**Privacy-Preserving Cross-Institution Fraud Detection using Federated Learning**

[![CI](https://github.com/yourusername/fraud-intelligence-simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/fraud-intelligence-simulator/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## The Problem

Financial institutions detect fraud in isolation. Each bank trains models on its own transaction data, missing cross-institution fraud patterns like:

- **Velocity fraud** that spans multiple banks
- **Syndicate rings** operating across institutions
- **Emerging fraud typologies** visible only with aggregate data

Sharing raw transaction data is prohibited by privacy regulations (GDPR, CCPA, banking secrecy laws). Banks need a way to **collaborate without exposing customer data**.

## The Solution

This project simulates **Federated Learning** — a distributed ML paradigm where multiple institutions collaboratively train a shared fraud detection model. Each bank trains locally on its own data and shares only **model weight updates** (gradients), never raw transactions.

The simulator demonstrates:

| Feature | Description |
|---------|-------------|
| **Non-IID Data Generation** | Three banks with distinct fraud profiles, transaction distributions, and data volumes |
| **Federated Averaging (FedAvg)** | Round-based aggregation of model updates from participating clients |
| **Differential Privacy** | Calibrated Gaussian noise injection with privacy budget (ε, δ) tracking |
| **Secure Aggregation** | Pairwise masking that cancels during summation (simulated) |
| **Failure Injection** | Client dropout, reconnection, and network latency simulation |
| **Real-time Monitoring** | WebSocket-based round-by-round training progress |
| **Local vs Federated Comparison** | Side-by-side metrics proving collaborative advantage |
| **AML Intelligence Feed** | Collaborative risk-indicator exchange stripping all customer PII |
| **9-Signal Risk Engine** | Composite risk scoring combining ML predictions with velocity rules, device anomalies, and baseline deviations |
| **Entity Relationship Graph** | Interactive network visualization of customers, cards, devices, and merchants using React Flow |
| **Deterministic HMAC Resolution** | Privacy-preserving cross-bank entity linkage using HMAC-SHA256 hashes |
| **Scenario Replay Engine** | Scripted multi-bank fraud scenarios (Fraud Ring, ATO, Layering, Card Testing) replayed in real time |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Dashboard (Vite)                     │
│  Simulation Controls │ Training Timeline │ Metrics Charts     │
└──────────────┬───────────────────┬───────────────────────────┘
               │ REST API          │ WebSocket
┌──────────────▼───────────────────▼───────────────────────────┐
│                    FastAPI Application                        │
│  Routers → Services → Domain Entities                        │
│            │                                                  │
│            ├─ SimulationService (orchestrator)                │
│            ├─ FederatedLearningEngine (FedAvg + failure sim)  │
│            ├─ ModelService (PyTorch MLP)                      │
│            ├─ PrivacyService (DP + secure aggregation)        │
│            └─ DataGenerator (Non-IID synthetic data)          │
└──────────────┬───────────────────┬───────────────────────────┘
               │                   │
    ┌──────────▼───────┐  ┌───────▼────────┐
    │   PostgreSQL     │  │     Redis      │
    │   (persistence)  │  │ (cache + pub/sub│
    └──────────────────┘  │  + Celery)     │
                          └────────────────┘
```

> **Detailed architecture docs**: [`docs/architecture.md`](docs/architecture.md)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Make (optional, for convenience commands)

### Run with Docker

```bash
# Clone
git clone https://github.com/yourusername/fraud-intelligence-simulator.git
cd fraud-intelligence-simulator

# Copy environment file
cp .env.example .env

# Start all services
make dev
# Or: docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Flower (task monitor) | http://localhost:5555 |

### Run Without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

> **Note**: You'll need PostgreSQL and Redis running locally. See `.env.example` for connection strings.

## Running a Simulation

1. Open the dashboard at `http://localhost:3000`
2. Configure training parameters (rounds, learning rate, privacy settings)
3. Click **Start Federated Training**
4. Watch real-time progress via WebSocket updates
5. When complete, explore:
   - **Metrics comparison table** — local vs federated for all banks
   - **Loss convergence chart** — with dropout annotations
   - **ROC curves** — per-bank, per-model overlaid
   - **Confusion matrices** — heatmap visualization
   - **Feature importance** — first-layer weight analysis

## API Reference

### Phase 1: Federated Learning

```bash
# Start a simulation
POST /api/v1/simulations

# List simulations
GET /api/v1/simulations

# Get simulation details
GET /api/v1/simulations/{id}

# Get comparison metrics
GET /api/v1/simulations/{id}/comparison

# Get training rounds
GET /api/v1/training/{id}/rounds

# WebSocket training progress
WS /ws/training/{id}

# Bank reference data
GET /api/v1/banks

# Health checks
GET /health
GET /health/ready
```

### Phase 2: AML Intelligence Platform

```bash
# List and filter fraud alerts
GET /api/v1/alerts

# Get specific alert detail
GET /api/v1/alerts/{id}

# Get explainability report for a specific alert
GET /api/v1/alerts/{id}/explain

# List shared cross-bank intelligence items
GET /api/v1/intelligence

# Get shared intelligence aggregate stats
GET /api/v1/intelligence/stats

# CRUD investigation cases
GET/POST /api/v1/cases
GET/PATCH /api/v1/cases/{id}

# Add case investigation notes
POST /api/v1/cases/{id}/notes

# Link alerts to an investigation case
POST /api/v1/cases/{id}/alerts

# Get case event timeline
GET /api/v1/cases/{id}/timeline

# Export case summary as markdown
GET /api/v1/cases/{id}/export

# List entities
GET /api/v1/entities

# Get entity profile with cross-bank risk metrics
GET /api/v1/entities/{id}

# Get relationships associated with an entity
GET /api/v1/entities/{id}/relationships

# Resolve cross-bank entity overlap
POST /api/v1/entities/resolve

# Get subgraph centered on an entity for React Flow
GET /api/v1/graph/{id}

# List suspicious entity clusters
GET /api/v1/graph/clusters/list

# Search graph nodes
GET /api/v1/graph/search/nodes

# Get graph stats summary
GET /api/v1/graph/stats/summary

# List pre-built scenarios
GET /api/v1/scenarios

# Start a real-time scenario stream
POST /api/v1/scenarios/start

# Get status of active scenario
GET /api/v1/scenarios/{id}/status

# Stop a scenario stream
POST /api/v1/scenarios/{id}/stop

# List active scenarios
GET /api/v1/scenarios/active/list

# WebSocket scenario streaming
WS /ws/streaming/{scenario_id}

# Get dashboard aggregated stats
GET /api/v1/dashboard/stats

# Get current risk engine scoring weights
GET /api/v1/dashboard/risk-weights

# Update risk weights config
PUT /api/v1/dashboard/risk-weights
```

Full interactive docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Testing

```bash
# All tests
make test

# Unit tests only
make test-unit

# With coverage
make test-coverage

# Linting
make lint
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── domain/           # Entities, enums, value objects (Phase 1 & 2)
│   │   │   ├── enums.py
│   │   │   ├── entities.py
│   │   │   ├── entities_phase2.py
│   │   │   └── value_objects_phase2.py
│   │   ├── application/      # Services, schemas, interfaces
│   │   │   └── services/
│   │   │       ├── data_generator.py    # Non-IID synthetic data
│   │   │       ├── model_service.py     # PyTorch MLP
│   │   │       ├── fl_engine.py         # FedAvg + failure simulation
│   │   │       ├── privacy_service.py   # DP + secure aggregation
│   │   │       ├── alert_service.py     # Alert intelligence (Phase 2)
│   │   │       ├── risk_engine.py       # 9-signal Risk Engine (Phase 2)
│   │   │       ├── case_service.py      # Case management (Phase 2)
│   │   │       ├── entity_resolution.py # Cross-bank linkage (Phase 2)
│   │   │       ├── graph_engine.py      # Relationship Graph (Phase 2)
│   │   │       ├── explainability_service.py # Explainable AI (Phase 2)
│   │   │       └── streaming_engine.py  # Event replay (Phase 2)
│   │   ├── infrastructure/   # Database, cache, event bus, models
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── event_bus.py
│   │   ├── presentation/     # API routers, WebSocket (Phase 1 & 2)
│   │   └── tasks/            # Celery async tasks
│   ├── tests/                # Test suite (60 unit tests)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/              # Types, client, React Query hooks
│   │   ├── components/       # Reusable UI components
│   │   │   ├── layout/       # Sidebar, Header, Layout
│   │   │   ├── dashboard/    # BankCard, Controls, Timeline
│   │   │   └── charts/       # Loss, ROC, Confusion, Feature
│   │   ├── pages/            # Dashboard, SimulationView
│   │   └── utils/            # Formatters, constants
│   ├── Dockerfile
│   └── package.json
├── docs/                     # Architecture, system design, threat model
├── docker-compose.yml
├── Makefile
└── .github/                  # CI, templates
```

## Engineering Documentation

| Document | Purpose |
|----------|---------|
| [`docs/architecture.md`](docs/architecture.md) | Clean Architecture breakdown, layer responsibilities, data flow |
| [`docs/system_design.md`](docs/system_design.md) | System design interview-style walkthrough |
| [`docs/engineering_decisions.md`](docs/engineering_decisions.md) | ADR-style decision log with tradeoffs |
| [`docs/threat_model.md`](docs/threat_model.md) | Security analysis and privacy guarantees |
| [`docs/aml-platform.md`](docs/aml-platform.md) | Overview of AML intelligence, entity resolution, and fraud scenarios |
| [`docs/architecture-phase2.md`](docs/architecture-phase2.md) | Phase 2 system design, real-time data flows, and secure hashing details |

## Key Design Decisions

1. **Custom FL engine** over Flower (`flwr`) — maintains control over failure injection, round-based UI observability, and latency simulation. In production, `flwr` with gRPC is preferred for multi-machine deployment.

2. **Clean Architecture** — strict layer separation with dependency inversion. Domain layer has zero external imports. Application services define interfaces that Infrastructure implements.

3. **Synthetic Non-IID data** — three banks have distinct fraud profiles (velocity spikes, new-account fraud, card testing) to demonstrate real-world data heterogeneity.

4. **Simulated secure aggregation** — pairwise masks that mathematically cancel during summation. A production system would use SMPC protocols.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic v2, Uvicorn |
| ML | PyTorch, scikit-learn, NumPy |
| Task Queue | Celery + Redis |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic |
| Cache/PubSub | Redis |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 |
| Charts | Recharts |
| State | React Query (TanStack), Zustand |
| Containerization | Docker, Docker Compose |
| CI | GitHub Actions |

## License

MIT — see [LICENSE](LICENSE) for details.
#   C o l l a b o r a t i v e - F r a u d - I n t e l l i g e n c e - S i m u l a t o r  
 